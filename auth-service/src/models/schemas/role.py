from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    description: str | None = Field(None, max_length=255)
    model_config = ConfigDict(from_attributes=True)

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    model_config = ConfigDict(str_strip_whitespace=True)

class RoleOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)

class RolesPage(BaseModel):
    items: list[RoleOut]
    total: int
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

class AssignRoleByIdIn(BaseModel):
    user_id: UUID
    role_id: UUID

class RevokeRoleByIdIn(BaseModel):
    user_id: UUID
    role_id: UUID