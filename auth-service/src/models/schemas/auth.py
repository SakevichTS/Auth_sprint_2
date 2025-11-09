from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict

class LoginIn(BaseModel):
    login: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    model_config = ConfigDict(str_strip_whitespace=True)

class TokenPair(BaseModel):
    access: str
    refresh: str
    token_type: str = "bearer"
    expires_in: int | None = None

class RefreshIn(BaseModel):
    refresh: str

class MeOut(BaseModel):
    id: str
    login: str
    roles: list[str]