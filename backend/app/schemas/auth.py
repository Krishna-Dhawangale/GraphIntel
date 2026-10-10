from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters long"
    )
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field("USER", description="Role: USER, ANALYST, or ADMIN")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str



class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    jti: Optional[str] = None
    role: Optional[str] = "USER"
    tenant_id: Optional[str] = None
    type: Optional[str] = "access"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, description="Reset token from email link")
    new_password: str = Field(..., min_length=8, description="New password, at least 8 characters")


class MessageResponse(BaseModel):
    message: str
