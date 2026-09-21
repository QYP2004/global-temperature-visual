"""Offline deterministic LLM for zero-key local demo.

It answers the SAME structured prompts the real pipeline uses (lineup /
scheduler / consensus / summary), so the whole studio runs end-to-end with no
external API. Real deployments set LLM_DEMO=0 and provide a real key.
"""
from __future__ import annotations

import re

# A small pool of diverse, credible expert personas.
EXPERT_POOL = [
    ("张维", "某高校教授", "技术乐观派：认为趋势不可阻挡"),
    ("李工", "某厂前技术负责人", "务实谨慎：关注落地成本与风险"),
    ("王芳", "独立行业分析师", "中立观察者：强调数据与边界"),
    ("赵磊", "一线从业者", "用户视角：关心真实体验与成本"),
    ("陈静", "政策研究员", "制度视角：关注监管与公平"),
    ("周明", "连续创业者", "市场视角：关注商业可行性"),
]

_DEBATE_LINES = [
    "从我的视角看，这件事不能简单下结论，得先分清楚适用场景。",
    "我不太同意刚才那种乐观，真正的成本往往被忽略了。",
    "补充一点：数据显示，这件事在不同行业的节奏完全不一样。",
    "说到底，技术只是工具，决定结果的是怎么用、谁来用。",
    "我更关心普通人能不能真正受益，而不是概念有多新。",
    "风险当然存在，但因为怕风险就不动，代价可能更大。",
]


def _parse_topic(text: str) -> str:
    for pat in (
        r"话题[：:]\s*[「『]?(.+?)[」』]?\n",
        r"为话题[「『](.+?)[」『]",
    ):
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return "这个话题"


class DemoLLM:
    """Scripted, deterministic replacement for the real LLM client."""

    async def chat_json(self, system: str, user: str) -> dict:
        if "设计一场圆桌讨论阵容" in user:
            return self._lineup(user)
        if "在场嘉宾" in user or "下一位发言者" in user:
            return self._scheduler(user)
        return self._consensus()

    async def chat_text(self, system: str, user: str) -> str:
        topic = _parse_topic(user)
        return (
            f"各位，今天关于「{topic}」的讨论很充分。我们基本同意：这件事不能一概而论，"
            f"需要分场景、看节奏；主要分歧在于落地的速度与代价。这是一个值得持续观察的话题。"
            f"谢谢各位嘉宾，也谢谢观众。"
        )

    # -- internal --------------------------------------------------------
    def _lineup(self, user: str) -> dict:
        m = re.search(r"专家人数为\s*(\d+)", user)
        n = int(m.group(1)) if m else 3
        topic = _parse_topic(user)
        experts = []
        for i in range(min(n, len(EXPERT_POOL))):
            name, title, stance = EXPERT_POOL[i]
            experts.append({
                "name": name, "title": title, "stance": stance,
                "persona": f"对「{topic}」有自己的判断",
            })
        return {
            "host": {"name": "林薇", "title": "资深媒体人",
                     "persona": "中立主持，擅长追问与串联"},
            "experts": experts,
        }

    def _scheduler(self, user: str) -> dict:
        topic = _parse_topic(user)
        ids = [int(x) for x in re.findall(r"(?m)^(\d+):\s", user)]
        turn = int(re.search(r"现在是第\s*(\d+)\s*轮", user).group(1))
        max_turns = int(re.search(r"目标总轮数约\s*(\d+)\s*轮", user).group(1))
        if not ids:
            ids = [1, 2, 3, 4]
        host_id, expert_ids = ids[0], ids[1:] or ids[1:]

        if turn >= max_turns:
            return {
                "speaker_id": host_id,
                "utterance": f"好，最后我们收个尾。围绕「{topic}」，大家的观点已经很清楚了。",
                "public_thought": "准备收尾",
                "action": "summary",
                "wants_summary": True,
            }
        if turn == 1:
            return {
                "speaker_id": host_id,
                "utterance": (f"各位好，欢迎来到今天的讨论。我们聊的是「{topic}」。"
                              f"先请各位表个态，也欢迎互相反驳。"),
                "public_thought": "开场",
                "action": "comment",
                "wants_summary": False,
            }
        if turn % 4 == 0:
            return {
                "speaker_id": host_id,
                "utterance": (f"刚才几位各有立场。我追问一句：落到现实里，"
                              f"「{topic}」最容易被高估或低估的是什么？"),
                "public_thought": "追问推进",
                "action": "follow_up",
                "wants_summary": False,
            }

        spk = expert_ids[(turn - 2) % len(expert_ids)]
        action = "rebuttal" if turn % 3 == 0 else "comment"
        if turn % 5 == 0:
            action = "supplement"
        return {
            "speaker_id": spk,
            "utterance": _DEBATE_LINES[(turn - 2) % len(_DEBATE_LINES)],
            "public_thought": "思考上一位的观点",
            "action": action,
            "wants_summary": False,
        }

    def _consensus(self) -> dict:
        return {
            "consensus": [
                "都认为这件事需要分场景、分阶段看，不能一概而论",
                "技术本身不是答案，关键在于如何使用与治理",
            ],
            "divergence": [
                "对落地速度与节奏的判断存在分歧",
                "成本由谁承担，各方看法不一",
            ],
        }
