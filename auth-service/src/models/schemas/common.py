from __future__ import annotations
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    message: str | None = None

class PageMeta(BaseModel):
    page: int
    size: int
    total: int

class PageRoles(BaseModel):
    items: list["RoleOut"]
    meta: PageMeta

from .role import RoleOut
PageRoles.model_rebuild()