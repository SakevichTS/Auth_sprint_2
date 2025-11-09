from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class RefreshSessionOut(BaseModel):
    id: UUID
    device: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    expires_at: datetime
    revoked: bool
    model_config = ConfigDict(from_attributes=True)