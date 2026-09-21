# AI 圆桌演播厅 MVP

一个极简但有生产级质感的 AI 圆桌讨论演播厅：输入话题，后端用大模型自动生成「主持人 + 立场多元的专家阵容」，随后由导演循环驱动一场**非机械轮流**的讨论——主持人开场/追问/串联/总结，专家依据 transcript 自主决定发言（反驳/补充/追问），右侧实时沉淀共识与分歧，最后由主持人用自然语言收尾。

## 技术选型说明

| 层 | 选择 | 理由 |
|---|---|---|
| 后端 | FastAPI + SQLAlchemy | 异步友好、自带 OpenAPI、轻量 |
| 数据库 | SQLite | 零运维、单文件、满足单机 MVP |
| 实时通道 | SSE（Server-Sent Events） | 单向实时推送足够，比 WebSocket 简单可靠 |
| 前端 | 原生 HTML/CSS/ES Modules | 零构建、易部署，演播厅视觉靠 CSS 即可 |
| 大模型 | OpenAI 协议兼容客户端 | 同一套代码可接 DeepSeek / Moonshot / 本地 vLLM |
| 测试 | pytest + pytest-asyncio + httpx ASGI | 核心逻辑单测 + 端到端，FakeLLM 脚本化 |

## 目录结构

```
├── backend/
│   ├── main.py                # FastAPI 路由 + SSE + 静态托管
│   ├── database.py / models.py / schemas.py
│   ├── llm.py                 # LLM 客户端（Key 只在后端读环境变量）
│   ├── prompts.py              # 全部结构化 Prompt 集中在此
│   ├── eventbus.py            # 每场讨论独立的 SSE 订阅与 Agent 状态
│   └── agents/
│       ├── guest_generator.py      # 嘉宾阵容生成
│       ├── speaking_scheduler.py    # 发言调度（非机械轮流）
│       ├── consensus_extractor.py  # 实时共识/分歧提炼
│       ├── discussion_loop.py      # 异步导演循环
│       └── demo_llm.py             # 零 Key 离线演示模式
├── frontend/                  # index.html / studio.html / css / js
├── scripts/
│   ├── init_db.py             # 数据库初始化
│   └── seed_demo.py           # 写入 5 条预置样例讨论
├── docs/                      # PRD / ER / API / Prompt 记录 / 工作流
└── backend/tests/             # 单测 + E2E（FakeLLM）
```

## 运行指南

```bash
# 1. 安装依赖
python -m pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env

# 3. 初始化数据库 + 写入样例（可选）
python -m scripts.init_db
python -m scripts.seed_demo

# 4. 启动
python -m uvicorn backend.main:app --reload --port 8000
# 浏览器打开 http://127.0.0.1:8000
```

## 环境变量配置（.env）

| 变量 | 说明 | 默认 |
|---|---|---|
| `LLM_DEMO` | `1`=零 Key 离线演示；`0`=真实大模型 | `0` |
| `LLM_API_KEY` | 大模型 Key，**只在后端读取** | 无 |
| `LLM_BASE_URL` | OpenAI 兼容端点 | `https://api.deepseek.com` |
| `LLM_MODEL` | 模型名 | `deepseek-chat` |
| `LLM_WIRE_API` | `chat` 或 `responses`（兼容只支持 Responses 的本地中转） | `chat` |
| `LLM_TIMEOUT` | 单次请求超时秒数 | `90` |
| `LLM_MAX_RETRIES` | 自动重试次数 | `1` |

## 主要 API 列表

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/discussions` | 讨论列表 |
| POST | `/api/discussions` | body `{topic, expert_count}` → 生成阵容 |
| GET | `/api/discussions/{id}` | 讨论完整状态 |
| POST | `/api/discussions/{id}/start` | 启动导演循环 |
| GET | `/api/discussions/{id}/events` | SSE 事件流 |

事件类型：`history / agent_status / message / consensus / summary / status / error`。详见 `docs/API.md`。

## 已完成能力
- 首页列表 + 发起新讨论 + 加入观察；
- 大模型动态生成主持人+专家（姓名/Title/立场/专属颜色）；
- 非机械轮流发言、主持人追问串联、1–2 句控制；
- 专家三态小窗（待机/准备/发言中）+ 公开思考，不暴露 CoT；
- 实时共识/分歧提炼；Transcript 按颜色区分；
- 主持人自然语言总结；
- 多讨论并行隔离、SSE 实时推送、中文响应式 UI；
- 核心逻辑 TDD + E2E（含并行隔离测试）。

## 后续改进方向
- 支持观众发言/点赞等互动事件；
- 讨论时长与专家人数的 Prompt 自适应调参；
- 发言情绪/立场漂移的可视化；
- 持久化专家小窗历史状态；
- 接入 WebSocket 支持多人同时观察同一讨论的光标/焦点。

## 文档索引
- `docs/PRD.md` — 产品需求与架构（Mermaid）
- `docs/ER.md` — 数据模型与 ER 图（Mermaid）
- `docs/API.md` — 接口与事件说明
- `docs/PROMPTS.md` — 核心 Prompt 记录与阶段范式
- `docs/WORKFLOW.md` — 开发过程与工作流说明

## 运行测试
```bash
python -m pytest -q
```
