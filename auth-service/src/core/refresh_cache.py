import json
from datetime import datetime, timezone
from src.db import redis as redis_db

def _key(token_hash: str) -> str:
    return f"rsess:{token_hash}"

async def get_cached_session(token_hash: str):
    r = redis_db.redis
    if r is None:
        return None
    raw = await r.get(_key(token_hash))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data  # {"user_id": "...", "revoked": bool}
    except Exception:
        return None

async def cache_session(token_hash: str, user_id: str, expires_at: datetime, revoked: bool = False):
    r = redis_db.redis
    if r is None:
        return
    now = datetime.now(timezone.utc)
    ttl = max(0, int((expires_at - now).total_seconds()))
    if ttl <= 0:
        return
    payload = json.dumps({"user_id": user_id, "revoked": revoked})
    await r.setex(_key(token_hash), ttl, payload)

async def delete_cached_session(token_hash: str):
    r = redis_db.redis
    if r is None:
        return
    await r.delete(_key(token_hash))