import pytest
from http import HTTPStatus

pytestmark = pytest.mark.asyncio
# --- Тесты поиска персон ---
@pytest.mark.parametrize(
    "query, expected_status, expected_count",
    [
        ("Tom", HTTPStatus.OK, 21),
        ("NotExistingPerson", HTTPStatus.OK, 0),
        ("", HTTPStatus.UNPROCESSABLE_ENTITY, None),
    ],
)
async def test_search_persons(make_raw_get_request, query, expected_status, expected_count):
    response = await make_raw_get_request("/api/v1/persons/search", {"query": query})
    assert response.status == expected_status

    if expected_status == HTTPStatus.OK:
        body = await response.json()
        assert isinstance(body, list)
        assert len(body) == expected_count


# --- Тесты получения детальной карточки ---
@pytest.mark.parametrize(
    "person_id, expected_status",
    [
        ("53f55411-e8b5-491e-a526-770ed4bf71a7", HTTPStatus.OK),
        ("99999999-9999-9999-9999-999999999999", HTTPStatus.NOT_FOUND),
    ],
)
async def test_person_details(make_raw_get_request, person_id, expected_status):
    response = await make_raw_get_request(f"/api/v1/persons/{person_id}")
    assert response.status == expected_status

    if expected_status == HTTPStatus.OK:
        body = await response.json()
        assert "id" in body
        assert "full_name" in body
        assert "films" in body
        assert body["id"] == person_id


# --- Тесты получения фильмов персоны ---
@pytest.mark.parametrize(
    "person_id, expected_status, min_count",
    [
        ("53f55411-e8b5-491e-a526-770ed4bf71a7", HTTPStatus.OK, 1),   # заменить на реальный ID
        ("99999999-9999-9999-9999-999999999999", HTTPStatus.OK, 0),
    ],
)
async def test_person_films(make_raw_get_request, person_id, expected_status, min_count):
    response = await make_raw_get_request(f"/api/v1/persons/{person_id}/film")
    assert response.status == expected_status

    if expected_status == HTTPStatus.OK:
        body = await response.json()
        assert isinstance(body, list)
        assert len(body) >= min_count
        for film in body:
            assert "id" in film
            assert "title" in film
            assert "imdb_rating" in film


# --- Тесты кэша Redis ---
async def test_persons_cache(redis_client, make_get_request):
    person_id = "96b9fc3a-e133-4d7b-9755-7d0a22daf8d8"
    cache_key = f"person:detail:{person_id}"

    # 1. Кэша ещё нет
    assert await redis_client.get(cache_key) is None

    # 2. Запрос к API
    response = await make_get_request(f"/api/v1/persons/{person_id}")
    assert response["status"] == HTTPStatus.OK
    body = response["body"]
    assert body["id"] == person_id

    # 3. Кэш появляется
    cached = await redis_client.get(cache_key)
    assert cached is not None

    # 4. Проверяем, что данные в кэше соответствуют ответу API
    import json
    cached_data = json.loads(cached)
    assert cached_data["id"] == body["id"]
    assert cached_data["full_name"] == body["full_name"]
