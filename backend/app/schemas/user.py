from typing import Any, Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AuthenticatedUser(BaseModel):
    id: UUID
    email: str | None = None
    role: str = "customer"
    user_metadata: Dict[str, Any] = Field(default_factory=dict)
    app_metadata: Dict[str, Any] = Field(default_factory=dict)


class UserProfileResponse(BaseModel):
    id: UUID
    email: str | None = None
    full_name: str | None = None
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150, description="Updated full name")
