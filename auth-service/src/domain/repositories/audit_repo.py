from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.orm.audit import LoginAudit, LoginResult
from datetime import datetime, timezone

class AuditRepository:
    async def list_user_logins(self, db: AsyncSession, user_id: str, *, page: int, page_size: int):
        offset = (page - 1) * page_size

        q = (
            select(LoginAudit)
            .where(LoginAudit.user_id == user_id)
            .order_by(desc(LoginAudit.ts))
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(q)).scalars().all()

        total = await db.scalar(
            select(func.count()).select_from(
                select(LoginAudit.id).where(LoginAudit.user_id == user_id).subquery()
            )
        )
        return rows, int(total or 0)

    async def add_login_event(
        self,
        db: AsyncSession,
        *,
        user_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
        result: LoginResult,
        reason: str | None = None,
    ):
        row = LoginAudit(
            user_id=user_id,
            ts=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            result=result,
            reason=reason,
        )
        db.add(row)