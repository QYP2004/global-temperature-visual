"""Pydantic schemas for API responses."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class GuestOut(BaseModel):
    id: int
    role: str
    name: str
    title: str
    stance: str
    color: str

    class Config:
        from_attributes = True


class DiscussionSummaryOut(BaseModel):
    id: int
    topic: str
    expert_count: int
    status: str
    message_count: int
    created_at: str


class MessageOut(BaseModel):
    id: int
    guest_id: int
    name: str
    title: str
    color: str
    content: str
    action: str


class DiscussionDetailOut(BaseModel):
    id: int
    topic: str
    status: str
    summary: str
    guests: List[GuestOut]
    messages: List[MessageOut]
    consensus: List[str]
    divergence: List[str]


class CreateDiscussionIn(BaseModel):
    topic: str
    expert_count: int = 3
