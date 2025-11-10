from fastapi import Security, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_service.http_client import AuthServiceClient

auth_client = AuthServiceClient()
auth_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(auth_scheme)):
    """Проверяет токен и возвращает данные пользователя из auth-service."""
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    return await auth_client.verify_token(token)
