"""Seed 5 preset sample discussions (topic + lineup + a short finished debate).

Usage:
    python -m scripts.seed_demo
"""
from backend.database import SessionLocal, init_db
from backend.models import Consensus, Divergence, Discussion, Guest, Message

HOST_COLOR = "#E8C872"
PALETTE = ["#5B8FF9", "#F6BD16", "#5AD8A6", "#E8684A", "#6DC8EC", "#945FB9"]

SAMPLES = [
    {
        "topic": "AI 会取代初级程序员吗",
        "guests": [
            ("host", "陈启", "资深科技谈话节目主持人", "中立主持"),
            ("expert", "林一舟", "某头部云厂商前算法负责人", "门槛从打字变成判断力"),
            ("expert", "苏晚晴", "某 985 高校副教授", "AI 正在掏空新人的学习阶梯"),
            ("expert", "郑大川", "某软件外包公司技术总监", "AI 替不了背锅填坑的人"),
        ],
        "messages": [
            ("陈启", "各位，今天聊聊 AI 会不会把初级程序员这碗饭端走。"),
            ("林一舟", "只会写 CRUD 的简历我们基本不看了，但会用 AI 拆需求、定位 bug 的人身价翻倍。"),
            ("苏晚晴", "可判断力恰恰是从亲手写烂代码、亲手 debug 里长出来的，跳过这一步是教育危机。"),
            ("郑大川", "客户要的是敢签字、能扛事的人，这部分 AI 暂时替不了。"),
        ],
        "consensus": ["AI 取代的是只会敲代码的部分，判断力与扛事能力成为新稀缺品"],
        "divergence": ["判断力是否必须从亲手写代码中长出来", "新人用 AI 会不会跳过学习阶梯"],
        "summary": "说到底，AI 取代的不是初级程序员这个身份，而是其中只会敲代码的部分；判断力、扛事能力成了新的稀缺品。",
    },
    {
        "topic": "金价未来一年会涨吗",
        "guests": [
            ("host", "林衡", "财经节目主持人", "中立主持"),
            ("expert", "周谨", "某券商首席分析师", "实际利率下行，金价中枢仍有支撑"),
            ("expert", "吴桐", "黄金 ETF 基金经理", "短期涨幅已透支，回调风险不小"),
            ("expert", "赵野", "某产业链贸易商", "央行购金的实物需求托底"),
        ],
        "messages": [
            ("林衡", "今天聊聊接下来一年金价怎么走。"),
            ("周谨", "实际利率下行、央行持续购金，金价的中期中枢是往上走的。"),
            ("吴桐", "但短期涨幅已经很大，追高的回撤风险不小，别线性外推。"),
            ("赵野", "实物需求在那摆着，真跌下来买盘会接住。"),
        ],
        "consensus": ["央行购金与实际利率下行构成中期支撑"],
        "divergence": ["短期是否已经透支、会不会出现明显回调"],
        "summary": "中期有支撑，但短期位置不低；看多不追高，是今天的共识。",
    },
    {
        "topic": "外卖骑手的算法困局该怎么解",
        "guests": [
            ("host", "方宁", "深度报道记者", "中立主持"),
            ("expert", "韩磊", "外卖骑手、骑手站副站长", "派单规则不透明，时间越压越紧"),
            ("expert", "沈之遥", "某平台算法负责人", "系统在优化整体效率，也在给安全留缓冲"),
            ("expert", "顾云", "劳动法学研究者", "灵活用工关系的认定才是根问题"),
        ],
        "messages": [
            ("方宁", "我们来直面骑手和算法之间的矛盾。"),
            ("韩磊", "路线一改、时间一压，超时扣款就落到我们头上。"),
            ("沈之遥", "系统确实在不断放安全缓冲，但城市级效率优化天然有取舍。"),
            ("顾云", "比算法更重要的是用工关系怎么认定，这决定了谁来兜底。"),
        ],
        "consensus": ["算法需要更透明，也需要为安全和劳动者留缓冲"],
        "divergence": ["效率优化与劳动权益谁优先、用工关系如何认定"],
        "summary": "算法要透明、要留缓冲，但真正的根问题是用工关系的法律认定。",
    },
    {
        "topic": "短视频让人更聪明还是更笨",
        "guests": [
            ("host", "许诺", "文化评论节目主持人", "中立主持"),
            ("expert", "唐果", "认知心理学研究者", "碎片化输入削弱深度专注能力"),
            ("expert", "孟川", "知识类短视频创作者", "短视频是认知入口，深度学习靠个人选择"),
            ("expert", "阮星", "某中学教师", "学生的注意力时长确实在变短"),
        ],
        "messages": [
            ("许诺", "短视频到底让我们更聪明还是更笨？"),
            ("唐果", "高频切换的碎片输入，长期看是在侵蚀深度专注。"),
            ("孟川", "它是入口不是终点，有人刷到兴趣后会主动去读长内容。"),
            ("阮星", "从课堂观察看，学生的注意力时长确实在下降。"),
        ],
        "consensus": ["短视频本身是工具，关键在于怎么用、用多少"],
        "divergence": ["算法推荐是否系统性地削弱了深度思考能力"],
        "summary": "工具无对错，真正的变量是我们愿不愿意为自己保留深度时间。",
    },
    {
        "topic": "新能源汽车价格战会打到什么时候",
        "guests": [
            ("host", "高翔", "汽车产业节目主持人", "中立主持"),
            ("expert", "钱程", "某新势力车企产品总监", "规模不经济就出清，价格战会自我收敛"),
            ("expert", "许岚", "某动力电池厂销售总监", "电池成本下探给车企留了降价空间"),
            ("expert", "冯远", "汽车行业分析师", "头部品牌会借价格战完成洗牌"),
        ],
        "messages": [
            ("高翔", "这一轮价格战还要打多久？"),
            ("钱程", "没有规模效应的玩家撑不住，价格战会自我出清。"),
            ("许岚", "上游成本还在下探，车企手里确实还有牌。"),
            ("冯远", "头部正好借这一轮把尾部洗出去。"),
        ],
        "consensus": ["价格战会随尾部出清而收敛，行业走向集中"],
        "divergence": ["收敛的时点、以及是否会触发监管介入"],
        "summary": "价格战不是常态，它是行业洗牌的过程；出清之日，战端才停。",
    },
]


def main():
    init_db()
    db = SessionLocal()
    try:
        for s in SAMPLES:
            d = Discussion(topic=s["topic"], expert_count=len(s["guests"]) - 1,
                          status="ended", summary=s["summary"])
            db.add(d)
            db.flush()
            guest_by_name = {}
            for i, (role, name, title, stance) in enumerate(s["guests"]):
                color = HOST_COLOR if role == "host" else PALETTE[(i - 1) % len(PALETTE)]
                g = Guest(discussion_id=d.id, role=role, name=name, title=title,
                          stance=stance, color=color)
                db.add(g)
                guest_by_name[name] = g
            db.flush()  # assign guest ids before referencing them
            for name, content in s["messages"]:
                db.add(Message(discussion_id=d.id, guest_id=guest_by_name[name].id,
                               content=content, action="comment"))
            for c in s["consensus"]:
                db.add(Consensus(discussion_id=d.id, content=c))
            for x in s["divergence"]:
                db.add(Divergence(discussion_id=d.id, content=x))
        db.commit()
        print(f"Seeded {len(SAMPLES)} sample discussions.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
