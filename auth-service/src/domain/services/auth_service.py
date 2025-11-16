from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Request

from src.domain.repositories.user_repo import UserRepository
from src.domain.repositories.role_repo import RoleRepository
from src.domain.repositories.session_repo import SessionRepository
from src.domain.repositories.audit_repo import AuditRepository

from src.core.security import hash_password, verify_password
from src.core.jwt import create_access_token, create_refresh_token, sha256_hex, decode_refresh
from src.core.ratelimit import check_login_ratelimit, bump_login_fail_counter, reset_login_counters
from src.core.refresh_cache import get_cached_session, cache_session, delete_cached_session

from src.models.schemas.auth import RefreshIn, TokenPair, LoginIn
from src.models.schemas.user import UserCreate, UserChangeLoginIn, UserChangePasswordIn
from src.models.schemas.audit import LoginHistoryPage, LoginEventOut

from src.models.orm import User
from src.models.orm.audit import LoginResult

from typing import Iterable


class AuthService:
    def __init__(self, user_repo: UserRepository, role_repo: RoleRepository, session_repo: SessionRepository, audit_repo: AuditRepository):
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.session_repo = session_repo
        self.audit_repo = audit_repo

    async def register(self, db: AsyncSession, payload: UserCreate) -> User:
        # уникальность логина / email
        if await self.user_repo.get_by_login(db, payload.login):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail={"error": "login_taken", "message": "Login is already in use"})
        if await self.user_repo.get_by_email(db, payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail={"error": "email_taken", "message": "Email is already in use"})

        # создать пользователя
        base_role = await self.role_repo.get_by_name(db, "user")  # может быть None
        user = await self.user_repo.create(
            db,
            login=payload.login.strip(),
            email=payload.email,
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            roles=[base_role] if base_role else None,
        )

        await db.commit()
        await db.refresh(user)
        return user
    
    async def login(self, db: AsyncSession, payload: LoginIn, request: Request) -> TokenPair:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

        # 0) rate limit до проверки пароля
        await check_login_ratelimit(ip, payload.login)

        # 1) проверка пользователя/пароля
        user = await self.user_repo.get_by_login(db, payload.login)
        if not user or not verify_password(payload.password, user.password_hash):
            # неудача → увеличиваем счётчик и отдаём 401
            # если логин не найден или пароль неверен:
            await self.audit_repo.add_login_event(
                db,
                user_id=user.id if user else None,
                ip_address=ip,
                user_agent=ua,
                result=LoginResult.fail,
                reason="bad credentials",
            )
            await db.commit()

            await bump_login_fail_counter(ip, payload.login)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_credentials", "message": "Invalid login or password"},
            )

        # успех → сбрасываем счётчики
        await reset_login_counters(ip, payload.login)

        roles = [r.name for r in user.roles] if user.roles else []

        # 2) токены
        access, ttl = create_access_token(str(user.id), roles)
        refresh, refresh_exp = create_refresh_token(str(user.id))

        # 3) сессия refresh (в БД храним ХЭШ)
        ua = request.headers.get("user-agent")
        device = None
        await self.session_repo.create(
            db,
            user_id=user.id,
            refresh_hash=sha256_hex(refresh),
            expires_at=refresh_exp,
            device=device, ip=ip, ua=ua,
        )

        # аудит успешного логина
        await self.audit_repo.add_login_event(
            db,
            user_id=user.id,
            ip_address=ip,
            user_agent=ua,
            result=LoginResult.success,
            reason=None,
        )

        await db.commit()

        return TokenPair(access=access, refresh=refresh, expires_in=ttl)
    
    async def refresh(self, db: AsyncSession, payload: RefreshIn, request: Request) -> TokenPair:
        # --- 1) оффлайн-проверка refresh
        claims = decode_refresh(payload.refresh)
        user_id = str(claims["sub"])
        old_hash = sha256_hex(payload.refresh)

        # --- 2) быстрая проверка в Redis
        cached = await get_cached_session(old_hash)
        if cached:
            if cached.get("revoked"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": "refresh_revoked", "message": "Refresh revoked"},
                )
            if cached.get("user_id") and cached["user_id"] != user_id:
                # крайне редкий случай несовпадения; перестрахуемся
                cached = None

        # --- 3) если в Redis промах — проверяем Postgres
        if not cached:
            sess = await self.session_repo.get_by_hash(db, token_hash=old_hash)
            if not sess:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": "refresh_invalid", "message": "Session not found"},
                )
            if sess.revoked:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": "refresh_revoked", "message": "Refresh revoked"},
                )
            if str(sess.user_id) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": "refresh_invalid", "message": "Token/user mismatch"},
                )
            # положим в кэш на будущее
            await cache_session(old_hash, user_id, sess.expires_at, revoked=False)

        # --- 4) берём актуальные роли (чтобы новый access содержал свежие права)
        user = await self.user_repo.get_by_id(db, user_id)
        roles = [r.name for r in (user.roles or [])] if user else []

        # --- 5) ротация: помечаем старую сессию как отозванную и убираем из Redis
        sess = await self.session_repo.get_by_hash(db, token_hash=old_hash)
        if sess and not sess.revoked:
            await self.session_repo.revoke(db, session_id=sess.id)
        await delete_cached_session(old_hash)

        # --- 6) выпускаем новую пару токенов
        access, access_ttl = create_access_token(user_id, roles)
        new_refresh, new_refresh_exp = create_refresh_token(user_id)

        # --- 7) сохраняем новую сессию (и кладём её в Redis)
        ua = request.headers.get("user-agent")
        ip = request.client.host if request.client else None

        await self.session_repo.create(
            db,
            user_id=user_id,
            refresh_hash=sha256_hex(new_refresh),
            expires_at=new_refresh_exp,
            device=None, ip=ip, ua=ua,
        )
        await cache_session(sha256_hex(new_refresh), user_id, new_refresh_exp, revoked=False)

        await db.commit()

        return TokenPair(access=access, refresh=new_refresh, expires_in=access_ttl)

    async def logout(self, db: AsyncSession, payload: RefreshIn, request: Request) -> None:
        # 1) оффлайн-проверка refresh JWT
        claims = decode_refresh(payload.refresh)

        # 2) хэш refresh для поиска записи и ключа в Redis
        refresh_hash = sha256_hex(payload.refresh)

        # 3) помечаем revoked в БД
        await self.session_repo.revoke_by_hash(db, token_hash=refresh_hash)
        await delete_cached_session(refresh_hash)
        await db.commit()

    async def change_login(self, db: AsyncSession, user_id: str, payload: UserChangeLoginIn):
        # 1) проверить, что логин свободен
        if await self.user_repo.get_by_login(db, payload.new_login):
            raise HTTPException(status_code=409, detail={"error": "login_taken", "message": "Login already in use"})
        # 2) обновить
        await self.user_repo.update_login(db, user_id, payload.new_login)
        await db.commit()
        return {"status": "ok"}
    
    async def change_password(self, db: AsyncSession, user_id: str, payload: UserChangePasswordIn):
        if payload.current_password == payload.new_password:
            raise HTTPException(status_code=400, detail={"error": "same_password", "message": "New password equals current"})

        user = await self.user_repo.get_by_id(db, user_id)
        if not user or not verify_password(payload.current_password, user.password_hash):
            # не раскрываем, что именно не так
            raise HTTPException(status_code=401, detail={"error": "invalid_credentials", "message": "Invalid password"})

        # 1) обновить хеш пароля
        new_hash = hash_password(payload.new_password)
        await self.user_repo.update_password_hash(db, user_id, new_hash)

        # 2) безопасность: отозвать все refresh-сессии пользователя (разлогинить везде)
        await self.session_repo.revoke_all_by_user(db, user_id)

        # 3) подчистить кэш refresh-сессий в Redis
        try:
            hashes: Iterable[str] = await self.session_repo.get_hashes_by_user(db, user_id)
            for h in hashes:
                await delete_cached_session(h)
        except Exception:
            # не валим запрос, если Redis недоступен
            pass

        await db.commit()
        return {"status": "ok"}

    async def login_history(self, db, user_id: str, page: int = 1, page_size: int = 20) -> LoginHistoryPage:
        rows, total = await self.audit_repo.list_user_logins(db, user_id, page=page, page_size=page_size)
        return LoginHistoryPage(
            items=[LoginEventOut.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )