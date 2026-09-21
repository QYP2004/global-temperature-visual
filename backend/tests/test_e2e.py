"""End-to-end test: boots the real FastAPI app on a temp SQLite DB with a
scripted FakeLLM, creates a discussion, starts the loop, and asserts the whole
studio flow (lineup -> messages -> live consensus -> host summary).
"""
import os
import tempfile

# Point the DB and set a dummy key BEFORE importing backend (engine is created at import).
os.environ["ROUND_TABLE_DB"] = os.path.join(tempfile.mkdtemp(), "e2e.db")
os.environ["LLM_API_KEY"] = "test-key-not-used"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402

from backend.agents import discussion_loop  # noqa: E402
from backend.database import Base, engine, init_db  # noqa: E402
from backend.llm import configure_llm  # noqa: E402
from backend.main import app  # noqa: E402
from backend.tests.conftest import FakeLLM  # noqa: E402


def _lineup():
    return {
        "host": {"name": "主持人", "title": "节目主持人"},
        "experts": [
            {"name": "张专家", "title": "某高校教授", "stance": "乐观"},
            {"name": "李专家", "title": "某厂工程师", "stance": "谨慎"},
            {"name": "王专家", "title": "某分析师", "stance": "中立"},
        ],
    }


def _decision(speaker_id, action="comment", summary=False):
    return {
        "speaker_id": speaker_id,
        "utterance": f"这是{speaker_id}的一句发言。",
        "public_thought": "正在思考",
        "action": action,
        "wants_summary": summary,
    }


@pytest_asyncio.fixture
async def client(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    init_db()

    fake = FakeLLM()
    fake.plan_json(
        _lineup(),
        # turn 1
        _decision(2),
        # turn 2
        _decision(3),
        # consensus after turn 2
        {"consensus": ["都认为应该重视"], "divergence": ["节奏看法不同"]},
        # turn 3
        _decision(4),
        # turn 4: host concludes
        _decision(1, action="summary", summary=True),
        # consensus after turn 4 (latest view replaces earlier one)
        {"consensus": ["都认为应该重视", "方向基本一致"], "divergence": ["节奏看法不同"]},
    )
    fake.plan_text("以上就是今天讨论的全部内容，谢谢大家。")

    configure_llm(fake)
    # Speed the loop up: no real sleeps, short discussion.
    async def _no_sleep():
        return None
    monkeypatch.setattr(discussion_loop, "_sleep_realistic", _no_sleep)
    monkeypatch.setattr(discussion_loop, "_sleep_thinking", _no_sleep)
    monkeypatch.setattr(discussion_loop, "MAX_TURNS", 4)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_full_discussion_flow(client):
    # 1) Create discussion -> LLM generates lineup.
    r = await client.post("/api/discussions", json={"topic": "AI 会不会取代程序员",
                                                   "expert_count": 3})
    assert r.status_code == 200, r.text
    d = r.json()
    disc_id = d["id"]
    assert d["status"] == "pending"
    assert len(d["guests"]) == 4  # 1 host + 3 experts
    host = [g for g in d["guests"] if g["role"] == "host"][0]
    assert host["color"] == "#E8C872"

    # 2) Start the loop.
    r = await client.post(f"/api/discussions/{disc_id}/start")
    assert r.status_code == 200

    # 3) Poll until the loop ends (host summary delivered).
    import asyncio
    final = None
    for _ in range(100):
        await asyncio.sleep(0.05)
        r = await client.get(f"/api/discussions/{disc_id}")
        state = r.json()
        if state["status"] == "ended":
            final = state
            break
    assert final is not None, "discussion never reached 'ended'"

    # 4) Transcript: 4 scheduled utterances persisted.
    assert len(final["messages"]) == 4
    names = [m["name"] for m in final["messages"]]
    assert "张专家" in names and "主持人" in names

    # 5) Consensus / divergence updated live and persisted.
    assert any("重视" in c for c in final["consensus"])
    assert any("节奏" in x for x in final["divergence"])

    # 6) Host summary is natural language, not JSON.
    assert "今天讨论" in final["summary"] or "以上" in final["summary"]
    assert "{" not in final["summary"]

    # 7) Listing endpoint works and shows the ended discussion.
    r = await client.get("/api/discussions")
    rows = r.json()
    assert any(row["id"] == disc_id and row["status"] == "ended" for row in rows)


@pytest.mark.asyncio
async def test_two_discussions_run_in_parallel_isolated(client):
    """Two discussions started concurrently must not leak state into each other."""
    fake = FakeLLM()  # content-aware fallback handles both discussions
    configure_llm(fake)

    import asyncio

    ids = []
    for topic in ["话题甲", "话题乙"]:
        r = await client.post("/api/discussions",
                              json={"topic": topic, "expert_count": 3})
        assert r.status_code == 200
        ids.append(r.json()["id"])
    # Start both nearly at the same time.
    for i in ids:
        await client.post(f"/api/discussions/{i}/start")

    finals = {}
    for i in ids:
        for _ in range(100):
            await asyncio.sleep(0.03)
            s = (await client.get(f"/api/discussions/{i}")).json()
            if s["status"] == "ended":
                finals[i] = s
                break
        assert i in finals, f"discussion {i} never ended"

    # Isolation: each discussion has its own transcript and delivered a summary.
    assert len(finals[ids[0]]["messages"]) == 4
    assert len(finals[ids[1]]["messages"]) == 4
    assert finals[ids[0]]["summary"]
    assert finals[ids[1]]["summary"]
    # Each discussion only talks about its own roster (own message rows).
    names_a = {m["name"] for m in finals[ids[0]]["messages"]}
    names_b = {m["name"] for m in finals[ids[1]]["messages"]}
    assert names_a == names_b
