import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel
from core.config import Settings


settings = Settings()


class UserPayload(BaseModel):
    sub: str
    email: str | None = None
    roles: list[str] | None = None


class AuthServiceClient:
    """HTTP клиент для обращения к auth-service."""

    def __init__(self):
        # Используем URL авторизационного сервиса из .env
        self.base_url = settings.auth_service_url.rstrip("/")

    async def verify_token(self, token: str):
        """Проверка токена через эндпойнт /auth/verify."""
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/auth/verify", headers=headers)
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Auth service unavailable: {e}",
                )
            if response.status_code == 200:
                return response.json()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
