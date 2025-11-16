from typing import Annotated, Literal
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_async_session
from src.core.config import VkSettings, YandexSettings
from src.models.schemas.auth import RefreshIn
from src.domain.services.vk_service import VkService, get_vk_service
from src.domain.services.yand_service import YandexService, get_yandex_service

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

router = APIRouter()

vk_settings = VkSettings()
yandex_settings = YandexSettings()


@router.get("/login/vk", tags=["social"], summary="Callback vk site")
async def auth_vk(
    code: str,
    db: AsyncSession = Depends(get_async_session),
    service: VkService = Depends(get_vk_service),
):
    try:
        vk_logined = await service.login_vk_user(
            db, code, vk_settings.redirect_uri_login
        )
        return vk_logined
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout/vk", tags=["social"], summary="Logout from vk site")
async def logout_vk(
    payload: RefreshIn,
    db: AsyncSession = Depends(get_async_session),
    service: VkService = Depends(get_vk_service),
):
    try:
        await service.logout_vk_user(db, payload.refresh)
        return {"status": "refresh token revoked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/login/yandex", tags=["social"], summary="Callback yandex site")
async def auth_yandex(
    code: str,
    db: AsyncSession = Depends(get_async_session),
    service: YandexService = Depends(get_yandex_service),
):
    try:
        yand_logined = await service.login_yandex_user(
            db, code, yandex_settings.redirect_uri_login
        )
        return yand_logined
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout/yandex", tags=["social"], summary="Logout from yandex site")
async def logout_yandex(
    payload: RefreshIn,
    db: AsyncSession = Depends(get_async_session),
    service: YandexService = Depends(get_yandex_service),
):
    try:
        await service.logout_yandex_user(db, payload.refresh)
        return {"status": "refresh token revoked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
