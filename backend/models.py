"""ORM models: Discussion / Guest / Message / Consensus / Divergence."""
import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def _now():
    return datetime.datetime.utcnow()


class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(Integer, primary_key=True)
    topic = Column(String, nullable=False)
    expert_count = Column(Integer, nullable=False)
    # pending = lineup generated, waiting for user confirm
    # active  = loop running
    # ended   = host delivered summary
    status = Column(String, default="pending", nullable=False)
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=_now)

    guests = relationship("Guest", back_populates="discussion", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="discussion", cascade="all, delete-orphan",
                            order_by="Message.id")
    consensus_items = relationship("Consensus", back_populates="discussion",
                                   cascade="all, delete-orphan", order_by="Consensus.id")
    divergence_items = relationship("Divergence", back_populates="discussion",
                                  cascade="all, delete-orphan", order_by="Divergence.id")


class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=False)
    role = Column(String, nullable=False)  # "host" | "expert"
    name = Column(String, nullable=False)
    title = Column(String, nullable=False, default="")
    stance = Column(String, nullable=False, default="")
    persona = Column(Text, default="")
    color = Column(String, nullable=False, default="#888888")

    discussion = relationship("Discussion", back_populates="guests")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=False)
    guest_id = Column(Integer, ForeignKey("guests.id"), nullable=False)
    content = Column(Text, nullable=False)
    action = Column(String, default="comment")  # comment|follow_up|rebuttal|supplement|summary
    created_at = Column(DateTime, default=_now)

    discussion = relationship("Discussion", back_populates="messages")
    guest = relationship("Guest")


class Consensus(Base):
    __tablename__ = "consensus"

    id = Column(Integer, primary_key=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now)

    discussion = relationship("Discussion", back_populates="consensus_items")


class Divergence(Base):
    __tablename__ = "divergence"

    id = Column(Integer, primary_key=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now)

    discussion = relationship("Discussion", back_populates="divergence_items")
