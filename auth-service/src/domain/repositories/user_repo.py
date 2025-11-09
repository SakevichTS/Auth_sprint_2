from __future__ import annotations
from sqlalchemy import select, inspect
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.orm import User, Role

from typing import Iterable

class UserRepository:
    async def get_by_id(self, db: AsyncSession, user_id: str) -> User | None:
        return await db.scalar(select(User).where(User.id == user_id))
    
    async def get_by_login(self, db: AsyncSession, login: str) -> User | None:
        return await db.scalar(select(User).where(User.login == login))

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        return await db.scalar(select(User).where(User.email == email))
    
    async def update_password_hash(self, db: AsyncSession, user_id: str, password_hash: str) -> None:
        user = await db.get(User, user_id)
        if user is None:
            return
        user.password_hash = password_hash
        await db.commit()

    async def update_login(self, db: AsyncSession, user_id: str, new_login: str) -> None:
            user = await db.get(User, user_id)
            if user is None:
                return
            user.login = new_login
            await db.commit()

    async def create(
        self,
        db: AsyncSession,
        *,
        login: str,
        email: str,
        password_hash: str,
        first_name: str | None,
        last_name: str | None,
        roles: Iterable[Role] | None = None,   # 👈 новые
    ) -> User:
        user = User(
            login=login,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )

        # ВАЖНО: добавляем роли ДО первого flush
        if roles:
            # гарантируем, что сами Role «в той же сессии»
            for r in roles:
                if inspect(r).session is not db:
                    db.add(r)
            # отключаем автофлаш на время модификации коллекции
            with db.no_autoflush:
                user.roles.extend(list(roles))

        db.add(user)
        # если нужен id — делаем flush здесь
        await db.flush()
        return user
    
    async def get_user_roles(self, db: AsyncSession, user_id: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.roles))  # заранее грузим roles
            .where(User.id == user_id)
        )
        return await db.scalar(stmt)