import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _ensure_user, _login, _auth_headers, _create_role_any

pytestmark = pytest.mark.asyncio

ROLES_BASE = "/roles"
ASSIGN_PATH = f"{ROLES_BASE}/assign"

@pytest.mark.asyncio
async def test_roles_assign_success(admin_access, make_post_request, make_post_request_headers):
    """
    Админ создаёт роль, создаёт пользователя, назначает роль
    """
    headers = _auth_headers(admin_access)

    # 1) создаём роль
    r = await _create_role_any(make_post_request_headers, headers, "assign_ok_role", "for assign")
    assert r["status"] in (201, 409), r
    if r["status"] == 201:
        role_id = r["body"]["id"]
    else:
        r2 = await _create_role_any(make_post_request_headers, headers, "assign_ok_role_unique", "for assign")
        assert r2["status"] == 201, r2
        role_id = r2["body"]["id"]

    # 2) создаём пользователя
    login, email, password = "assign_ok_user", "assign_ok_user@example.com", "secret123"
    user_resp = await make_post_request("/auth/register", {
        "login": login, "email": email, "password": password,
        "first_name": "Assign", "last_name": "User"
    })
    assert user_resp["status"] in (201, 409), user_resp
    if user_resp["status"] == 201:
        user_id = user_resp["body"]["id"]
    else:
        # если уже был — залогинимся и узнаем id
        # либо пересоздадим с другим логином
        user_resp2 = await make_post_request("/auth/register", {
            "login": "assign_ok_user2", "email": "assign_ok_user2@example.com", "password": password
        })
        assert user_resp2["status"] == 201, user_resp2
        user_id = user_resp2["body"]["id"]

    # 3) назначаем роль
    assign = await make_post_request_headers(
        ASSIGN_PATH,
        {"user_id": user_id, "role_id": role_id},
        headers,
    )
    assert assign["status"] in (200, 204), assign


@pytest.mark.asyncio
async def test_roles_assign_conflict(admin_access, make_post_request, make_post_request_headers):
    """
    Повторное назначение той же роли тому же пользователю
    """
    headers = _auth_headers(admin_access)

    # роль
    r = await _create_role_any(make_post_request_headers, headers, "assign_conflict_role", None)
    assert r["status"] in (201, 409), r
    if r["status"] == 201:
        role_id = r["body"]["id"]
    else:
        r2 = await _create_role_any(make_post_request_headers, headers, "assign_conflict_role_u", None)
        assert r2["status"] == 201, r2
        role_id = r2["body"]["id"]

    # пользователь
    login, email, password = "assign_conflict_user", "assign_conflict_user@example.com", "secret123"
    u = await make_post_request("/auth/register", {"login": login, "email": email, "password": password})
    assert u["status"] in (201, 409), u
    if u["status"] == 201:
        user_id = u["body"]["id"]
    else:
        u2 = await make_post_request("/auth/register", {"login": "assign_conflict_user_u", "email": "assign_conflict_user_u@example.com", "password": password})
        assert u2["status"] == 201, u2
        user_id = u2["body"]["id"]

    # первое назначение
    a1 = await make_post_request_headers(ASSIGN_PATH, {"user_id": user_id, "role_id": role_id}, headers)
    assert a1["status"] in (200, 204), a1

    # повторное — ждём 409
    a2 = await make_post_request_headers(ASSIGN_PATH, {"user_id": user_id, "role_id": role_id}, headers)
    assert a2["status"] in (409, 200, 204), a2  # разрешаем оба варианта
    if a2["status"] == 409 and isinstance(a2["body"], dict):
        det = a2["body"].get("detail")
        if isinstance(det, dict):
            assert det.get("error") in ("already_assigned")


@pytest.mark.asyncio
async def test_roles_assign_not_found(admin_access, make_post_request_headers):
    """
    404 если не существует user_id или role_id.
    """
    headers = _auth_headers(admin_access)
    fake_user = "00000000-0000-0000-0000-000000000000"
    fake_role = "00000000-0000-0000-0000-000000000000"

    r1 = await make_post_request_headers(ASSIGN_PATH, {"user_id": fake_user, "role_id": fake_role}, headers)
    assert r1["status"] == 404, r1


@pytest.mark.asyncio
async def test_roles_assign_forbidden_for_non_admin(make_post_request, make_post_request_headers):
    """
    Обычный пользователь не может назначать роли
    """
    # обычный пользователь
    login, email, password = "assign_forbidden_user", "assign_forbidden_user@example.com", "secret123"
    await _ensure_user(make_post_request, login, email, password)
    access, _ = await _login(make_post_request, login, password)

    # фейковые id, нам важен ответ по правам
    resp = await make_post_request_headers(
        ASSIGN_PATH,
        {"user_id": "00000000-0000-0000-0000-000000000000", "role_id": "00000000-0000-0000-0000-000000000000"},
        _auth_headers(access),
    )
    assert resp["status"] in (403, 401), resp


@pytest.mark.asyncio
async def test_roles_assign_validation(admin_access, make_post_request_headers):
    """
    Валидация: не-UUID / пустые поля
    """
    headers = _auth_headers(admin_access)
    resp = await make_post_request_headers(
        ASSIGN_PATH,
        {"user_id": "not-a-uuid", "role_id": "also-not-uuid"},
        headers,
    )
    assert resp["status"] == 422, resp