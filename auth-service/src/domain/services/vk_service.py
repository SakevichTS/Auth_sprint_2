from dataclasses import dataclass
import aiohttp
from fastapi import Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import UserRepository, SessionRepository, get_user_repo, get_session_repo
from src.core.config import VkSettings
from src.core.jwt import create_access_token, create_refresh_token, sha256_hex
from src.core.security import hash_password

vk_settings = VkSettings()


def get_vk_service(
        user_manager: UserRepository = Depends(get_user_repo),
        session_manager: SessionRepository = Depends(get_session_repo)
) -> "VkService":
    return VkService(user_manager, session_manager)


@dataclass
class VkService:
    user_manager: UserRepository
    session_manager: SessionRepository

    async def get_vk_redirect(self, redirect_uri: str, state: str) -> RedirectResponse:
        url = (
            f"https://oauth.vk.com/authorize?"
            f"client_id={vk_settings.client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"state={state}&"
            f"scope=email"
        )
        return RedirectResponse(url, status_code=307)

    async def login_vk_user(self, db: AsyncSession, code: str, redirect_uri: str) -> dict:
        async with aiohttp.ClientSession() as session:
            data = {
                "client_id": vk_settings.client_id,
                "client_secret": vk_settings.client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            }
            async with session.post(vk_settings.token_url, data=data) as resp:
                token_resp = await resp.json()

        email = token_resp.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not returned by VK")

        user = await self.user_manager.get_by_email(db, email)
        if not user:
            password_hash = hash_password(email)
            user = await self.user_manager.create(
                db,
                login=email,
                email=email,
                password_hash=password_hash,
                first_name=None,
                last_name=None,
                roles=None,
            )
        access_token, _ = create_access_token(sub=str(user.id), roles=user.roles)
        refresh_token, refresh_exp = create_refresh_token(sub=str(user.id))

        await self.session_manager.create(
            db,
            user_id=user.id,
            refresh_hash=sha256_hex(refresh_token),
            expires_at=refresh_exp,
            device=None,
            ip=None,
            ua=None,
        )
        await db.commit()

        return {"access_token": access_token, "refresh_token": refresh_token, "email": email}

    async def logout_vk_user(self, db: AsyncSession, refresh_token: str) -> None:
        """Отзываем refresh token пользователя."""
        refresh_hash = sha256_hex(refresh_token)
        await self.session_manager.revoke_by_hash(db, token_hash=refresh_hash)
        await db.commit()
