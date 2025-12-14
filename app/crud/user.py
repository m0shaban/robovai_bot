"""
User CRUD operations for SaaS authentication.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole


# ==================== Create ====================

async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole = UserRole.AGENT,
    tenant_id: Optional[int] = None,
    phone: Optional[str] = None,
    is_verified: bool = False,
    is_active: bool = True,
) -> User:
    """Create a new user with hashed password."""
    user = User(
        email=email.lower().strip(),
        hashed_password=get_password_hash(password),
        full_name=full_name.strip(),
        role=role,
        tenant_id=tenant_id,
        phone=phone,
        is_verified=is_verified,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_super_admin(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
) -> User:
    """Create a super admin user (platform owner)."""
    return await create_user(
        session,
        email=email,
        password=password,
        full_name=full_name,
        role=UserRole.SUPER_ADMIN,
        tenant_id=None,
        is_verified=True,
        is_active=True,
    )


# ==================== Read ====================

async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> Optional[User]:
    """Get user by ID with tenant loaded."""
    result = await session.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.tenant))
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> Optional[User]:
    """Get user by email (case-insensitive)."""
    result = await session.execute(
        select(User)
        .where(User.email == email.lower().strip())
        .options(selectinload(User.tenant))
    )
    return result.scalar_one_or_none()


async def get_user_by_reset_token(
    session: AsyncSession,
    token: str,
) -> Optional[User]:
    """Get user by password reset token."""
    result = await session.execute(
        select(User)
        .where(
            User.reset_token == token,
            User.reset_token_expires > datetime.utcnow(),
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_verification_token(
    session: AsyncSession,
    token: str,
) -> Optional[User]:
    """Get user by email verification token."""
    result = await session.execute(
        select(User)
        .where(
            User.verification_token == token,
            User.verification_token_expires > datetime.utcnow(),
        )
    )
    return result.scalar_one_or_none()


async def list_users(
    session: AsyncSession,
    *,
    tenant_id: Optional[int] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[Sequence[User], int]:
    """List users with filters and pagination."""
    query = select(User).options(selectinload(User.tenant))
    count_query = select(func.count(User.id))
    
    # Apply filters
    if tenant_id is not None:
        query = query.where(User.tenant_id == tenant_id)
        count_query = count_query.where(User.tenant_id == tenant_id)
    
    if role is not None:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            or_(
                User.email.ilike(search_term),
                User.full_name.ilike(search_term),
            )
        )
        count_query = count_query.where(
            or_(
                User.email.ilike(search_term),
                User.full_name.ilike(search_term),
            )
        )
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await session.execute(query)
    users = result.scalars().all()
    
    return users, total


async def get_users_by_tenant(
    session: AsyncSession,
    tenant_id: int,
) -> Sequence[User]:
    """Get all users for a tenant."""
    result = await session.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.desc())
    )
    return result.scalars().all()


# ==================== Update ====================

async def update_user(
    session: AsyncSession,
    user: User,
    **kwargs,
) -> User:
    """Update user fields."""
    for key, value in kwargs.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_password(
    session: AsyncSession,
    user: User,
    new_password: str,
) -> User:
    """Update user password (hashes automatically)."""
    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await session.commit()
    await session.refresh(user)
    return user


async def update_last_login(
    session: AsyncSession,
    user: User,
) -> User:
    """Update user's last login timestamp."""
    user.last_login = datetime.utcnow()
    await session.commit()
    return user


async def verify_user_email(
    session: AsyncSession,
    user: User,
) -> User:
    """Mark user email as verified."""
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    await session.commit()
    await session.refresh(user)
    return user


# ==================== Token Generation ====================

async def generate_reset_token(
    session: AsyncSession,
    user: User,
    expires_hours: int = 24,
) -> str:
    """Generate password reset token."""
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=expires_hours)
    await session.commit()
    return token


async def generate_verification_token(
    session: AsyncSession,
    user: User,
    expires_hours: int = 48,
) -> str:
    """Generate email verification token."""
    token = secrets.token_urlsafe(32)
    user.verification_token = token
    user.verification_token_expires = datetime.utcnow() + timedelta(hours=expires_hours)
    await session.commit()
    return token


# ==================== Delete ====================

async def delete_user(
    session: AsyncSession,
    user: User,
) -> None:
    """Delete a user."""
    await session.delete(user)
    await session.commit()


async def deactivate_user(
    session: AsyncSession,
    user: User,
) -> User:
    """Soft delete - deactivate user instead of deleting."""
    user.is_active = False
    await session.commit()
    await session.refresh(user)
    return user


# ==================== Authentication Helpers ====================

async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    """Authenticate user by email and password."""
    user = await get_user_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def user_exists(
    session: AsyncSession,
    email: str,
) -> bool:
    """Check if user with email already exists."""
    result = await session.execute(
        select(func.count(User.id)).where(User.email == email.lower().strip())
    )
    return (result.scalar() or 0) > 0


async def count_super_admins(
    session: AsyncSession,
) -> int:
    """Count total super admins (for safety checks)."""
    result = await session.execute(
        select(func.count(User.id)).where(User.role == UserRole.SUPER_ADMIN)
    )
    return result.scalar() or 0
