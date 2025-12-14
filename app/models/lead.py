from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    phone_number: Mapped[str | None] = mapped_column(String(64), nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant = relationship("Tenant", back_populates="leads")

    chat_logs = relationship(
        "ChatLog",
        back_populates="lead",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_leads_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_leads_tenant_phone", "tenant_id", "phone_number"),
    )
