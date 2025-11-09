import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _login, _auth_headers, _ensure_user_and_get_id, _create_role_any

pytestmark = pytest.mark.asyncio

ROLES_BASE = "/roles"

@pytest.mark.asyncio
async def test_get_user_roles_success_after_assign(
    admin_access, make_post_request, make_post_request_headers, make_get_request_headers
):
    headers = _auth_headers(admin_access)

    r = await _create_role_any(make_post_request_headers, headers, "roles_view_role", "for view")
    assert r["status"] in (201, 409), r
    role_id = r["body"]["id"] if r["status"] == 201 else (
        await _create_role_any(make_post_request_headers, headers, "roles_view_role_u", "alt")
    )["body"]["id"]

    # создаём пользователя и берём его id
    user_id = await _ensure_user_and_get_id(make_post_request, "roles_view_user", "roles_view_user@example.com", "secret123")

    # назначаем роль
    a1 = await make_post_request_headers(f"{ROLES_BASE}/assign", {"user_id": user_id, "role_id": role_id}, headers)
    assert a1["status"] in (200, 204), a1

    # проверяем, что роль есть у пользователя
    resp = await make_get_request_headers(f"{ROLES_BASE}/{user_id}", headers=headers)
    assert resp["status"] == 200, resp
    roles = resp["body"]
    assert isinstance(roles, list), resp
    ids = {r["id"] for r in roles if "id" in r}
    assert role_id in ids, f"role {role_id} not found in {roles}"


@pytest.mark.asyncio
async def test_get_user_roles_not_found(
    admin_access,
    make_get_request_headers,
):
    """
    Несуществующий пользователь -> 404.
    """
    headers = _auth_headers(admin_access)
    fake_user = "00000000-0000-0000-0000-000000000000"
    resp = await make_get_request_headers(f"{ROLES_BASE}/{fake_user}", headers=headers)
    assert resp["status"] == 404 or resp["status"] == 200 and resp["body"].get("items") == [], resp

@pytest.mark.asyncio
async def test_get_user_roles_forbidden_for_non_admin(
    make_post_request,
    make_get_request_headers,
):
    """
    Обычный пользователь не должен видеть роли других пользователей -> 403/401.
    """
    # создаём обычного пользователя A
    a_login, a_email, pw = "roles_view_noadmin_a", "roles_view_noadmin_a@example.com", "secret123"
    ua = await make_post_request("/auth/register", {"login": a_login, "email": a_email, "password": pw})
    assert ua["status"] in (201, 409), ua
    # логинимся A
    a_access, _ = await _login(make_post_request, a_login, pw)

    # создаём другого пользователя B (чьи роли будем пытаться читать под A)
    b_login, b_email = "roles_view_noadmin_b", "roles_view_noadmin_b@example.com"
    ub = await make_post_request("/auth/register", {"login": b_login, "email": b_email, "password": pw})
    assert ub["status"] in (201, 409), ub
    if ub["status"] == 201:
        b_user_id = ub["body"]["id"]
    else:
        ub2 = await make_post_request("/auth/register", {"login": "roles_view_noadmin_b_u", "email": "roles_view_noadmin_b_u@example.com", "password": pw})
        assert ub2["status"] == 201, ub2
        b_user_id = ub2["body"]["id"]

    # пробуем GET /roles/{b_user_id} под A
    resp = await make_get_request_headers(f"{ROLES_BASE}/{b_user_id}", headers=_auth_headers(a_access))
    assert resp["status"] in (401, 403), resp