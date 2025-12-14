from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    api_key: Mapped[str] = mapped_column(
        String(96), nullable=False, unique=True, index=True
    )

    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    branding_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    scripted_responses = relationship(
        "ScriptedResponse",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    quick_replies = relationship(
        "QuickReply",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    leads = relationship(
        "Lead",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    flows = relationship(
        "Flow",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    message_templates = relationship(
        "MessageTemplate",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    users = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_tenants_name", "name"),)
