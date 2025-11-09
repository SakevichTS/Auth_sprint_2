from __future__ import annotations
from fastapi import APIRouter, Depends, status, Request, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_async_session
from src.api.deps import get_auth_service
from src.models.schemas.user import UserCreate, UserOut, UserChangeLoginIn, UserChangePasswordIn
from src.models.schemas.auth import LoginIn, TokenPair, RefreshIn
from src.core.jwt_verify import current_user_claims
from src.domain.services.auth_service import AuthService
from src.models.schemas.audit import LoginHistoryPage

router = APIRouter()

@router.post(
        "/register", 
        response_model=UserOut, 
        status_code=status.HTTP_201_CREATED,
        description="Регистрация нового пользователя. "
                "Создает учетную запись и возвращает данные о пользователе."
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
):
    return await service.register(db, payload)

@router.post(
        "/login", 
        response_model=TokenPair,
        description="Авторизация пользователя. "
                "Возвращает пару токенов (доступа и обновления)."
)
async def login(
    payload: LoginIn,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
):
    return await service.login(db, payload, request)

@router.post(
        "/refresh", 
        response_model=TokenPair,
        description="Обновление токенов. "
                "По refresh-токену выдает новую пару access/refresh."
)
async def refresh(
    payload: RefreshIn, 
    request: Request, 
    db: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
):
    return await service.refresh(db, payload, request)

@router.post(
        "/logout", 
        status_code=status.HTTP_204_NO_CONTENT, 
        response_class=Response,
        description="Выход из системы. "
                "Аннулирует текущий refresh-токен."
)
async def logout(
    payload: RefreshIn,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
):
    await service.logout(db, payload, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post(
        "/change-login", 
        status_code=status.HTTP_200_OK,
        description="Изменение логина пользователя. "
                "Требует авторизации."
)
async def change_login(
    payload: UserChangeLoginIn,
    db: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
    claims: dict = Depends(current_user_claims),  # достаём user_id из access токена
):
    user_id = claims["sub"]
    return await service.change_login(db, user_id, payload)

@router.post(
        "/change-password", 
        status_code=status.HTTP_200_OK,
        description="Изменение пароля пользователя. "
                "Требует авторизации."
)
async def change_password(
    payload: UserChangePasswordIn,
    db: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
    claims: dict = Depends(current_user_claims),
):
    user_id = claims["sub"]
    return await service.change_password(db, user_id, payload)

@router.get(
        "/login-history", 
        response_model=LoginHistoryPage,
        description="История входов пользователя. "
                "Возвращает список устройств, IP-адресов и времени входа."
)
async def login_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
    claims: dict = Depends(current_user_claims),
):
    user_id = claims["sub"]
    return await service.login_history(db, user_id, page=page, page_size=page_size)