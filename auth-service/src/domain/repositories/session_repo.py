from __future__ import annotations
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.models.orm import RefreshSession
from datetime import datetime, timezone

class SessionRepository:
    async def create(self, db: AsyncSession, *, user_id, refresh_hash: str,
                     expires_at: datetime, device: str | None, ip: str | None, ua: str | None) -> RefreshSession:
        now = datetime.now(timezone.utc)
        row = RefreshSession(
            user_id=user_id,
            refresh_token_hash=refresh_hash,
            device=device, 
            ip_address=ip, 
            user_agent=ua,
            expires_at=expires_at,
            revoked=False,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return row
    
    async def get_by_hash(self, db: AsyncSession, *, token_hash: str) -> RefreshSession | None:
        stmt = select(RefreshSession).where(RefreshSession.refresh_token_hash == token_hash)
        return await db.scalar(stmt)

    async def revoke(self, db: AsyncSession, *, session_id):
        await db.execute(
            update(RefreshSession)
            .where(RefreshSession.id == session_id)
            .values(revoked=True, updated_at=datetime.now(timezone.utc))
        )

    async def revoke_by_hash(self, db: AsyncSession, *, token_hash: str):
        await db.execute(
            update(RefreshSession)
            .where(RefreshSession.refresh_token_hash == token_hash)
            .values(revoked=True, updated_at=datetime.now(timezone.utc))
        )
    
    # чтобы разлогинить при смене пароля
    async def revoke_all_by_user(self, db: AsyncSession, user_id: str) -> None:
        await db.execute(
            update(RefreshSession).where(RefreshSession.user_id == user_id, RefreshSession.revoked == False)
                                   .values(revoked=True)
        )
    
    # для подсчета количества сессий
    async def get_hashes_by_user(self, db: AsyncSession, user_id: str) -> list[str]:
        rows = await db.execute(select(RefreshSession.refresh_token_hash).where(RefreshSession.user_id == user_id))
        return [r[0] for r in rows.fetchall()]