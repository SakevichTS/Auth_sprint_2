import pytest

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _ensure_user, _login, _auth_headers

pytestmark = pytest.mark.asyncio

ROLES_PATH = "/roles"

@pytest.mark.asyncio
async def test_roles_update_success(admin_access, make_post_request_headers, make_patch_request):
    # создаём роль
    create = await make_post_request_headers(
        f'{ROLES_PATH}/create', {"name": "role_upd_src", "description": "before"},
        _auth_headers(admin_access),
    )
    assert create["status"] in (201, 409), create
    if create["status"] == 201:
        role_id = create["body"]["id"]
    else:
        # если уже существовала — надо получить её id через повторное создание не выйдет.
        # для простоты создадим уникальную роль:
        create2 = await make_post_request_headers(
            f'{ROLES_PATH}/create', {"name": "role_upd_src_unique", "description": "before"},
            _auth_headers(admin_access),
        )
        assert create2["status"] == 201, create2
        role_id = create2["body"]["id"]

    # апдейт
    upd = await make_patch_request(
        f"{ROLES_PATH}/{role_id}",
        {"name": "role_upd_dst", "description": "after"},
        _auth_headers(admin_access),
    )
    assert upd["status"] == 200, upd
    body = upd["body"]
    assert body["id"] == role_id
    assert body["name"] == "role_upd_dst"
    assert body.get("description") == "after"


@pytest.mark.asyncio
async def test_roles_update_not_found(admin_access, make_patch_request):
    """
    Обновление несуществующей роли 404.
    """
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await make_patch_request(
        f"{ROLES_PATH}/{fake_id}",
        {"name": "new_name"},
        _auth_headers(admin_access),
    )
    assert resp["status"] == 404, resp


@pytest.mark.asyncio
async def test_roles_update_conflict(admin_access, make_post_request_headers, make_patch_request):
    """
    Конфликт по имени: меняем роль A на имя, уже занятое ролью B -> 409.
    """
    # создадим две роли
    r1 = await make_post_request_headers(
        f'{ROLES_PATH}/create', {"name": "role_upd_conflict_A"}, _auth_headers(admin_access)
    )
    assert r1["status"] in (201, 409), r1
    if r1["status"] == 201:
        r1_id = r1["body"]["id"]
    else:
        # чтобы гарантированно иметь id, создадим уникальную:
        r1b = await make_post_request_headers(
            f'{ROLES_PATH}/create', {"name": "role_upd_conflict_A_unique"}, _auth_headers(admin_access)
        )
        assert r1b["status"] == 201, r1b
        r1_id = r1b["body"]["id"]

    r2 = await make_post_request_headers(
        f'{ROLES_PATH}/create', {"name": "role_upd_conflict_B"}, _auth_headers(admin_access)
    )
    assert r2["status"] in (201, 409), r2

    # пробуем переименовать A в имя B
    upd = await make_patch_request(
        f"{ROLES_PATH}/{r1_id}",
        {"name": "role_upd_conflict_B"},
        _auth_headers(admin_access),
    )
    assert upd["status"] == 409, upd
    if isinstance(upd["body"], dict) and "detail" in upd["body"]:
        d = upd["body"]["detail"]
        if isinstance(d, dict) and "error" in d:
            assert d["error"] in ("role_exists", "conflict")


@pytest.mark.asyncio
async def test_roles_update_forbidden_for_non_admin(make_post_request, make_patch_request):
    """
    Обычный пользователь не может обновлять роли -> 403/401.
    """
    # создадим обычного пользователя и залогинимся
    login, email, password = "roles_upd_user", "roles_upd_user@example.com", "secret123"
    await _ensure_user(make_post_request, login, email, password)
    access, _ = await _login(make_post_request, login, password)

    # пробуем обновить любую роль (id фиктивный)
    resp = await make_patch_request(
        f"{ROLES_PATH}/00000000-0000-0000-0000-000000000000",
        {"name": "no_rights"},
        _auth_headers(access),
    )
    assert resp["status"] in (403, 401), resp


@pytest.mark.asyncio
async def test_roles_update_validation(admin_access, make_post_request_headers, make_patch_request):
    """
    Пустое тело или отсутствие валидных полей -> 422 (в зависимости от схемы).
    """
    # создадим роль
    create = await make_post_request_headers(
        f'{ROLES_PATH}/create', {"name": "role_upd_validate"}, _auth_headers(admin_access)
    )
    assert create["status"] in (201, 409), create
    if create["status"] == 201:
        role_id = create["body"]["id"]
    else:
        # создадим уникальную
        c2 = await make_post_request_headers(
            f'{ROLES_PATH}/create', {"name": "role_upd_validate_unique"}, _auth_headers(admin_access)
        )
        assert c2["status"] == 201, c2
        role_id = c2["body"]["id"]

    resp = await make_patch_request(
        f"{ROLES_PATH}/{role_id}",
        {},
        _auth_headers(admin_access),
    )
    assert resp["status"] in (200, 422), resp
