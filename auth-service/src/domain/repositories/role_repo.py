from __future__ import annotations
from sqlalchemy import select, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.orm import Role, User, user_roles

class RoleRepository:
    async def get_by_id(self, db: AsyncSession, role_id: str) -> Role | None:
        return await db.get(Role, role_id)
    
    async def get_by_name(self, db: AsyncSession, name: str) -> Role | None:
        return await db.scalar(select(Role).where(Role.name == name))

    async def create(self, db: AsyncSession, name: str, description: str | None) -> Role:
        role = Role(name=name, description=description)
        db.add(role)
        # commit делаем в сервисе, чтобы можно было обрабатывать ошибки
        return role
    
    async def delete(self, db: AsyncSession, role_id: str) -> bool:
        result = await db.execute(delete(Role).where(Role.id == role_id))
        await db.commit()
        return result.rowcount > 0
    
    async def assign_role(self, db: AsyncSession, user: User, role) -> bool:
        if any(r.id == role.id for r in user.roles):
            return False
        user.roles.append(role)
        db.add(user)
        return True
    
    async def remove_role_by_id(self, db: AsyncSession, user_id, role_id) -> int:
        res = await db.execute(
            delete(user_roles).where(
                and_(user_roles.c.user_id == user_id, user_roles.c.role_id == role_id)
            )
        )
        return res.rowcount or 0
    
    async def update_fields(
        self, db: AsyncSession, role: Role, *, name: str | None, description: str | None
    ) -> Role:
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        db.add(role)
        return role
    
    async def list(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,     # фильтр по части имени (опционально)
    ) -> tuple[list[Role], int]:
        offset = (page - 1) * page_size

        stmt = select(Role)
        if q:
            stmt = stmt.where(Role.name.ilike(f"%{q}%"))
        stmt = stmt.order_by(Role.name).offset(offset).limit(page_size)

        rows = (await db.execute(stmt)).scalars().all()

        if q:
            total = await db.scalar(select(func.count()).select_from(select(Role.id).where(Role.name.ilike(f"%{q}%")).subquery()))
        else:
            total = await db.scalar(select(func.count(Role.id)))

        return rows, int(total or 0)