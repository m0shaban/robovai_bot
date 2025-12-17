"""
User model for SaaS authentication system.
Supports multi-tenant architecture with role-based access control.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class UserRole(str, enum.Enum):
    """User roles for RBAC"""

    SUPER_ADMIN = "super_admin"  # Platform owner - full access
    ADMIN = "admin"  # Tenant admin - full tenant access
    MANAGER = "manager"  # Can manage team & settings
    AGENT = "agent"  # Can handle chats & leads
    VIEWER = "viewer"  # Read-only access


class User(Base):
    """
    User model for SaaS authentication.
    - Multi-tenant: users can belong to a tenant (or be super_admin for all)
    - Role-based access control
    - Email verification & password reset support
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Role & Tenant (nullable for super_admin who has access to all)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=UserRole.AGENT,
        index=True,
    )
    tenant_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Email verification
    verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    verification_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Password reset
    reset_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="users")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"

    @property
    def is_super_admin(self) -> bool:
        """Check if user is super admin (platform owner)"""
        return self.role == UserRole.SUPER_ADMIN

    @property
    def can_manage_tenants(self) -> bool:
        """Check if user can create/manage tenants"""
        return self.role in (UserRole.SUPER_ADMIN,)

    @property
    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER)

    @property
    def can_manage_settings(self) -> bool:
        """Check if user can manage tenant settings"""
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER)

    @property
    def can_handle_chats(self) -> bool:
        """Check if user can handle customer chats"""
        return self.role in (
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.AGENT,
        )
