import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _auth_headers, _ensure_user, _login

pytestmark = pytest.mark.asyncio

HISTORY_PATH = "/auth/login-history" 

@pytest.mark.asyncio
async def test_login_history_unauthorized(make_get_request):
    """Без авторизации должно вернуться 401/403."""
    resp = await make_get_request(HISTORY_PATH)
    assert resp["status"] in (401, 403), resp

@pytest.mark.asyncio
async def test_login_history_structure_and_events(make_post_request, make_get_request_headers):
    """
    1) Создаём пользователя.
    2) Делаем один неверный логин (fail) и один успешный (success).
    3) Запрашиваем историю: проверяем структуру и что есть хотя бы 'success' событие.
    """
    login = "hist_user_2"
    email = "hist_user_2@example.com"
    pw = "secret123"

    await _ensure_user(make_post_request, login, email, pw)

    # неуспешный логин (может записаться как fail)
    bad = await make_post_request("/auth/login", {"login": login, "password": "WRONGPW"})
    assert bad["status"] in (400, 401), bad

    # успешный логин
    access, _ = await _login(make_post_request, login, pw)

    # история c авторизацией
    resp = await make_get_request_headers(HISTORY_PATH, headers=_auth_headers(access))
    assert resp["status"] == 200, resp

    body = resp["body"]
    # проверяем форму ответа
    assert isinstance(body, dict), body
    assert "items" in body and isinstance(body["items"], list)
    assert "total" in body and isinstance(body["total"], int)
    assert "page" in body and "page_size" in body

    items = body["items"]
    assert len(items) >= 1
    assert body["total"] >= 1

    have_success = False
    have_fail = False

    for ev in items:
        # обязательные поля
        assert "id" in ev
        assert "ts" in ev
        assert "result" in ev  # "success" | "fail"
        # опциональные поля
        assert "ip_address" in ev
        assert "user_agent" in ev
        assert "reason" in ev

        res = str(ev["result"]).lower()
        if res == "success":
            have_success = True
        if res == "fail":
            have_fail = True

    # Минимальное требование — хотя бы одно успешное событие
    assert have_success, f"No 'success' events in: {items}"