from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.repositories.role_repo import RoleRepository
from src.domain.repositories.user_repo import UserRepository
from src.models.schemas.user import UserOut
from src.models.schemas.role import RoleCreate, RoleOut, RoleUpdate, RolesPage

class RoleService:
    def __init__(self, user_repo: UserRepository, role_repo: RoleRepository):
        self.user_repo = user_repo
        self.role_repo = role_repo

    async def create_role(self, db: AsyncSession, payload: RoleCreate) -> RoleOut:
        try:
            role = await self.role_repo.create(db, payload.name, payload.description)
            await db.commit()
            await db.refresh(role)
            return RoleOut.model_validate(role)
        except IntegrityError:
            await db.rollback()
            # конфликт по UNIQUE(name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "role_exists", "message": "Role already exists"},
            )
        
    async def delete_role(self, db: AsyncSession, role_id: str) -> None:
        ok = await self.role_repo.delete(db, role_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Role not found")
        
    async def update_role(self, db: AsyncSession, role_id: str, payload: RoleUpdate) -> RoleOut:
        role = await self.role_repo.get_by_id(db, role_id)
        if not role:
            raise HTTPException(status_code=404, detail={"error": "role_not_found"})
        try:
            await self.role_repo.update_fields(
                db, role, name=payload.name, description=payload.description
            )
            await db.commit()
            await db.refresh(role)
            return RoleOut.model_validate(role)
        except IntegrityError:
            await db.rollback()
            # конфликт UNIQUE по name
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "role_exists", "message": "Role name already in use"},
            )
    
    async def revoke_role_by_id(self, db: AsyncSession, user_id, role_id) -> None:
        # Проверим, что пользователь и роль существуют — чтобы вернуть понятные ошибки
        user = await self.user_repo.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail={"error": "user_not_found"})

        role = await self.role_repo.get_by_id(db, role_id)
        if not role:
            raise HTTPException(status_code=404, detail={"error": "role_not_found"})

        deleted = await self.role_repo.remove_role_by_id(db, user_id, role_id)
        if deleted == 0:
            # Связи не было
            raise HTTPException(status_code=404, detail={"error": "not_assigned"})

        await db.commit()
        # ничего не возвращаем
        return None

    async def list_roles(self, db: AsyncSession, *, page: int = 1, page_size: int = 20, q: str | None = None) -> RolesPage:
        roles, total = await self.role_repo.list(db, page=page, page_size=page_size, q=q)
        return RolesPage(
            items=[RoleOut.model_validate(r) for r in roles],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def assign_role_by_id(self, db: AsyncSession, user_id, role_id) -> UserOut:
        user = await self.user_repo.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail={"error": "user_not_found"})

        role = await self.role_repo.get_by_id(db, role_id)
        if not role:
            raise HTTPException(status_code=404, detail={"error": "role_not_found"})

        added = await self.role_repo.assign_role(db, user, role)
        if not added:
            # уже назначена
            raise HTTPException(status_code=409, detail={"error": "already_assigned"})

        await db.commit()
        await db.refresh(user)
        return UserOut.model_validate(user)
    
    async def list_user_roles(self, db: AsyncSession, user_id: str) -> list[RoleOut]:
        user = await self.user_repo.get_user_roles(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail={"error": "user_not_found"})
        # user.roles уже в памяти — безопасно
        return [RoleOut.model_validate(r) for r in user.roles]