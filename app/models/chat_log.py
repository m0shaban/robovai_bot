from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SenderType(str, enum.Enum):
    user = "user"
    bot = "bot"


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    lead_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(Text, nullable=False)

    sender_type: Mapped[SenderType] = mapped_column(
        Enum(SenderType, name="sender_type"),
        nullable=False,
    )

    timestamp: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    lead = relationship("Lead", back_populates="chat_logs")

    __table_args__ = (Index("ix_chat_logs_lead_ts", "lead_id", "timestamp"),)
