"""Distill consensus / divergence from the running transcript."""
from __future__ import annotations

from typing import List

from .. import prompts
from ..llm import LLMClient


class ConsensusError(RuntimeError):
    pass


def _transcript_text(messages: List[dict]) -> str:
    return "\n".join(f"[{m['name']}] {m['content']}" for m in messages)


def normalize(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ConsensusError("consensus output must be a JSON object")
    consensus = raw.get("consensus") or []
    divergence = raw.get("divergence") or []
    if not isinstance(consensus, list) or not isinstance(divergence, list):
        raise ConsensusError("consensus/divergence must be lists")
    consensus = [str(x).strip() for x in consensus if x and str(x).strip()]
    divergence = [str(x).strip() for x in divergence if x and str(x).strip()]
    # De-duplicate while preserving order.
    def _dedup(seq):
        seen = set()
        out = []
        for s in seq:
            key = s.lower()
            if key not in seen:
                seen.add(key)
                out.append(s)
        return out
    return {"consensus": _dedup(consensus), "divergence": _dedup(divergence)}


async def extract(topic: str, messages: List[dict], llm: LLMClient) -> dict:
    if len(messages) < 2:
        return {"consensus": [], "divergence": []}
    raw = await llm.chat_json(
        prompts.CONSENSUS_SYSTEM,
        prompts.consensus_user(topic, _transcript_text(messages)),
    )
    return normalize(raw)
