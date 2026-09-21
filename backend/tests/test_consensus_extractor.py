import pytest

from backend.agents import consensus_extractor


@pytest.mark.asyncio
async def test_early_transcript_returns_empty(fake_llm):
    out = await consensus_extractor.extract("话题", [{"name": "H", "content": "开场"}], fake_llm)
    assert out == {"consensus": [], "divergence": []}
    # No LLM call for a too-short transcript.
    assert fake_llm.calls == []


@pytest.mark.asyncio
async def test_extract_normalizes_and_dedupes(fake_llm):
    fake_llm.plan_json({
        "consensus": ["都认为安全很重要", "都认为安全很重要", "  ", None],
        "divergence": ["落地速度看法不一"],
    })
    msgs = [
        {"name": "A", "content": "1"},
        {"name": "B", "content": "2"},
        {"name": "A", "content": "3"},
    ]
    out = await consensus_extractor.extract("话题", msgs, fake_llm)
    assert out["consensus"] == ["都认为安全很重要"]
    assert out["divergence"] == ["落地速度看法不一"]


@pytest.mark.asyncio
async def test_extract_empty_lists(fake_llm):
    fake_llm.plan_json({"consensus": [], "divergence": []})
    msgs = [{"name": "A", "content": "1"}, {"name": "B", "content": "2"}]
    out = await consensus_extractor.extract("话题", msgs, fake_llm)
    assert out == {"consensus": [], "divergence": []}
