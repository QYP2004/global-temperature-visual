import pytest

from backend.agents import speaking_scheduler
from backend.agents.speaking_scheduler import ScheduleError


GUESTS = [
    {"id": 1, "role": "host", "name": "H", "title": "主持", "stance": "中立"},
    {"id": 2, "role": "expert", "name": "A", "title": "学者", "stance": "乐观"},
    {"id": 3, "role": "expert", "name": "B", "title": "工程师", "stance": "谨慎"},
]


def test_validate_happy_path():
    raw = {"speaker_id": 2, "utterance": "我认为可行。",
           "public_thought": "想回应 A", "action": "rebuttal", "wants_summary": False}
    out = speaking_scheduler.validate_decision(raw, {1, 2, 3})
    assert out["speaker_id"] == 2
    assert out["action"] == "rebuttal"
    assert out["wants_summary"] is False


def test_validate_rejects_unknown_speaker():
    raw = {"speaker_id": 99, "utterance": "hi"}
    with pytest.raises(ScheduleError):
        speaking_scheduler.validate_decision(raw, {1, 2, 3})


def test_validate_rejects_empty_utterance():
    raw = {"speaker_id": 2, "utterance": "   "}
    with pytest.raises(ScheduleError):
        speaking_scheduler.validate_decision(raw, {1, 2, 3})


def test_validate_defaults_unknown_action():
    raw = {"speaker_id": 2, "utterance": "x", "action": "magic"}
    out = speaking_scheduler.validate_decision(raw, {1, 2, 3})
    assert out["action"] == "comment"


@pytest.mark.asyncio
async def test_decide_next_builds_prompt_and_validates(fake_llm):
    fake_llm.plan_json({
        "speaker_id": 3, "utterance": "我反对。",
        "public_thought": "反驳一下", "action": "rebuttal", "wants_summary": False,
    })
    msgs = [{"name": "A", "content": "AI 会普及。"}]
    out = await speaking_scheduler.decide_next("话题", GUESTS, msgs,
                                                 turn=2, max_turns=10, llm=fake_llm)
    assert out["speaker_id"] == 3
    # Prompt must carry the guest list (with ids) and the running transcript.
    user_prompt = fake_llm.calls[0][2]
    assert "2: A" in user_prompt
    assert "AI 会普及" in user_prompt


@pytest.mark.asyncio
async def test_decide_next_invalid_json_raises(fake_llm):
    fake_llm.plan_json({"speaker_id": 999, "utterance": "x"})
    with pytest.raises(ScheduleError):
        await speaking_scheduler.decide_next("话题", GUESTS, [], 1, 10, fake_llm)
