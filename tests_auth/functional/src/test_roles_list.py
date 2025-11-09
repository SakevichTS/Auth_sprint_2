import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _ensure_user, _login, _auth_headers

pytestmark = pytest.mark.asyncio

ROLES_PATH = "/roles"

@pytest.mark.asyncio
async def test_roles_list_admin_ok(admin_access, make_get_request_headers):
    """
    Админ может получить список ролей и корректная структура
    """
    resp = await make_get_request_headers(
        ROLES_PATH,
        headers=_auth_headers(admin_access),
        params={"page": 1, "page_size": 20},
    )
    assert resp["status"] == 200, resp
    body = resp["body"]
    assert isinstance(body, dict), body
    for key in ("items", "total", "page", "page_size"):
        assert key in body, body
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["page"] == 1
    assert body["page_size"] == 20 or isinstance(body["page_size"], int)

    # если есть хотя бы одна роль, проверим форму элемента
    if body["items"]:
        r = body["items"][0]
        # допускаем любую схему, но обычно: id, name, description
        assert "id" in r and "name" in r


@pytest.mark.asyncio
async def test_roles_list_pagination(admin_access, make_get_request_headers):
    """
    Проверяем пагинацию: page=1,page_size=1 и page=2,page_size=1 возвращают разные наборы.
    (Если ролей меньше 2 — просто проверим, что 200 и структура корректна.)
    """
    headers = _auth_headers(admin_access)

    p1 = await make_get_request_headers(ROLES_PATH, headers=headers, params={"page": 1, "page_size": 1})
    assert p1["status"] == 200, p1
    p2 = await make_get_request_headers(ROLES_PATH, headers=headers, params={"page": 2, "page_size": 1})
    assert p2["status"] == 200, p2

    items1 = p1["body"].get("items", [])
    items2 = p2["body"].get("items", [])
    # если в системе >= 2 ролей — ожидаем, что элементы различаются
    if len(items1) == 1 and len(items2) == 1 and p1["body"]["total"] >= 2:
        assert items1[0]["id"] != items2[0]["id"]


@pytest.mark.asyncio
async def test_roles_list_forbidden_for_non_admin(make_post_request, make_get_request_headers):
    """
    Обычный пользователь не должен видеть список ролей
    """
    login = "roles_list_user"
    email = "roles_list_user@example.com"
    password = "secret123"
    await _ensure_user(make_post_request, login, email, password)
    access, _ = await _login(make_post_request, login, password)

    resp = await make_get_request_headers(
        ROLES_PATH,
        headers=_auth_headers(access),
        params={"page": 1, "page_size": 10},
    )
    assert resp["status"] in (403, 401), resp