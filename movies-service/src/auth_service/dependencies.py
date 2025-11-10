from fastapi import Depends, Request, HTTPException, status
from auth_service.http_client import AuthServiceClient

auth_client = AuthServiceClient()


async def get_current_user(request: Request):
    """Проверяет токен и возвращает данные пользователя из auth-service."""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    return await auth_client.verify_token(token)
