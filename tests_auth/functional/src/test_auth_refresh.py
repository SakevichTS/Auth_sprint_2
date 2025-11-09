import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _ensure_user, _login

pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_refresh_success_and_rotation(make_post_request):
    login, email, password = "refresh_u1", "refresh_u1@example.com", "secret123"
    await _ensure_user(make_post_request, login, email, password)

    old_access, old_refresh = await _login(make_post_request, login, password)

    # 1) Успешный refresh
    resp = await make_post_request("/auth/refresh", {"refresh": old_refresh})
    assert resp["status"] == 200, resp
    body = resp["body"]
    assert "access" in body and "refresh" in body
    assert body.get("token_type") == "bearer"
    assert isinstance(body.get("expires_in"), int)

    new_access, new_refresh = body["access"], body["refresh"]
    # токены должны измениться (ротация jti)
    # успешная ротация и смена токенов;
	# запрет повторного использования старого refresh (revoked);
    assert new_access != old_access
    assert new_refresh != old_refresh

    # 2) Повторно вызвать refresh со СТАРЫМ refresh → должен быть отказ (ревокнут)
    resp2 = await make_post_request("/auth/refresh", {"refresh": old_refresh})
    assert resp2["status"] in (400, 401), resp2
    # допускаем разные сообщения в зависимости от реализации
    if isinstance(resp2["body"], dict) and "detail" in resp2["body"]:
        detail = resp2["body"]["detail"]
        # detail может быть строкой или объектом с error
        if isinstance(detail, dict):
            assert any(k in detail.get("error", "") for k in ("revoked", "invalid", "expired"))
        elif isinstance(detail, str):
            assert any(x in detail.lower() for x in ("revoked", "invalid", "expired"))

@pytest.mark.asyncio
async def test_refresh_invalid_token(make_post_request):
    # Совсем невалидный рефреш
    resp = await make_post_request("/auth/refresh", {"refresh": "not-a-jwt"})
    assert resp["status"] in (400, 401), resp
    if isinstance(resp["body"], dict) and "detail" in resp["body"]:
        msg = resp["body"]["detail"]
        if isinstance(msg, str):
            assert any(x in msg.lower() for x in ("invalid", "decode", "token"))
        elif isinstance(msg, dict):
            assert "invalid" in msg.get("error", "") or "decode" in msg.get("error", "")

@pytest.mark.asyncio
async def test_refresh_twice_new_token_works(make_post_request):
    """
    цепочка ротация -> ротация и проверка, что предыдущий каждый раз становится недействителен.
    """
    login, email, password = "refresh_u2", "refresh_u2@example.com", "secret123"
    await _ensure_user(make_post_request, login, email, password)

    _, r1 = await _login(make_post_request, login, password)

    # первая ротация
    resp1 = await make_post_request("/auth/refresh", {"refresh": r1})
    assert resp1["status"] == 200, resp1
    r2 = resp1["body"]["refresh"]

    # старый r1 — больше не работает
    resp_old = await make_post_request("/auth/refresh", {"refresh": r1})
    assert resp_old["status"] in (400, 401), resp_old

    # вторая ротация — с r2
    resp2 = await make_post_request("/auth/refresh", {"refresh": r2})
    assert resp2["status"] == 200, resp2
    r3 = resp2["body"]["refresh"]
    assert r3 != r2