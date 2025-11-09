import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _auth_headers, _ensure_user, _login

pytestmark = pytest.mark.asyncio

# --- тесты ---
@pytest.mark.asyncio
async def test_change_login_success(make_post_request, make_post_request_headers):
    old_login = "chg_login_user_1"
    new_login = "chg_login_user_1_new"
    email = "chg_login_user_1@example.com"
    password = "secret123"

    await _ensure_user(make_post_request, old_login, email, password)
    access, _ = await _login(make_post_request, old_login, password)

    resp = await make_post_request_headers(
        "/auth/change-login",
        {"new_login": new_login},
        _auth_headers(access),
    )
    assert resp["status"] in (200, 204), resp
    if isinstance(resp["body"], dict) and resp["body"]:
        assert resp["body"].get("status") == "ok"

    # старый логин больше не работает
    resp_old = await make_post_request("/auth/login", {"login": old_login, "password": password})
    assert resp_old["status"] == 401, resp_old

    # новый работает
    resp_new = await make_post_request("/auth/login", {"login": new_login, "password": password})
    assert resp_new["status"] == 200, resp_new

# когда пользователь пытается сменить свой логин на уже занятый другим пользователем.
@pytest.mark.asyncio
async def test_change_login_conflict(make_post_request, make_post_request_headers):
    a_login, a_email, a_pw = "chg_login_user_A", "chg_login_user_A@example.com", "secret123"
    await _ensure_user(make_post_request, a_login, a_email, a_pw)
    a_access, _ = await _login(make_post_request, a_login, a_pw)

    b_login, b_email, b_pw = "chg_login_user_B", "chg_login_user_B@example.com", "secret123"
    await _ensure_user(make_post_request, b_login, b_email, b_pw)

    resp = await make_post_request_headers(
        "/auth/change-login",
        {"new_login": b_login},
        _auth_headers(a_access),
    )
    assert resp["status"] == 409, resp
    if isinstance(resp["body"], dict) and "detail" in resp["body"]:
        d = resp["body"]["detail"]
        if isinstance(d, dict):
            assert d.get("error") in ("login_taken", "conflict")

@pytest.mark.asyncio
async def test_change_login_unauthorized(make_post_request):
    resp = await make_post_request("/auth/change-login", {"new_login": "xxx"})
    assert resp["status"] in (401, 403), resp