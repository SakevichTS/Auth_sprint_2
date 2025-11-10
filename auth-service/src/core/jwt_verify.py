from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from src.core.config import settings

bearer = HTTPBearer(auto_error=True)


async def current_user_claims(
    cred: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    token = cred.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt.secret,            
            algorithms=[settings.jwt.algorithm],
            audience=settings.jwt.audience,
            issuer=settings.jwt.issuer,
        )
        return payload  # в payload уже есть sub, roles, exp и т.д.
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token_expired", "message": "Access token expired"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token_invalid", "message": "Invalid token"},
        )


def require_roles(*needed: str):
    def dep(claims: dict = Depends(current_user_claims)):
        roles = set(claims.get("roles", []))
        if roles.isdisjoint(needed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "forbidden"})
        return claims
    return dep
