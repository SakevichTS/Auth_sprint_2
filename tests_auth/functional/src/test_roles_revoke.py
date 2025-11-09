import pytest

from tests.functional.utils.helpers import _login, _auth_headers, _create_role_any, _ensure_user_and_get_id

pytestmark = pytest.mark.asyncio

ROLES_PATH = "/roles"
REVOKE_PATH = "/roles/revoke"
ASSIGN_PATH = "/roles/assign"

@pytest.mark.asyncio
async def test_roles_revoke_success(admin_access, make_post_request_headers, make_post_request):
    """
    Успешный отзыв роли:
    1) Создаём роль и пользователя.
    2) Назначаем роль пользователю.
    3) Отзываем роль -> 204.
    """
    headers = _auth_headers(admin_access)

    # создаём роль
    r = await _create_role_any(make_post_request_headers, headers, "role_to_revoke", "tmp")
    assert r["status"] in (201, 409), r
    role_id = r["body"]["id"] if r["status"] == 201 else (
        await _create_role_any(make_post_request_headers, headers, "role_to_revoke_u", "alt")
    )["body"]["id"]

    # создаём пользователя
    user_id = await _ensure_user_and_get_id(
        make_post_request, "user_revoke", "user_revoke@example.com", "secret123"
    )

    # назначаем роль пользователю
    assign = await make_post_request_headers(ASSIGN_PATH, {"user_id": user_id, "role_id": role_id}, headers)
    assert assign["status"] in (200, 204), assign

    # отзываем роль
    resp = await make_post_request_headers(REVOKE_PATH, {"user_id": user_id, "role_id": role_id}, headers)
    assert resp["status"] in (200, 204), resp


@pytest.mark.asyncio
async def test_roles_revoke_not_assigned(admin_access, make_post_request_headers, make_post_request):
    """
    Отзыв несуществующей роли у пользователя -> 404/400.
    """
    headers = _auth_headers(admin_access)

    # создаём пользователя
    u = await make_post_request("/auth/register", {
        "login": "user_no_role",
        "email": "user_no_role@example.com",
        "password": "secret123"
    })
    assert u["status"] in (201, 409), u
    user_id = u["body"]["id"]

    # пробуем отозвать случайную роль
    resp = await make_post_request_headers(REVOKE_PATH, {
        "user_id": user_id,
        "role_id": "00000000-0000-0000-0000-000000000000"
    }, headers)

    assert resp["status"] in (400, 404), resp


@pytest.mark.asyncio
async def test_roles_revoke_forbidden_for_non_admin(make_post_request, make_post_request_headers):
    """
    Обычный пользователь не может отзывать роли -> 403/401.
    """
    # создаём пользователя
    login, email, password = "revoke_noadmin", "revoke_noadmin@example.com", "secret123"
    u = await make_post_request("/auth/register", {"login": login, "email": email, "password": password})
    assert u["status"] in (201, 409), u
    user_id = u["body"]["id"]

    # логинимся
    access, _ = await _login(make_post_request, login, password)

    # пробуем отозвать
    resp = await make_post_request_headers(REVOKE_PATH, {
        "user_id": user_id,
        "role_id": "00000000-0000-0000-0000-000000000000"
    }, _auth_headers(access))

    assert resp["status"] in (401, 403), resp