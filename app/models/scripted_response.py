from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScriptedResponse(Base):
    __tablename__ = "scripted_responses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    trigger_keyword: Mapped[str] = mapped_column(String(255), nullable=False)

    response_text: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    tenant = relationship("Tenant", back_populates="scripted_responses")

    __table_args__ = (
        Index(
            "ix_scripted_responses_tenant_trigger",
            "tenant_id",
            "trigger_keyword",
        ),
        Index(
            "ix_scripted_responses_tenant_active",
            "tenant_id",
            "is_active",
        ),
    )
