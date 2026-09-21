"""Decide who speaks next and what they say — non-mechanical flow."""
from __future__ import annotations

from typing import List, Set

from .. import prompts
from ..llm import LLMClient


class ScheduleError(RuntimeError):
    pass


def _guest_list_text(guests: List[dict]) -> str:
    lines = []
    for g in guests:
        role = "主持人" if g["role"] == "host" else "专家"
        lines.append(f"{g['id']}: {g['name']} / {g['title']}（{role}，立场：{g.get('stance') or '中立'}）")
    return "\n".join(lines)


def _transcript_text(messages: List[dict]) -> str:
    if not messages:
        return ""
    return "\n".join(f"[{m['name']}] {m['content']}" for m in messages)


def validate_decision(raw: dict, valid_ids: Set[int]) -> dict:
    if not isinstance(raw, dict):
        raise ScheduleError("decision must be a JSON object")
    try:
        speaker_id = int(raw["speaker_id"])
    except (KeyError, TypeError, ValueError):
        raise ScheduleError("speaker_id missing or not an int")
    if speaker_id not in valid_ids:
        raise ScheduleError(f"speaker_id {speaker_id} not in guest list")
    utterance = (raw.get("utterance") or "").strip()
    if not utterance:
        raise ScheduleError("utterance empty")
    action = raw.get("action", "comment")
    if action not in {"comment", "follow_up", "rebuttal", "supplement", "summary"}:
        action = "comment"
    return {
        "speaker_id": speaker_id,
        "utterance": utterance,
        "public_thought": (raw.get("public_thought") or "").strip() or "正在思考",
        "action": action,
        "wants_summary": bool(raw.get("wants_summary", False)),
    }


async def decide_next(topic: str, guests: List[dict], messages: List[dict],
                      turn: int, max_turns: int, llm: LLMClient) -> dict:
    """Return a validated next-speaker decision.

    guests: [{"id","role","name","title","stance"}]
    messages: [{"name","content"}]
    """
    valid_ids = {g["id"] for g in guests}
    raw = await llm.chat_json(
        prompts.SCHEDULER_SYSTEM,
        prompts.scheduler_user(
            topic=topic,
            guest_list=_guest_list_text(guests),
            transcript=_transcript_text(messages),
            turn=turn,
            max_turns=max_turns,
        ),
    )
    return validate_decision(raw, valid_ids)
