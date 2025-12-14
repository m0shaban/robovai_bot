from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ChannelType(str, enum.Enum):
    telegram = "telegram"
    whatsapp = "whatsapp"
    messenger = "messenger"
    instagram = "instagram"


class ChannelIntegration(Base):
    __tablename__ = "channel_integrations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # External identifier per channel:
    # - WhatsApp: phone_number_id
    # - Messenger: page_id
    # - Instagram: instagram business account id (or page id depending on setup)
    # - Telegram: optional (bot username), typically not required
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Access token / secret used to send messages back to the platform.
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification token used during webhook setup.
    verify_token: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint(
            "channel_type", "external_id", name="uq_channel_type_external_id"
        ),
        Index("ix_channel_integrations_tenant_type", "tenant_id", "channel_type"),
    )
