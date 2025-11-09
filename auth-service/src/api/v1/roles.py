from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_async_session
from src.domain.services.role_service import RoleService
from src.api.deps import get_role_service
from src.core.jwt_verify import require_roles
from src.models.schemas.role import RoleCreate, RoleOut, RoleUpdate, RolesPage, AssignRoleByIdIn, RevokeRoleByIdIn
from src.models.schemas.user import UserOut

router = APIRouter()

@router.post(
        "/create", 
        response_model=RoleOut, 
        status_code=status.HTTP_201_CREATED, 
        dependencies=[Depends(require_roles("admin"))],
        description="Создание новой роли. Доступно только администраторам."
)
async def create_role(
    payload: RoleCreate,
    db: AsyncSession = Depends(get_async_session),
    service: RoleService = Depends(get_role_service),
):
    return await service.create_role(db, payload)

@router.delete(
        "/{role_id}", 
        status_code=status.HTTP_204_NO_CONTENT, 
        dependencies=[Depends(require_roles("admin"))],
        description="Удаление роли по ID. Доступно только администраторам."
)
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_async_session),
    service: RoleService = Depends(get_role_service),
):
    await service.delete_role(db, role_id)
    return None

@router.patch(
        "/{role_id}", 
        response_model=RoleOut, 
        dependencies=[Depends(require_roles("admin"))],
        description="Обновление информации о роли (например, названия). "
                "Доступно только администраторам."
)
async def update_role(
    role_id: str,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_async_session),
    service: RoleService = Depends(get_role_service),
):
    return await service.update_role(db, role_id, payload)

@router.get(
        "", 
        response_model=RolesPage, 
        dependencies=[Depends(require_roles("admin"))],
        description="Получение списка всех ролей. "
                "Доступно только администраторам."
)
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, description="Фильтр по имени роли"),
    db: AsyncSession = Depends(get_async_session),
    service: RoleService = Depends(get_role_service),
):
    return await service.list_roles(db, page=page, page_size=page_size, q=q)

@router.post(
        "/assign", 
        response_model=UserOut, 
        dependencies=[Depends(require_roles("admin"))],
        description="Назначение роли пользователю. "
                "Возвращает обновлённые данные пользователя. "
                "Доступно только администраторам."
)
async def assign_role(
    payload: AssignRoleByIdIn,
    db: AsyncSession = Depends(get_async_session),
    service: RoleService = Depends(get_role_service),
):
    return await service.assign_role_by_id(db, payload.user_id, payload.role_id)

@router.post(
        "/revoke", 
        status_code=status.HTTP_204_NO_CONTENT, 
        dependencies=[Depends(require_roles("admin"))],
        description="Отзыв (удаление) роли у пользователя. "
                "Доступно только администраторам."
)
async def revoke_role(
    payload: RevokeRoleByIdIn,
    db: AsyncSession = Depends(get_async_session),
    service: RoleService = Depends(get_role_service),
):
    await service.revoke_role_by_id(db, payload.user_id, payload.role_id)
    return None

@router.get(
        "/{user_id}", 
        response_model=list[RoleOut], 
        dependencies=[Depends(require_roles("admin"))],
        description="Получение списка ролей конкретного пользователя. "
                "Доступно только администраторам."
)
async def get_user_roles(
    user_id: str,
    db: AsyncSession = Depends(get_async_session),
    service: RoleService = Depends(get_role_service),
):
    return await service.list_user_roles(db, user_id)