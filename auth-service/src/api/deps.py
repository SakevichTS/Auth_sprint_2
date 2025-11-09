from __future__ import annotations
from fastapi import Depends

from src.domain.repositories.user_repo import UserRepository
from src.domain.repositories.role_repo import RoleRepository
from src.domain.repositories.session_repo import SessionRepository
from src.domain.repositories.audit_repo import AuditRepository
from src.domain.services.auth_service import AuthService
from src.domain.services.role_service import RoleService

def get_user_repo() -> UserRepository:
    return UserRepository()

def get_role_repo() -> RoleRepository:
    return RoleRepository()

def get_session_repo() -> SessionRepository: 
    return SessionRepository()

def get_audit_repo() -> AuditRepository: 
    return AuditRepository()

def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    role_repo: RoleRepository = Depends(get_role_repo),
    session_repo: SessionRepository = Depends(get_session_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo)
) -> AuthService:
    return AuthService(user_repo, role_repo, session_repo, audit_repo)

def get_role_service(
    user_repo: UserRepository = Depends(get_user_repo),
    role_repo: RoleRepository = Depends(get_role_repo),
) -> RoleService:
    return RoleService(user_repo, role_repo)