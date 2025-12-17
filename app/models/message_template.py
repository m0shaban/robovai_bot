from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TemplateCategory(str, enum.Enum):
    welcome = "welcome"  # ترحيب
    farewell = "farewell"  # وداع
    complaint = "complaint"  # شكاوى
    inquiry = "inquiry"  # استفسار
    promotion = "promotion"  # عروض
    support = "support"  # دعم فني
    payment = "payment"  # دفع
    shipping = "shipping"  # شحن
    general = "general"  # عام


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    category: Mapped[TemplateCategory] = mapped_column(
        Enum(TemplateCategory, name="template_category"),
        nullable=False,
        default=TemplateCategory.general,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional: variables that can be replaced like {customer_name}
    variables: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant = relationship("Tenant", back_populates="message_templates")

    __table_args__ = (
        Index("ix_message_templates_tenant_category", "tenant_id", "category"),
    )
