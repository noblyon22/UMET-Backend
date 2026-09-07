from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    model_config = {"extra": "ignore"}

    email: EmailStr
    full_name: str
    password: str
    currency: str = "UGX"


class UserUpdate(BaseModel):
    full_name: str | None = None
    currency: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    currency: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
