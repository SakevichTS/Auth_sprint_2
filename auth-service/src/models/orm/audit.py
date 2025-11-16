from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SAEnum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum

from src.db.base import Base


class LoginResult(str, Enum):
    success = "success"
    fail = "fail"


class LoginAudit(Base):
    """
    История входов (успешных/неуспешных) — полезно для /auth/me/logins.
    """
    __tablename__ = "login_audit"
    __table_args__ = (
        Index("ix_login_audit_user_ts", "user_id", "ts"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    result: Mapped[LoginResult] = mapped_column(SAEnum(LoginResult, name="login_result"), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))  # например: invalid_credentials, locked, rate_limited

    user: Mapped["User | None"] = relationship("User", back_populates="login_events", lazy="joined")
