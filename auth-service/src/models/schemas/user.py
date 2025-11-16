from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    login: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    first_name: str | None = Field(None, max_length=64)
    last_name: str | None = Field(None, max_length=64)
    model_config = ConfigDict(str_strip_whitespace=True)


class UserChangeLoginIn(BaseModel):
    new_login: str = Field(min_length=3, max_length=64)


class UserChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: UUID
    login: str
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserShort(BaseModel):
    id: UUID
    login: str
    model_config = ConfigDict(from_attributes=True)