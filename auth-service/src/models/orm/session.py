from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from src.db.base import Base


class RefreshSession(Base):
    """
    Запись о refresh-сессии пользователя.
    Храним ХЭШ refresh-токена (не сам токен).
    """

    __tablename__ = "refresh_sessions"
    __table_args__ = (
        # часто ищем по user_id и сроку истечения
        Index("ix_refresh_sessions_user_expires", "user_id", "expires_at"),
        # ускоряем поиск по хэшу (точечная проверка при /refresh /logout)
        Index("ix_refresh_sessions_token_hash", "refresh_token_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)  # например, sha256 hex
    device: Mapped[str | None] = mapped_column(String(128))        # "iPhone 14", "Chrome/Win10"
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions", lazy="joined")