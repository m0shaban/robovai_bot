"""
Authentication service for SaaS platform.
Handles JWT tokens, sessions, and authentication logic.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
import logging

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from app.crud.user import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_reset_token,
    get_user_by_verification_token,
    generate_reset_token,
    generate_verification_token,
    update_last_login,
    update_user_password,
    verify_user_email,
    user_exists,
)
from app.models.user import User, UserRole
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserProfile,
    UserRegisterRequest,
    UserRegisterResponse,
)
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthError(Exception):
    """Authentication error with user-friendly message."""

    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# ==================== Token Generation ====================


def create_access_token(
    user_id: int,
    role: UserRole,
    tenant_id: Optional[int] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(user_id),
        "role": role.value,
        "tenant_id": tenant_id,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT refresh token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_token_pair(
    user: User,
    remember_me: bool = False,
) -> TokenResponse:
    """Create access + refresh token pair."""
    access_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=30 if remember_me else REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
        tenant_id=user.tenant_id,
        expires_delta=access_expires,
    )

    refresh_token = create_refresh_token(
        user_id=user.id,
        expires_delta=refresh_expires,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_expires.total_seconds()),
    )


# ==================== Token Verification ====================


def decode_token(token: str) -> dict:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise AuthError("رمز غير صالح أو منتهي الصلاحية", "INVALID_TOKEN")


def verify_access_token(token: str) -> dict:
    """Verify access token and return payload."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthError("نوع الرمز غير صحيح", "INVALID_TOKEN_TYPE")
    return payload


def verify_refresh_token(token: str) -> dict:
    """Verify refresh token and return payload."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise AuthError("نوع الرمز غير صحيح", "INVALID_TOKEN_TYPE")
    return payload


# ==================== Authentication Services ====================


async def register_user(
    session: AsyncSession,
    data: UserRegisterRequest,
    tenant_id: Optional[int] = None,
    role: UserRole = UserRole.AGENT,
    auto_verify: bool = True,  # Changed default to True to bypass email verification
    base_url: Optional[str] = None,
) -> UserRegisterResponse:
    """Register a new user and send verification email."""
    # Check if email exists
    if await user_exists(session, data.email):
        raise AuthError("البريد الإلكتروني مسجل مسبقاً", "EMAIL_EXISTS")

    # Create user
    user = await create_user(
        session,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        phone=data.phone,
        role=role,
        tenant_id=tenant_id,
        is_verified=auto_verify,
    )

    # Generate verification token and send email if not auto-verified
    email_sent = False
    if not auto_verify:
        token = await generate_verification_token(session, user)
        
        # Build verification URL
        app_base_url = base_url or settings.base_url
        verification_url = f"{app_base_url.rstrip('/')}/ui/auth/verify-email?token={token}"
        
        # Send verification email
        try:
            email_sent = await email_service.send_verification_email(
                to_email=user.email,
                verification_url=verification_url,
                user_name=user.full_name,
            )
            if email_sent:
                logger.info(f"✅ Verification email sent to {user.email}")
            else:
                logger.warning(f"⚠️ Could not send verification email to {user.email}")
                logger.info(f"[DEV] Verification URL: {verification_url}")
        except Exception as e:
            logger.error(f"❌ Failed to send verification email: {e}")
            logger.info(f"[DEV] Verification URL: {verification_url}")

    message = "تم التسجيل بنجاح!"
    if auto_verify:
        message += " يمكنك تسجيل الدخول الآن."
    elif email_sent:
        message += " تم إرسال رابط التفعيل إلى بريدك الإلكتروني."
    else:
        message += " يرجى التحقق من بريدك الإلكتروني أو طلب إعادة إرسال رابط التفعيل."

    return UserRegisterResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        message=message,
    )


async def login_user(
    session: AsyncSession,
    data: UserLoginRequest,
) -> UserLoginResponse:
    """Authenticate user and return tokens."""
    # Authenticate
    user = await authenticate_user(session, data.email, data.password)
    if not user:
        raise AuthError(
            "البريد الإلكتروني أو كلمة المرور غير صحيحة", "INVALID_CREDENTIALS"
        )

    # Check if verified (optional - can be disabled)
    # if not user.is_verified:
    #     raise AuthError("يرجى تأكيد بريدك الإلكتروني أولاً", "EMAIL_NOT_VERIFIED")

    # Update last login
    await update_last_login(session, user)

    # Create tokens
    tokens = create_token_pair(user, data.remember_me)

    # Build profile
    profile = UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        phone=user.phone,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=user.tenant.name if user.tenant else None,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login,
    )

    return UserLoginResponse(
        user=profile,
        tokens=tokens,
        message="تم تسجيل الدخول بنجاح",
    )


async def refresh_tokens(
    session: AsyncSession,
    refresh_token: str,
) -> TokenResponse:
    """Refresh access token using refresh token."""
    payload = verify_refresh_token(refresh_token)
    user_id = int(payload.get("sub"))

    user = await get_user_by_id(session, user_id)
    if not user or not user.is_active:
        raise AuthError("المستخدم غير موجود أو معطل", "USER_INVALID")

    return create_token_pair(user)


async def get_current_user(
    session: AsyncSession,
    token: str,
) -> User:
    """Get current user from access token."""
    payload = verify_access_token(token)
    user_id = int(payload.get("sub"))

    user = await get_user_by_id(session, user_id)
    if not user:
        raise AuthError("المستخدم غير موجود", "USER_NOT_FOUND")
    if not user.is_active:
        raise AuthError("الحساب معطل", "USER_INACTIVE")

    return user


# ==================== Password Reset ====================


async def request_password_reset(
    session: AsyncSession,
    email: str,
    base_url: Optional[str] = None,
) -> str:
    """Request password reset - sends email with reset link."""
    user = await get_user_by_email(session, email)
    if not user:
        # Don't reveal if email exists (security best practice)
        return "إذا كان البريد الإلكتروني مسجلاً، ستصلك رسالة لإعادة تعيين كلمة المرور"

    # Generate reset token
    token = await generate_reset_token(session, user)
    
    # Build reset URL
    app_base_url = base_url or settings.base_url
    reset_url = f"{app_base_url.rstrip('/')}/ui/auth/reset-password?token={token}"
    
    # Send password reset email
    try:
        email_sent = await email_service.send_password_reset_email(
            to_email=user.email,
            reset_url=reset_url,
            user_name=user.full_name,
        )
        if email_sent:
            logger.info(f"✅ Password reset email sent to {user.email}")
        else:
            logger.warning(f"⚠️ Could not send password reset email to {user.email}")
            logger.info(f"[DEV] Password reset URL: {reset_url}")
    except Exception as e:
        logger.error(f"❌ Failed to send password reset email: {e}")
        logger.info(f"[DEV] Password reset URL: {reset_url}")
    
    return "إذا كان البريد الإلكتروني مسجلاً، ستصلك رسالة لإعادة تعيين كلمة المرور"


async def reset_password(
    session: AsyncSession,
    token: str,
    new_password: str,
) -> str:
    """Reset password using token."""
    user = await get_user_by_reset_token(session, token)
    if not user:
        raise AuthError(
            "رمز إعادة التعيين غير صالح أو منتهي الصلاحية", "INVALID_RESET_TOKEN"
        )

    await update_user_password(session, user, new_password)
    return "تم تغيير كلمة المرور بنجاح"


# ==================== Email Verification ====================


async def verify_email(
    session: AsyncSession,
    token: str,
) -> str:
    """Verify email using token."""
    user = await get_user_by_verification_token(session, token)
    if not user:
        raise AuthError(
            "رمز التحقق غير صالح أو منتهي الصلاحية", "INVALID_VERIFICATION_TOKEN"
        )

    await verify_user_email(session, user)
    return "تم تأكيد البريد الإلكتروني بنجاح"


async def resend_verification(
    session: AsyncSession,
    email: str,
    base_url: Optional[str] = None,
) -> str:
    """Resend verification email."""
    user = await get_user_by_email(session, email)
    if not user:
        return "إذا كان البريد الإلكتروني مسجلاً، ستصلك رسالة التأكيد"

    if user.is_verified:
        return "البريد الإلكتروني مؤكد بالفعل"

    # Generate new verification token
    token = await generate_verification_token(session, user)
    
    # Build verification URL
    app_base_url = base_url or settings.base_url
    verification_url = f"{app_base_url.rstrip('/')}/ui/auth/verify-email?token={token}"
    
    # Send verification email
    try:
        email_sent = await email_service.send_verification_email(
            to_email=user.email,
            verification_url=verification_url,
            user_name=user.full_name,
        )
        if email_sent:
            logger.info(f"✅ Verification email resent to {user.email}")
            return "تم إرسال رسالة التأكيد إلى بريدك الإلكتروني"
        else:
            logger.warning(f"⚠️ Could not resend verification email to {user.email}")
            logger.info(f"[DEV] Verification URL: {verification_url}")
            return "حدث خطأ في إرسال البريد. حاول مرة أخرى."
    except Exception as e:
        logger.error(f"❌ Failed to resend verification email: {e}")
        logger.info(f"[DEV] Verification URL: {verification_url}")
        return "حدث خطأ في إرسال البريد. حاول مرة أخرى."


# ==================== Permission Checks ====================


def check_permission(
    user: User,
    required_role: UserRole,
    tenant_id: Optional[int] = None,
) -> bool:
    """Check if user has required permission."""
    # Super admin has all permissions
    if user.role == UserRole.SUPER_ADMIN:
        return True

    # Role hierarchy
    role_hierarchy = {
        UserRole.SUPER_ADMIN: 5,
        UserRole.ADMIN: 4,
        UserRole.MANAGER: 3,
        UserRole.AGENT: 2,
        UserRole.VIEWER: 1,
    }

    # Check role level
    if role_hierarchy.get(user.role, 0) < role_hierarchy.get(required_role, 0):
        return False

    # Check tenant access
    if tenant_id is not None and user.tenant_id != tenant_id:
        return False

    return True


def require_role(user: User, *roles: UserRole) -> None:
    """Require user to have one of the specified roles."""
    if user.role == UserRole.SUPER_ADMIN:
        return  # Super admin bypasses all checks

    if user.role not in roles:
        raise AuthError("ليس لديك صلاحية لهذا الإجراء", "PERMISSION_DENIED")


def require_tenant_access(user: User, tenant_id: int) -> None:
    """Require user to have access to specific tenant."""
    if user.role == UserRole.SUPER_ADMIN:
        return  # Super admin has access to all tenants

    if user.tenant_id != tenant_id:
        raise AuthError("ليس لديك صلاحية الوصول لهذا المشروع", "TENANT_ACCESS_DENIED")
