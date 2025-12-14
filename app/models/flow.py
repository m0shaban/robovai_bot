from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Flow(Base):
    __tablename__ = "flows"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # JSON structure: { "nodes": [...], "edges": [...] }
    flow_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    tenant = relationship("Tenant", back_populates="flows")

    __table_args__ = (
        Index("ix_flows_tenant_trigger", "tenant_id", "trigger_keyword"),
    )
