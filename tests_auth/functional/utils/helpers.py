async def _ensure_user(make_post_request, login: str, email: str, password: str):
    payload = {
        "login": login,
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User",
    }
    resp = await make_post_request("/auth/register", payload)
    assert resp["status"] in (201, 409), f"register failed: {resp}"
    return resp

async def _ensure_user_and_get_id(make_post_request, login: str, email: str, password: str) -> str:
    """
    Создаёт пользователя и возвращает user_id.
    Если логин/почта заняты (409), регистрирует с суффиксом, чтобы получить id.
    """
    r = await _ensure_user(make_post_request, login, email, password)
    if r["status"] == 201:
        return r["body"]["id"]

    # конфликт — зарегистрируем уникальный логин/почту
    alt_login = f"{login}_u"
    alt_email = f"{login}_u@example.com"
    r2 = await make_post_request("/auth/register", {
        "login": alt_login, "email": alt_email, "password": password,
        "first_name": "Test", "last_name": "User",
    })
    assert r2["status"] == 201, r2
    return r2["body"]["id"]

async def _login(make_post_request, login: str, password: str):
    resp = await make_post_request("/auth/login", {"login": login, "password": password})
    assert resp["status"] == 200, resp
    body = resp["body"]
    return body["access"], body["refresh"]

def _auth_headers(access: str) -> dict:
    return {"Authorization": f"Bearer {access}"}

async def _create_role_any(make_post_request_headers, headers, name: str, description: str | None = None):
    # пробуем POST /roles, при 405 — POST /roles/create
    resp = await make_post_request_headers(
        '/roles',
        {"name": name, "description": description},
        headers,
    )
    if resp["status"] == 405:
        resp = await make_post_request_headers(
            "/roles/create",
            {"name": name, "description": description},
            headers,
        )
    return resp