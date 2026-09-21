"""FastAPI entry: REST API + SSE + static frontend."""
from __future__ import annotations

import asyncio
import json
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import schemas
from .agents import guest_generator
from .agents.discussion_loop import start_or_restart
from .database import get_db, init_db
from .eventbus import bus
from .llm import configure_llm
from .models import Consensus, Discussion, Divergence, Guest, Message

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = FastAPI(title="AI 圆桌演播厅")


@app.on_event("startup")
def _startup():
    init_db()
    configure_llm()


# ---------- helpers -------------------------------------------------------
def _discussion_detail(d: Discussion) -> dict:
    return {
        "id": d.id,
        "topic": d.topic,
        "status": d.status,
        "summary": d.summary or "",
        "guests": [
            {"id": g.id, "role": g.role, "name": g.name, "title": g.title,
             "stance": g.stance, "color": g.color}
            for g in d.guests
        ],
        "messages": [
            {"id": m.id, "guest_id": m.guest_id, "name": m.guest.name,
             "title": m.guest.title, "color": m.guest.color,
             "content": m.content, "action": m.action}
            for m in d.messages
        ],
        "consensus": [c.content for c in d.consensus_items],
        "divergence": [x.content for x in d.divergence_items],
    }


# ---------- REST ----------------------------------------------------------
@app.get("/api/discussions")
def list_discussions(db: Session = Depends(get_db)):
    rows = (db.query(Discussion)
            .order_by(Discussion.id.desc()).all())
    out = []
    for d in rows:
        out.append({
            "id": d.id,
            "topic": d.topic,
            "expert_count": d.expert_count,
            "status": d.status,
            "message_count": db.query(Message).filter_by(discussion_id=d.id).count(),
            "created_at": d.created_at.isoformat(),
        })
    return out


@app.post("/api/discussions")
async def create_discussion(body: schemas.CreateDiscussionIn,
                            db: Session = Depends(get_db)):
    from .llm import get_llm

    if not body.topic.strip():
        raise HTTPException(400, "话题不能为空")
    try:
        lineup = await guest_generator.generate_lineup(
            body.topic, body.expert_count, llm=get_llm()
        )
    except Exception as exc:
        raise HTTPException(502, f"嘉宾生成失败：{exc}")

    d = Discussion(topic=body.topic.strip(), expert_count=body.expert_count,
                   status="pending")
    db.add(d)
    db.flush()

    host = lineup["host"]
    db.add(Guest(discussion_id=d.id, role="host", name=host["name"],
                 title=host["title"], stance="中立主持", persona=host.get("persona", ""),
                 color=host["color"]))
    for e in lineup["experts"]:
        db.add(Guest(discussion_id=d.id, role="expert", name=e["name"],
                     title=e["title"], stance=e["stance"],
                     persona=e.get("persona", ""), color=e["color"]))
    db.commit()
    db.refresh(d)
    return _discussion_detail(d)


@app.get("/api/discussions/{disc_id}")
def get_discussion(disc_id: int, db: Session = Depends(get_db)):
    d = db.query(Discussion).get(disc_id)
    if d is None:
        raise HTTPException(404, "讨论不存在")
    return _discussion_detail(d)


@app.post("/api/discussions/{disc_id}/start")
async def start_discussion(disc_id: int, db: Session = Depends(get_db)):
    d = db.query(Discussion).get(disc_id)
    if d is None:
        raise HTTPException(404, "讨论不存在")
    if d.status == "active":
        return {"ok": True, "already_running": True}
    ok = start_or_restart(disc_id)
    return {"ok": ok}


# ---------- SSE -----------------------------------------------------------
@app.get("/api/discussions/{disc_id}/events")
async def events(disc_id: int, db: Session = Depends(get_db)):
    d = db.query(Discussion).get(disc_id)
    if d is None:
        raise HTTPException(404, "讨论不存在")

    q = bus.subscribe(disc_id)

    async def gen():
        # 1) Replay current state so a late joiner sees the whole picture.
        state = _discussion_detail(d)
        yield f"data: {json.dumps({'type': 'history', **state}, ensure_ascii=False)}\n\n"
        # 2) Send current agent windows.
        yield f"data: {json.dumps({'type': 'agent_status', 'statuses': bus.snapshot_status(disc_id)}, ensure_ascii=False)}\n\n"
        # 3) Live events.
        try:
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat to keep the connection alive.
                    yield ": ping\n\n"
        finally:
            bus.unsubscribe(disc_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


# ---------- static frontend ----------------------------------------------
@app.get("/")
def home():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/studio")
def studio():
    return FileResponse(os.path.join(FRONTEND_DIR, "studio.html"))


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
