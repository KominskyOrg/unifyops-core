from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_id: Optional[UUID] = None
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    password_confirm: str

    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)
    password_confirm: Optional[str] = None

    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and values['password'] is not None and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserInDB(UserBase):
    id: UUID
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserResponse(UserInDB):
    full_name: str


# Authentication schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: UUID
    username: str
    organization_id: Optional[UUID] = None
    is_superuser: bool
    exp: Optional[int] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(..., min_length=8)
    password_confirm: str

    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


# Team assignment schemas
class UserTeamBase(BaseModel):
    team_id: UUID
    role: str


class UserTeamCreate(UserTeamBase):
    user_id: UUID


class UserTeamUpdate(BaseModel):
    role: Optional[str] = None


class UserTeamResponse(UserTeamBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    team_name: Optional[str] = None  # Added in the response by the API

    class Config:
        orm_mode = True 