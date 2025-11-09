from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class LoginEventOut(BaseModel):
    id: UUID
    ts: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    result: str            # "success" | "fail"
    reason: str | None = None
    model_config = ConfigDict(from_attributes=True)

class LoginHistoryPage(BaseModel):
    items: list[LoginEventOut]
    total: int
    page: int
    page_size: int