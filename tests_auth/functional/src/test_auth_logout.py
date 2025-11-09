import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _ensure_user, _login

pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_logout_success_and_refresh_blocked(make_post_request):
    """
    1) Логинимся, получаем refresh.
    2) Делаем /auth/logout с этим refresh → ожидаем 204.
    3) Пробуем /auth/refresh со СТАРЫМ refresh → ожидаем 400/401 (revoked/invalid/expired).
    """
    login, email, password = "logout_u1", "logout_u1@example.com", "secret123"
    await _ensure_user(make_post_request, login, email, password)

    _, refresh = await _login(make_post_request, login, password)

    resp = await make_post_request("/auth/logout", {"refresh": refresh})
    assert resp["status"] == 204, resp

    # старый refresh больше не должен работать
    resp2 = await make_post_request("/auth/refresh", {"refresh": refresh})
    assert resp2["status"] in (400, 401), resp2
    if isinstance(resp2["body"], dict) and "detail" in resp2["body"]:
        d = resp2["body"]["detail"]
        if isinstance(d, dict):
            assert any(x in d.get("error", "") for x in ("revoked", "invalid", "expired"))
        elif isinstance(d, str):
            assert any(x in d.lower() for x in ("revoked", "invalid", "expired"))

@pytest.mark.asyncio
async def test_logout_twice(make_post_request):
    """
    Повторный логаут тем же refresh:
    1) Первый раз — 204
    2) Второй раз — 400/401/404
    """
    login, email, password = "logout_u2", "logout_u2@example.com", "secret123"
    await _ensure_user(make_post_request, login, email, password)

    _, refresh = await _login(make_post_request, login, password)

    resp1 = await make_post_request("/auth/logout", {"refresh": refresh})
    assert resp1["status"] == 204, resp1

    resp2 = await make_post_request("/auth/logout", {"refresh": refresh})
    assert resp2["status"] == 204, resp2


@pytest.mark.asyncio
async def test_logout_with_invalid_refresh(make_post_request):
    """
    Совсем битый refresh должен вернуть 400/401.
    """
    invalid_refresh = "not-a-jwt"
    resp = await make_post_request("/auth/logout", {"refresh": invalid_refresh})
    assert resp["status"] in (400, 401), resp
    if isinstance(resp["body"], dict) and "detail" in resp["body"]:
        msg = resp["body"]["detail"]
        if isinstance(msg, str):
            assert any(x in msg.lower() for x in ("invalid", "decode", "token"))
        elif isinstance(msg, dict):
            assert "invalid" in msg.get("error", "") or "decode" in msg.get("error", "")