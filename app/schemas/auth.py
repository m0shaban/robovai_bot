"""
Authentication schemas for request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


# ==================== Registration ====================


class UserRegisterRequest(BaseModel):
    """Schema for user registration"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("كلمة المرور يجب أن تكون 8 أحرف على الأقل")
        if not any(c.isupper() for c in v):
            raise ValueError("كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل")
        if not any(c.islower() for c in v):
            raise ValueError("كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل")
        if not any(c.isdigit() for c in v):
            raise ValueError("كلمة المرور يجب أن تحتوي على رقم واحد على الأقل")
        return v


class UserRegisterResponse(BaseModel):
    """Response after successful registration"""

    id: int
    email: str
    full_name: str
    message: str = "تم التسجيل بنجاح! يرجى التحقق من بريدك الإلكتروني"


# ==================== Login ====================


class UserLoginRequest(BaseModel):
    """Schema for user login"""

    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserLoginResponse(BaseModel):
    """Response after successful login"""

    user: "UserProfile"
    tokens: TokenResponse
    message: str = "تم تسجيل الدخول بنجاح"


# ==================== User Profile ====================


class UserProfile(BaseModel):
    """User profile data"""

    id: int
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile"""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=512)


# ==================== Password Management ====================


class PasswordChangeRequest(BaseModel):
    """Schema for changing password"""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("كلمة المرور يجب أن تكون 8 أحرف على الأقل")
        if not any(c.isupper() for c in v):
            raise ValueError("كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل")
        if not any(c.islower() for c in v):
            raise ValueError("كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل")
        if not any(c.isdigit() for c in v):
            raise ValueError("كلمة المرور يجب أن تحتوي على رقم واحد على الأقل")
        return v


class PasswordResetRequest(BaseModel):
    """Schema for requesting password reset"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for confirming password reset with token"""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("كلمة المرور يجب أن تكون 8 أحرف على الأقل")
        return v


# ==================== Email Verification ====================


class EmailVerificationRequest(BaseModel):
    """Schema for email verification"""

    token: str


class ResendVerificationRequest(BaseModel):
    """Schema for resending verification email"""

    email: EmailStr


# ==================== User Management (Admin) ====================


class UserCreateRequest(BaseModel):
    """Schema for admin creating a user"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    role: UserRole = UserRole.AGENT
    tenant_id: Optional[int] = None
    is_active: bool = True
    send_verification_email: bool = True


class UserUpdateRequest(BaseModel):
    """Schema for admin updating a user"""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    role: Optional[UserRole] = None
    tenant_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserListResponse(BaseModel):
    """Response for listing users"""

    users: list[UserProfile]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Invitation System ====================


class InviteUserRequest(BaseModel):
    """Schema for inviting a new user"""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = UserRole.AGENT
    tenant_id: Optional[int] = None


class AcceptInvitationRequest(BaseModel):
    """Schema for accepting an invitation"""

    token: str
    password: str = Field(..., min_length=8, max_length=128)


# Forward reference update
UserLoginResponse.model_rebuild()
