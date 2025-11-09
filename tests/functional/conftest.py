import asyncio
import aiohttp
import pytest
import pytest_asyncio
from redis.asyncio import Redis

from tests.functional.settings import test_settings


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


@pytest.fixture(scope='session')
def make_raw_get_request(session):
    async def inner(path: str, params: dict = None):
        url = test_settings.service_url + path
        return await session.get(url, params=params)  # вернём сам ClientResponse
    return inner
