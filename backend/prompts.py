"""Structured prompts for the three core agents.

Keeping every prompt in one file makes the prompt-engineering choices reviewable
and lets tests assert on stable contract fields.
"""
from __future__ import annotations

from typing import List

LINEUP_SYSTEM = """你是一位资深的中文演播厅节目制作人，擅长为话题设计立场多元、有真实张力的圆桌讨论阵容。"""

def lineup_user(topic: str, expert_count: int) -> str:
    return f"""请为话题「{topic}」设计一场圆桌讨论阵容，专家人数为 {expert_count} 人（不含主持人）。

严格返回如下 JSON（不要任何额外文字、不要 Markdown 代码块）：
{{
  "host": {{"name": "化名", "title": "具体可信的身份", "persona": "一句话人物速写"}},
  "experts": [
    {{"name": "化名", "title": "身份", "stance": "在本话题上的明确立场或视角", "persona": "一句话人物速写"}}
  ]
}}

要求：
1. 专家背景必须覆盖该话题的不同视角（例如学界 / 产业 / 用户 / 政策 / 反方），立场之间要有真实差异，不要清一色站边。
2. 姓名用中文化名，Title 要具体到可信（如「某厂前算法负责人」「某高校副教授」）。
3. 主持人保持中立、善于追问与串联，不替任何一方下结论。
4. experts 数组长度必须等于 {expert_count}。"""


SCHEDULER_SYSTEM = """你是这场 AI 圆桌的导演兼主持人，负责决定下一位发言者与其台词。你要让讨论自然流动，而不是机械轮流。"""

def scheduler_user(topic: str, guest_list: str, transcript: str, turn: int,
                   max_turns: int) -> str:
    return f"""话题：{topic}

在场嘉宾（id: 姓名 / Title / 立场）：
{guest_list}

当前讨论记录：
{transcript if transcript else "（尚未开始，主持人即将开场）"}

现在是第 {turn} 轮，目标总轮数约 {max_turns} 轮。

请决定下一位发言者与他要说的话，严格返回如下 JSON：
{{
  "speaker_id": 必须是上面 guest_list 里出现过的数字 id,
  "public_thought": "一句话，用于该嘉宾小窗的公开思考摘要（例如「在考虑如何回应刚才的反驳」），不要暴露内部推理",
  "utterance": "1 到 2 句话的口语化发言，像真人说话，不要念稿",
  "action": "comment | follow_up | rebuttal | supplement | summary 之一",
  "wants_summary": true 或 false
}}

规则：
- 不要机械轮流。根据对话走向选择：可以是专家反驳上一位、补充新角度，也可以是主持人追问或把跑题拉回。
- 主持人只在开场、追问、串联、总结时发言。
- 当第 {turn} 轮已接近 {max_turns} 轮且讨论已充分时，把 speaker_id 设为主持人 id，action 设为 "summary"，wants_summary 设为 true；否则 wants_summary 为 false。
- utterance 控制在 1-2 句，不要长篇大论。"""


CONSENSUS_SYSTEM = """你是这场讨论的观察员，负责从发言中提炼已经形成的共识与分歧，只依据原文，不臆测。"""

def consensus_user(topic: str, transcript: str) -> str:
    return f"""话题：{topic}

讨论记录：
{transcript}

请严格返回如下 JSON：
{{
  "consensus": ["当前已形成的共识，每条一句话"],
  "divergence": ["当前仍存在的分歧，每条一句话"]
}}

要求：
- 只保留记录中明确出现过的内容；没有就返回空数组。
- 每条一句话，简洁、具体，不要泛泛而谈。"""


SUMMARY_SYSTEM = """你是本场圆桌的主持人，正在做收尾总结。请用自然、口语化的中文讲一段话。"""

def summary_user(topic: str, transcript: str, consensus: List[str],
                 divergence: List[str]) -> str:
    cons = "\n".join(f"- {c}" for c in consensus) or "- （尚不完全一致）"
    div = "\n".join(f"- {d}" for d in divergence) or "- （分歧不大）"
    return f"""话题：{topic}

讨论记录：
{transcript}

已观察到的共识：
{cons}

仍存在的分歧：
{div}

请以主持人身份用一段自然的口语化中文做总结：先概括主要共识，再点出仍然存在的分歧，最后一句有收束感。
直接输出主持人说的话，不要输出 JSON、不要分点编号、不要加「总结：」之类前缀。"""
