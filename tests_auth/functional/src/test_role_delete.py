import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _ensure_user, _login, _auth_headers

pytestmark = pytest.mark.asyncio

ROLES_PATH = "/roles"

@pytest.mark.asyncio
async def test_roles_delete_success(admin_access, make_post_request_headers, make_delete_request):
    # создаём новую роль
    name = "role_to_delete"
    desc = "will be deleted"
    resp = await make_post_request_headers(
        f"{ROLES_PATH}/create",
        {"name": name, "description": desc},
        _auth_headers(admin_access),
    )
    assert resp["status"] == 201, resp
    role_id = resp["body"]["id"]

    # удаляем роль
    resp_del = await make_delete_request(
        f"{ROLES_PATH}/{role_id}",
        _auth_headers(admin_access),
    )
    assert resp_del["status"] == 204, resp_del


@pytest.mark.asyncio
async def test_roles_delete_not_found(admin_access, make_delete_request):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await make_delete_request(
        f"{ROLES_PATH}/{fake_id}",
        _auth_headers(admin_access),
    )
    assert resp["status"] == 404, resp


@pytest.mark.asyncio
async def test_roles_delete_forbidden_for_non_admin(make_post_request, make_delete_request, make_post_request_headers):
    login = "roles_del_user"
    email = "roles_del_user@example.com"
    password = "secret123"
    await _ensure_user(make_post_request, login, email, password)
    access, _ = await _login(make_post_request, login, password)

    resp = await make_delete_request(
        f"{ROLES_PATH}/00000000-0000-0000-0000-000000000000",
        _auth_headers(access),
    )
    assert resp["status"] in (403, 401), resp