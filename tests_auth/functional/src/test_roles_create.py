import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _ensure_user, _login, _auth_headers

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_roles_create_success(admin_access, make_post_request_headers):
    """
    Админ создаёт роль: 201 и корректное тело.
    """
    name = "role_create_ok"
    desc = "created by tests"

    resp = await make_post_request_headers(
        "/roles/create",
        {"name": name, "description": desc},
        _auth_headers(admin_access),
    )
    assert resp["status"] == 201, resp

    body = resp["body"]
    assert isinstance(body, dict), body
    assert "id" in body
    assert body.get("name") == name
    if "description" in body:
        assert body["description"] == desc


@pytest.mark.asyncio
async def test_roles_create_conflict(admin_access, make_post_request_headers):
    """
    Повторное создание роли с тем же именем -> 409.
    """
    name = "role_create_conflict"

    first = await make_post_request_headers(
        "/roles/create",
        {"name": name, "description": "dup"},
        _auth_headers(admin_access),
    )
    assert first["status"] in (201, 409), first  # если тест гоняется повторно

    second = await make_post_request_headers(
        "/roles/create",
        {"name": name, "description": "dup2"},
        _auth_headers(admin_access),
    )
    assert second["status"] == 409, second
    if isinstance(second["body"], dict) and "detail" in second["body"]:
        d = second["body"]["detail"]
        if isinstance(d, dict) and "error" in d:
            assert d["error"] in ("role_exists", "conflict")


@pytest.mark.asyncio
async def test_roles_create_forbidden_for_non_admin(make_post_request, make_post_request_headers):
    """
    Обычный пользователь не может создавать роли -> 403 (или 401).
    """
    login = "roles_noadmin_u1"
    email = "roles_noadmin_u1@example.com"
    password = "secret123"

    await _ensure_user(make_post_request, login, email, password)
    access, _ = await _login(make_post_request, login, password)

    resp = await make_post_request_headers(
        "/roles/create",
        {"name": "should_fail"},
        _auth_headers(access),
    )
    assert resp["status"] in (403, 401), resp