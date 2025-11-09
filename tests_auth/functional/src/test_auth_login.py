import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _ensure_user

pytestmark = pytest.mark.asyncio

@pytest.mark.parametrize(
    "login,email,password",
    [
        ("login_u1", "login_u1@example.com", "secret123"),
        ("login_u2", "login_u2@example.com", "secret123"),
        ("login_u3", "login_u3@example.com", "secret123"),
    ],
)
async def test_login_success(make_post_request, login, email, password):
    # подготовим пользователя
    await _ensure_user(make_post_request, login, email, password)

    # логин
    resp = await make_post_request("/auth/login", {"login": login, "password": password})
    assert resp["status"] == 200, resp

    body = resp["body"]
    # базовые поля ответа
    assert "access" in body
    assert "refresh" in body
    assert body.get("token_type") == "bearer"
    assert isinstance(body.get("expires_in"), int)

async def test_login_wrong_password(make_post_request):
    login = "login_wrong_pw"
    email = "login_wrong_pw@example.com"
    good_pw = "secret123"
    bad_pw = "bad_secret"

    # подготовим пользователя
    await _ensure_user(make_post_request, login, email, good_pw)

    # неверный пароль
    resp = await make_post_request("/auth/login", {"login": login, "password": bad_pw})
    assert resp["status"] == 401, resp

async def test_login_unknown_user(make_post_request):
    resp = await make_post_request("/auth/login", {"login": "no_such_user", "password": "whatever"})
    assert resp["status"] == 401, resp

