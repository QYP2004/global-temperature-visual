"""Generate host + expert lineup from a topic and expert count."""
from __future__ import annotations

from .. import prompts
from ..llm import LLMClient

# Distinct, studio-friendly colors. Host gets a neutral gold.
EXPERT_PALETTE = [
    "#5B8FF9", "#F6BD16", "#5AD8A6", "#E8684A",
    "#6DC8EC", "#945FB9", "#FF9D4D", "#269A99",
]
HOST_COLOR = "#E8C872"


class LineupError(RuntimeError):
    pass


def normalize_lineup(raw: dict, expert_count: int) -> dict:
    """Validate and normalize the LLM JSON into a stable shape."""
    if not isinstance(raw, dict):
        raise LineupError("lineup must be a JSON object")
    host = raw.get("host") or {}
    experts = raw.get("experts") or []
    if not isinstance(host, dict) or not host.get("name"):
        raise LineupError("host.name missing")
    if not isinstance(experts, list) or len(experts) != expert_count:
        raise LineupError(
            f"experts count must be {expert_count}, got {len(experts) if isinstance(experts, list) else 'non-list'}"
        )
    for i, e in enumerate(experts):
        if not isinstance(e, dict) or not e.get("name"):
            raise LineupError(f"expert[{i}].name missing")
        e.setdefault("title", "嘉宾")
        e.setdefault("stance", "")
        e.setdefault("persona", "")
    host.setdefault("title", "主持人")
    host.setdefault("persona", "")
    return {"host": host, "experts": experts}


async def generate_lineup(topic: str, expert_count: int,
                          llm: LLMClient) -> dict:
    if not topic.strip():
        raise LineupError("topic is empty")
    if expert_count < 2 or expert_count > len(EXPERT_PALETTE):
        raise LineupError(f"expert_count must be between 2 and {len(EXPERT_PALETTE)}")
    raw = await llm.chat_json(prompts.LINEUP_SYSTEM,
                              prompts.lineup_user(topic, expert_count))
    lineup = normalize_lineup(raw, expert_count)
    # Assign colors (done deterministically by us, not the LLM).
    lineup["host"]["color"] = HOST_COLOR
    for i, e in enumerate(lineup["experts"]):
        e["color"] = EXPERT_PALETTE[i % len(EXPERT_PALETTE)]
    return lineup
