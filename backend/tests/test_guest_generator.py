import pytest

from backend.agents import guest_generator
from backend.agents.guest_generator import LineupError


def _lineup_payload(n):
    return {
        "host": {"name": "主持人甲", "title": "资深媒体人"},
        "experts": [
            {"name": f"专家{i}", "title": f"职位{i}", "stance": f"立场{i}"}
            for i in range(n)
        ],
    }


@pytest.mark.asyncio
async def test_generate_lineup_happy_path(fake_llm):
    fake_llm.plan_json(_lineup_payload(3))
    out = await guest_generator.generate_lineup("AI 会不会取代人", 3, fake_llm)
    assert out["host"]["name"] == "主持人甲"
    assert out["host"]["color"] == guest_generator.HOST_COLOR
    assert len(out["experts"]) == 3
    # Colors assigned deterministically from our palette, not from the LLM.
    assert out["experts"][0]["color"] == guest_generator.EXPERT_PALETTE[0]
    assert out["experts"][1]["color"] == guest_generator.EXPERT_PALETTE[1]
    # The LLM was asked the topic and count.
    assert "AI 会不会取代人" in fake_llm.calls[0][2]
    assert "3" in fake_llm.calls[0][2]


@pytest.mark.asyncio
async def test_generate_lineup_rejects_wrong_expert_count(fake_llm):
    fake_llm.plan_json(_lineup_payload(4))  # asked for 3, got 4
    with pytest.raises(LineupError):
        await guest_generator.generate_lineup("话题", 3, fake_llm)


@pytest.mark.asyncio
async def test_generate_lineup_rejects_empty_topic(fake_llm):
    with pytest.raises(LineupError):
        await guest_generator.generate_lineup("   ", 3, fake_llm)


@pytest.mark.asyncio
async def test_generate_lineup_rejects_out_of_range_count(fake_llm):
    with pytest.raises(LineupError):
        await guest_generator.generate_lineup("话题", 1, fake_llm)


@pytest.mark.asyncio
async def test_normalize_fills_defaults(fake_llm):
    raw = {"host": {"name": "H"}, "experts": [{"name": "E1"}]}
    out = guest_generator.normalize_lineup(raw, 1)
    assert out["host"]["title"] == "主持人"
    assert out["experts"][0]["title"] == "嘉宾"
