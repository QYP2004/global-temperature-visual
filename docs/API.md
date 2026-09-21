# API 文档

Base URL：`http://127.0.0.1:8000`

## REST

### GET `/api/discussions`
讨论列表。
```json
[
  {
    "id": 1,
    "topic": "AI 会取代初级程序员吗",
    "expert_count": 3,
    "status": "ended",
    "message_count": 12,
    "created_at": "2026-09-21T02:35:46"
  }
]
```

### POST `/api/discussions`
发起新讨论（后端调用大模型生成阵容）。
- 请求体：`{"topic": string, "expert_count": int(2~6)}`
- 返回：完整讨论详情（含 `guests`），状态为 `pending`。

### GET `/api/discussions/{id}`
讨论完整状态：话题、状态、总结、嘉宾、全部发言、共识、分歧。

### POST `/api/discussions/{id}/start`
启动导演循环。已在运行时幂等返回。

## SSE：GET `/api/discussions/{id}/events`
`text/event-stream`。连接后先收到一条 `history`（全量回放），随后持续推送：

| event type | 含义 | 关键字段 |
|---|---|---|
| `history` | 新观众连入时的全量回放 | guests/messages/consensus/divergence/summary |
| `agent_status` | 各嘉宾小窗状态 | `statuses: {guest_id: {status, thought}}` |
| `message` | 一条新发言 | `message: {name, title, color, content, action}` |
| `consensus` | 最新共识/分歧快照 | `consensus: [], divergence: []` |
| `summary` | 主持人自然语言总结 | `summary: string` |
| `status` | 讨论状态变化 | `status: active|ended` |
| `error` | 非致命错误 | `message: string` |

## 错误约定
- `400`：话题为空等参数错误。
- `404`：讨论不存在。
- `502`：嘉宾生成失败（含大模型超时/Key 无效/连接失败的中文原因）。
