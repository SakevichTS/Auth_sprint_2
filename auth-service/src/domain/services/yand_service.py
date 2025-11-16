from dataclasses import dataclass

import aiohttp
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.responses import RedirectResponse

from src.core.config import YandexSettings
from src.api.deps import UserRepository, SessionRepository, get_user_repo, get_session_repo
from src.core.jwt import (
    create_access_token,
    create_refresh_token,
    sha256_hex,
)
from src.core.security import hash_password


yandex_settings = YandexSettings()


def get_yandex_service(
    user_manager: UserRepository = Depends(get_user_repo),
    session_manager: SessionRepository = Depends(get_session_repo)
) -> "YandexService":
    return YandexService(user_manager, session_manager)


@dataclass
class YandexService:
    user_manager: UserRepository
    session_manager: SessionRepository

    async def get_yandex_redirect(self, redirect_uri: str, state: str) -> RedirectResponse:
        url = (
            f"https://oauth.yandex.ru/authorize?"
            f"response_type=code&"
            f"client_id={yandex_settings.client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}"
        )
        return RedirectResponse(url, status_code=307)

    async def exchange_code_for_token(self, code: str) -> str:
        """Обмениваем code → access_token Яндекса."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": yandex_settings.client_id,
            "client_secret": yandex_settings.client_secret,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(yandex_settings.token_url, data=data) as resp:
                token_resp = await resp.json()

        access_token = token_resp.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail=f"Yandex token exchange error: {token_resp}"
            )

        return access_token

    async def get_yandex_user_info(self, access_token: str) -> dict:
        headers = {"Authorization": f"OAuth {access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(yandex_settings.user_info_url, headers=headers) as resp:
                return await resp.json()

    async def login_yandex_user(self, db: AsyncSession, code: str, redirect_uri: str) -> dict:
        """Логин через Яндекс."""
        access_token = await self.exchange_code_for_token(code)
        user_info = await self.get_yandex_user_info(access_token)

        email = user_info.get("default_email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not returned by Yandex")

        user = await self.user_manager.get_by_email(db, email)

        if not user:
            password_hash = hash_password(email)
            user = await self.user_manager.create(
                db,
                login=email,
                email=email,
                password_hash=password_hash,
                first_name=user_info.get("first_name"),
                last_name=user_info.get("last_name"),
                roles=None,
            )

        access, _ = create_access_token(sub=str(user.id), roles=user.roles)
        refresh, refresh_exp = create_refresh_token(sub=str(user.id))

        await self.session_manager.create(
            db,
            user_id=user.id,
            refresh_hash=sha256_hex(refresh),
            expires_at=refresh_exp,
            device=None,
            ip=None,
            ua=None,
        )
        await db.commit()

        return {
            "email": email,
            "access_token": access,
            "refresh_token": refresh,
        }

    async def logout_yandex_user(self, db: AsyncSession, refresh_token: str) -> None:
        refresh_hash = sha256_hex(refresh_token)
        await self.session_manager.revoke_by_hash(db, token_hash=refresh_hash)
        await db.commit()
