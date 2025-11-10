from __future__ import annotations
from typing import Iterable
from src.db import redis
from src.core.config import settings
from fastapi import HTTPException, status


def _keys_for_login(ip: str | None, login: str) -> list[str]:
    keys = [f"rl:login:login:{login}"]
    if ip:
        keys.append(f"rl:login:ip:{ip}")
    return keys


async def check_login_ratelimit(ip: str | None, login: str) -> None:
    """Поднимаем 429, если порог превышен по ЛЮБОМУ ключу (ip или login)."""
    keys = _keys_for_login(ip, login)
    values = await redis.redis.mget(keys)  # ["3", None] и т.п.
    max_val = max((int(v) for v in values if v is not None), default=0)
    if max_val >= settings.ratelimit.login_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "message": "Too many login attempts. Try later."},
        )


async def bump_login_fail_counter(ip: str | None, login: str) -> None:
    """INCR + EXPIRE только если счётчик новый."""
    keys = _keys_for_login(ip, login)
    pipe = redis.redis.pipeline()
    for k in keys:
        pipe.incr(k)
        pipe.expire(k, settings.ratelimit.login_window_sec)
    await pipe.execute()


async def reset_login_counters(ip: str | None, login: str) -> None:
    keys = _keys_for_login(ip, login)
    await redis.redis.delete(*keys)