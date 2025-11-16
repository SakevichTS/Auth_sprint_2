from __future__ import annotations
import hashlib, uuid
from datetime import datetime, timedelta, timezone
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from src.core.config import settings
from fastapi import HTTPException, status


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_jti() -> str:
    return str(uuid.uuid4())


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_access_token(sub: str, roles: list[str]) -> tuple[str, int]:
    exp = now_utc() + timedelta(minutes=settings.jwt.access_ttl_min)
    payload = {
        "sub": sub,
        "roles": roles,
        "iss": settings.jwt.issuer,
        "aud": settings.jwt.audience,
        "iat": int(now_utc().timestamp()),
        "exp": int(exp.timestamp()),
        "jti": make_jti(),
    }
    token = jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)
    ttl = int((exp - now_utc()).total_seconds())
    return token, ttl


def create_refresh_token(sub: str) -> tuple[str, datetime]:
    exp = now_utc() + timedelta(days=settings.jwt.refresh_ttl_days)
    payload = {
        "sub": sub,
        "typ": "refresh",
        "iss": settings.jwt.issuer,
        "aud": settings.jwt.audience,
        "iat": int(now_utc().timestamp()),
        "exp": int(exp.timestamp()),
        "jti": make_jti(),
    }
    token = jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)
    return token, exp


def decode_refresh(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt.secret,
            algorithms=[settings.jwt.algorithm],
            audience=settings.jwt.audience,
            issuer=settings.jwt.issuer,
        )
        if payload.get("typ") != "refresh":
            # не тот тип токена
            raise JWTError("Wrong token type")
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token_expired", "message": "Refresh token expired"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token_invalid", "message": "Invalid refresh token"},
        )
