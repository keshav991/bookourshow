from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: str | None = Field(default=None, max_length=150, description="User's full name")


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., description="User's password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    user_id: UUID
    email: str


class AuthMessageResponse(BaseModel):
    message: str
    user_id: UUID | None = None
