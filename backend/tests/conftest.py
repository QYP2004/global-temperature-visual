"""Shared test fixtures: a scripted fake LLM client."""
from __future__ import annotations

import re
from typing import List, Tuple

import pytest


class FakeLLM:
    """Returns queued responses in order; when the queue runs out it answers
    content-aware deterministic responses (so concurrent multi-discussion E2E
    tests don't share a fragile FIFO script)."""

    def __init__(self):
        self.json_queue: List[dict] = []
        self.text_queue: List[str] = []
        self.calls: List[Tuple[str, str]] = []

    def plan_json(self, *objs: dict):
        self.json_queue.extend(objs)
        return self

    def plan_text(self, *texts: str):
        self.text_queue.extend(texts)
        return self

    async def chat_json(self, system: str, user: str) -> dict:
        self.calls.append(("json", system, user))
        if self.json_queue:
            return self.json_queue.pop(0)
        return self._fallback_json(user)

    async def chat_text(self, system: str, user: str) -> str:
        self.calls.append(("text", system, user))
        if self.text_queue:
            return self.text_queue.pop(0)
        return "以上就是今天讨论的全部内容，谢谢大家。"

    # -- content-aware fallback -----------------------------------------
    @staticmethod
    def _fallback_json(user: str) -> dict:
        if "设计一场圆桌讨论阵容" in user:
            return {
                "host": {"name": "主持人", "title": "节目主持人"},
                "experts": [
                    {"name": n, "title": "教授", "stance": "中立"}
                    for n in ["张专家", "李专家", "王专家"]
                ],
            }
        if "在场嘉宾" in user:
            ids = [int(x) for x in re.findall(r"(?m)^(\d+):\s", user)]
            if not ids:
                ids = [1, 2, 3, 4]
            turn = int(re.search(r"现在是第\s*(\d+)\s*轮", user).group(1))
            max_turns = int(re.search(r"目标总轮数约\s*(\d+)\s*轮", user).group(1))
            if turn >= max_turns:
                return {"speaker_id": ids[0], "utterance": "好，我们收尾。",
                        "public_thought": "收尾", "action": "summary",
                        "wants_summary": True}
            spk = ids[1 + (turn % (len(ids) - 1))]
            return {"speaker_id": spk, "utterance": f"第{turn}轮的一句发言。",
                    "public_thought": "思考", "action": "comment",
                    "wants_summary": False}
        # consensus / divergence extraction
        return {"consensus": ["共识一"], "divergence": ["分歧一"]}


@pytest.fixture
def fake_llm():
    return FakeLLM()
