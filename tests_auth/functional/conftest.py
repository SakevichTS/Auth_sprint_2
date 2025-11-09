import asyncio
import aiohttp
import pytest
import pytest_asyncio
from redis.asyncio import Redis
import psycopg

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import _login

# автозапуск перед всеми тестами
@pytest.fixture(scope="session", autouse=True)
def clean_postgres():
    """
    Чистим БД перед тестовой сессией.
    """
    dsn = f"postgresql://{test_settings.pg_user}:{test_settings.pg_password}@{test_settings.pg_host}:{test_settings.pg_port}/{test_settings.pg_db}"
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            # Отключим ограничения на время чистки
            cur.execute("SET session_replication_role = replica;")
            # Чистим в порядке, безопасном для FK
            cur.execute("""
                TRUNCATE TABLE
                    refresh_sessions,
                    login_audit,
                    users
                RESTART IDENTITY CASCADE;
            """)
            cur.execute("""
                DELETE FROM roles
                WHERE name NOT IN ('user', 'subscriber', 'admin');
            """)
            # Возвращаем обычный режим
            cur.execute("SET session_replication_role = DEFAULT;")
        conn.commit()


@pytest.fixture(scope="session", autouse=True)
async def clean_redis():
    """
    Redis — чистим весь DB 0.
    """
    client = Redis(
        host=test_settings.redis_host,
        port=test_settings.redis_port,
        db=getattr(test_settings, "redis_db", 0),
        decode_responses=True,
    )
    await client.flushdb()
    await client.aclose()

# переопределяем event loop, потому что по умолчению scope = function
@pytest_asyncio.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close() 

# фикстура для создания HTTP соединения
@pytest_asyncio.fixture(name='session', scope='session')
async def session():
    s = aiohttp.ClientSession()
    yield s
    await s.close()


@pytest_asyncio.fixture(name="redis_client", scope="session")
async def redis_client():
    client = Redis(
        host=test_settings.redis_host,
        port=test_settings.redis_port,
        decode_responses=True,
        db=0,
    )

    # очистим перед тестами
    await client.flushdb()
    yield client
    await client.aclose()

# фикстура запроса 
@pytest.fixture(scope='session')
def make_get_request(session):
    async def inner(path: str, params: dict = None):
        url = test_settings.service_url + path
        async with session.get(url, params=params) as response:
            body = await response.json()
            return {
                "status": response.status,
                "body": body,
            }
    return inner

@pytest.fixture(scope="session")
def make_get_request_headers(session):
    async def inner(path: str, headers: dict, params: dict | None = None):
        url = test_settings.service_url + path
        async with session.get(url, params=params, headers=headers) as resp:
            try:
                body = await resp.json()
            except Exception:
                body = await resp.text()
            return {"status": resp.status, "body": body}
    return inner

@pytest.fixture(scope="session")
def make_post_request(session):
    async def inner(path: str, data: dict):
        url = test_settings.service_url + path
        async with session.post(url, json=data) as response:
            try:
                body = await response.json()
            except Exception:
                body = await response.text()
            return {
                "status": response.status,
                "body": body,
            }
    return inner

@pytest.fixture(scope="session")
def make_post_request_headers(session):
    async def inner(path: str, data: dict, headers: dict | None = None):
        url = test_settings.service_url + path
        async with session.post(url, json=data, headers=headers) as response:
            try:
                body = await response.json()
            except Exception:
                body = await response.text()
            return {"status": response.status, "body": body}
    return inner

@pytest.fixture(scope='session')
def make_raw_get_request(session):
    async def inner(path: str, params: dict = None):
        url = test_settings.service_url + path
        return await session.get(url, params=params)  # вернём сам ClientResponse
    return inner

@pytest.fixture(scope="session")
async def admin_access(make_post_request):
    admin_login = getattr(test_settings, "admin_login", None)
    admin_password = getattr(test_settings, "admin_password", None)
    if not admin_login or not admin_password:
        pytest.skip("ADMIN creds are not configured in test_settings")

    access, _ = await _login(make_post_request, admin_login, admin_password)
    return access


def _dsn():
    return (
        f"postgresql://{test_settings.pg_user}:{test_settings.pg_password}"
        f"@{test_settings.pg_host}:{test_settings.pg_port}/{test_settings.pg_db}"
    )

@pytest.fixture(scope="session", autouse=True)
async def ensure_admin_after_cleanup(session):  # session = aiohttp.ClientSession фикстура
    """
    После очистки создаём админа:
      1) регистрируем через /auth/register
      2) убеждаемся, что есть роль 'admin',
      3) привязываем роль к пользователю.
    """
    admin_login = getattr(test_settings, "admin_login", "admin")
    admin_email = getattr(test_settings, "admin_email", "admin@example.com")
    admin_password = getattr(test_settings, "admin_password", "secret")

    # 1) регистрация через HTTP
    register_payload = {
        "login": admin_login,
        "email": admin_email,
        "password": admin_password,
        "first_name": "Admin",
        "last_name": "User",
    }
    url = test_settings.service_url + "/auth/register"
    async with session.post(url, json=register_payload) as resp:
        # допускаем 201 (создан) или 409 (уже есть, если тесты крутятся повторно)
        _ = await (resp.json() if resp.content_type == "application/json" else resp.text())
        assert resp.status in (201, 409), f"admin register failed: {resp.status}"

    # 2–3) роль и связь в БД — через psycopg
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            # роль admin
            cur.execute("SELECT id FROM roles WHERE name = %s", ("admin",))
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    "INSERT INTO roles (name, description) VALUES (%s, %s) RETURNING id",
                    ("admin", "Administrator"),
                )
                role_id = cur.fetchone()[0]
            else:
                role_id = row[0]

            # id пользователя admin
            cur.execute("SELECT id FROM users WHERE login = %s", (admin_login,))
            user_row = cur.fetchone()
            assert user_row, "Admin user not found after register"
            user_id = user_row[0]

            # связь user_roles (idempotent)
            cur.execute(
                """
                INSERT INTO user_roles (user_id, role_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (user_id, role_id),
            )
        conn.commit()


@pytest.fixture(scope="session")
def make_delete_request(session):
    async def inner(path: str, headers: dict = None):
        url = test_settings.service_url + path
        async with session.delete(url, headers=headers) as response:
            try:
                body = await response.json()
            except Exception:
                body = await response.text()
            return {
                "status": response.status,
                "body": body,
            }
    return inner

@pytest.fixture(scope="session")
def make_patch_request(session):
    async def inner(path: str, data: dict, headers: dict | None = None):
        url = test_settings.service_url + path
        async with session.patch(url, json=data, headers=headers) as response:
            try:
                body = await response.json()
            except Exception:
                body = await response.text()
            return {"status": response.status, "body": body}
    return inner