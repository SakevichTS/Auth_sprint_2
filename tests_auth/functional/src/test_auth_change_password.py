import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _auth_headers, _ensure_user, _login

pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_change_password_success(make_post_request, make_post_request_headers):
    """
    1) Создаём пользователя и логинимся.
    2) Меняем пароль (нужен access).
    3) Старый пароль больше не подходит; новый — подходит.
    """
    login = "chg_pw_user_1"
    email = "chg_pw_user_1@example.com"
    old_pw = "secret123"
    new_pw = "secret456"

    await _ensure_user(make_post_request, login, email, old_pw)
    access, _ = await _login(make_post_request, login, old_pw)

    # смена пароля
    resp = await make_post_request_headers(
        "/auth/change-password",
        {"current_password": old_pw, "new_password": new_pw},
        _auth_headers(access),
    )
    assert resp["status"] in (200, 204), resp
    if isinstance(resp["body"], dict) and resp["body"]:
        assert resp["body"].get("status") == "ok"

    # старый пароль не работает
    resp_old = await make_post_request("/auth/login", {"login": login, "password": old_pw})
    assert resp_old["status"] == 401, resp_old

    # новый работает
    resp_new = await make_post_request("/auth/login", {"login": login, "password": new_pw})
    assert resp_new["status"] == 200, resp_new

@pytest.mark.asyncio
async def test_change_password_wrong_old(make_post_request, make_post_request_headers):
    """
    Неверный старый пароль => 400/401
    """
    login = "chg_pw_user_2"
    email = "chg_pw_user_2@example.com"
    real_pw = "secret123"
    bad_old = "WRONG_OLD"
    new_pw = "secret456"

    await _ensure_user(make_post_request, login, email, real_pw)
    access, _ = await _login(make_post_request, login, real_pw)

    resp = await make_post_request_headers(
        "/auth/change-password",
        {"current_password": bad_old, "new_password": new_pw},
        _auth_headers(access),
    )
    assert resp["status"] in (400, 401), resp
    # проверим, что пароль не поменялся: старый всё ещё работает
    still_ok = await make_post_request("/auth/login", {"login": login, "password": real_pw})
    assert still_ok["status"] == 200, still_ok

@pytest.mark.asyncio
async def test_change_password_unauthorized(make_post_request):
    """
    Без Authorization -> 401/403.
    """
    resp = await make_post_request(
        "/auth/change-password",
        {"current_password": "x", "new_password": "y"},
    )
    assert resp["status"] in (401, 403), resp