"""Tests for the offline demo LLM (zero-key local mode)."""
import pytest

from backend.agents.demo_llm import DemoLLM


@pytest.mark.asyncio
async def test_lineup_shape_and_count():
    llm = DemoLLM()
    raw = await llm.chat_json(
        "sys",
        "请为话题「AI 会不会取代人」设计一场圆桌讨论阵容，专家人数为 3 人（不含主持人）。",
    )
    assert raw["host"]["name"]
    assert raw["host"]["title"]
    assert len(raw["experts"]) == 3
    assert all(e["name"] and e["stance"] for e in raw["experts"])


@pytest.mark.asyncio
async def test_scheduler_picks_known_ids_and_ends():
    llm = DemoLLM()
    user = (
        "话题：AI\n\n"
        "在场嘉宾：\n"
        "1: 林薇 / 主持（主持人，立场：中立）\n"
        "2: 张维 / 教授（专家，立场：乐观）\n"
        "3: 李工 / 工程师（专家，立场：谨慎）\n"
        "4: 王芳 / 分析师（专家，立场：中立）\n"
        "现在是第 6 轮，目标总轮数约 12 轮。"
    )
    d = await llm.chat_json("sys", user)
    assert d["speaker_id"] in (1, 2, 3, 4)
    assert d["utterance"]
    assert d["public_thought"]
    assert d["action"] in {"comment", "follow_up", "rebuttal", "supplement", "summary"}
    assert d["wants_summary"] is False

    # Final turn must end with the host summarizing.
    user_end = user.replace("第 6 轮", "第 12 轮")
    d2 = await llm.chat_json("sys", user_end)
    assert d2["speaker_id"] == 1
    assert d2["wants_summary"] is True
    assert d2["action"] == "summary"


@pytest.mark.asyncio
async def test_consensus_and_summary():
    llm = DemoLLM()
    c = await llm.chat_json("sys", "话题：AI\n\n讨论记录：x")
    assert c["consensus"] and c["divergence"]
    s = await llm.chat_text("sys", "话题：AI\n讨论记录：x")
    assert "AI" in s and "{" not in s
