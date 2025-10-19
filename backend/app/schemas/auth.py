from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=100)


class UserResponse(UserBase):
    id: str  # Changed from int to str for UUID
    is_active: bool
    is_verified: bool = False  # Added default value
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


# Session Schemas
class SessionCreate(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None


class SessionUpdate(BaseModel):
    is_active: Optional[bool] = None
    last_activity: Optional[datetime] = None
    device_info: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    access_token: str
    refresh_token: str
    is_active: bool
    created_at: datetime
    expires_at: datetime
    last_activity: Optional[datetime] = None
    device_info: Optional[str] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int
