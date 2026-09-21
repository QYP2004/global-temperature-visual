"""The async discussion loop: drives turns, emits SSE events, persists state."""
from __future__ import annotations

import asyncio
import random
from typing import List, Optional

from ..agents import consensus_extractor, guest_generator, speaking_scheduler
from ..database import SessionLocal
from ..eventbus import bus
from ..llm import LLMClient, get_llm
from ..models import Consensus, Divergence, Discussion, Guest, Message
from .. import prompts

MAX_TURNS = 14  # target length of one discussion


def _guests_payload(guests) -> List[dict]:
    return [
        {"id": g.id, "role": g.role, "name": g.name, "title": g.title,
         "stance": g.stance, "color": g.color}
        for g in guests
    ]


def _messages_payload(messages) -> List[dict]:
    return [
        {"id": m.id, "guest_id": m.guest_id, "name": m.guest.name,
         "title": m.guest.title, "color": m.guest.color, "content": m.content,
         "action": m.action}
        for m in messages
    ]


async def _sleep_realistic():
    # Simulate natural thinking / speaking pacing.
    await asyncio.sleep(random.uniform(1.4, 2.4))


async def _sleep_thinking():
    # Pause in the "preparing" stage.
    await asyncio.sleep(random.uniform(0.5, 1.0))


async def run_discussion(disc_id: int, llm: Optional[LLMClient] = None) -> None:
    llm = llm or get_llm()
    db = SessionLocal()
    try:
        disc: Discussion = db.query(Discussion).get(disc_id)
        if disc is None:
            return
        disc.status = "active"
        db.commit()
        await bus.publish(disc_id, {"type": "status", "status": "active"})

        guests = disc.guests
        gmap = {g.id: g for g in guests}
        guests_payload = _guests_payload(guests)

        # Reset all agent windows to idle.
        for g in guests:
            bus.set_status(disc_id, g.id, "idle", "")

        transcript_for_llm = []  # lightweight [{name, content}]

        turn = 0
        ended = False
        while not ended and turn < MAX_TURNS:
            turn += 1
            try:
                decision = await speaking_scheduler.decide_next(
                    topic=disc.topic,
                    guests=guests_payload,
                    messages=transcript_for_llm,
                    turn=turn,
                    max_turns=MAX_TURNS,
                    llm=llm,
                )
            except Exception as exc:  # pragma: no cover - defensive
                await bus.publish(disc_id, {"type": "error", "message": f"调度失败：{exc}"})
                break

            speaker_id = decision["speaker_id"]
            speaker = gmap[speaker_id]

            # Stage 1: this guest is "preparing" (thinking), others idle.
            def _paint(status: str):
                for g in guests:
                    bus.set_status(
                        disc_id, g.id,
                        status if g.id == speaker_id else "idle",
                        decision["public_thought"] if g.id == speaker_id else "",
                    )

            _paint("preparing")
            await bus.publish(disc_id, {"type": "agent_status",
                                        "statuses": bus.snapshot_status(disc_id)})
            # Natural "thinking" gap before the utterance lands.
            await _sleep_thinking()

            # Stage 2: this guest is actually speaking.
            _paint("speaking")
            await bus.publish(disc_id, {"type": "agent_status",
                                        "statuses": bus.snapshot_status(disc_id)})
            await _sleep_realistic()

            # Persist message.
            msg = Message(discussion_id=disc_id, guest_id=speaker_id,
                          content=decision["utterance"], action=decision["action"])
            db.add(msg)
            db.commit()
            db.refresh(msg)
            transcript_for_llm.append({"name": speaker.name, "content": msg.content})

            await bus.publish(disc_id, {
                "type": "message",
                "message": {
                    "id": msg.id, "guest_id": speaker.id, "name": speaker.name,
                    "title": speaker.title, "color": speaker.color,
                    "content": msg.content, "action": msg.action,
                },
            })

            # Periodically refresh consensus / divergence (not just at the end).
            if turn >= 2 and turn % 2 == 0:
                try:
                    cd = await consensus_extractor.extract(disc.topic, transcript_for_llm, llm)
                    # Replace persisted consensus/divergence with the latest view.
                    db.query(Consensus).filter_by(discussion_id=disc_id).delete()
                    db.query(Divergence).filter_by(discussion_id=disc_id).delete()
                    for c in cd["consensus"]:
                        db.add(Consensus(discussion_id=disc_id, content=c))
                    for d in cd["divergence"]:
                        db.add(Divergence(discussion_id=disc_id, content=d))
                    db.commit()
                    await bus.publish(disc_id, {"type": "consensus", **cd})
                except Exception:  # pragma: no cover - non-fatal
                    pass

            if decision["wants_summary"] and decision["action"] == "summary":
                ended = True

        # Host delivers the closing summary as natural language.
        cons = [c.content for c in disc.consensus_items]
        div = [d.content for d in disc.divergence_items]
        try:
            summary_text = await llm.chat_text(
                prompts.SUMMARY_SYSTEM,
                prompts.summary_user(disc.topic, transcript_for_llm, cons, div),
            )
        except Exception as exc:  # pragma: no cover
            summary_text = f"今天的讨论先告一段落。（总结生成失败：{exc}）"

        disc.summary = summary_text
        disc.status = "ended"
        db.commit()

        for g in guests:
            bus.set_status(disc_id, g.id, "idle", "")
        await bus.publish(disc_id, {"type": "agent_status",
                                    "statuses": bus.snapshot_status(disc_id)})
        await bus.publish(disc_id, {"type": "summary", "summary": summary_text})
        await bus.publish(disc_id, {"type": "status", "status": "ended"})
    finally:
        db.close()


def start_or_restart(disc_id: int, llm: Optional[LLMClient] = None) -> bool:
    """Kick off the loop as a background task. Returns False if already running."""
    if bus.task_running(disc_id):
        return False
    task = asyncio.create_task(run_discussion(disc_id, llm))
    bus.register_task(disc_id, task)
    return True
