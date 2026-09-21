"""Per-discussion SSE event bus + in-memory agent status.

Each discussion has its own set of subscriber queues, so multiple concurrent
discussions are fully isolated.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Set


class EventBus:
    def __init__(self) -> None:
        self._subs: Dict[int, Set[asyncio.Queue]] = {}
        # disc_id -> guest_id -> {"status": "idle|preparing|speaking", "thought": str}
        self._status: Dict[int, Dict[int, dict]] = {}
        self._tasks: Dict[int, asyncio.Task] = {}

    # ---- subscriptions -------------------------------------------------
    def subscribe(self, disc_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subs.setdefault(disc_id, set()).add(q)
        return q

    def unsubscribe(self, disc_id: int, q: asyncio.Queue) -> None:
        subs = self._subs.get(disc_id)
        if subs and q in subs:
            subs.discard(q)
        if subs is not None and not subs:
            self._status.pop(disc_id, None)

    async def publish(self, disc_id: int, event: dict) -> None:
        for q in list(self._subs.get(disc_id, ())):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Drop oldest, push newest — never block the producer.
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass

    # ---- agent status -------------------------------------------------
    def set_status(self, disc_id: int, guest_id: int, status: str,
                   thought: str = "") -> None:
        self._status.setdefault(disc_id, {})[guest_id] = {
            "status": status, "thought": thought,
        }

    def snapshot_status(self, disc_id: int) -> Dict[int, dict]:
        return dict(self._status.get(disc_id, {}))

    # ---- background tasks ---------------------------------------------
    def register_task(self, disc_id: int, task: asyncio.Task) -> None:
        self._tasks[disc_id] = task

    def task_running(self, disc_id: int) -> bool:
        t = self._tasks.get(disc_id)
        return t is not None and not t.done()


bus = EventBus()
