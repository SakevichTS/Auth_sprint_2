import pytest
from http import HTTPStatus

pytestmark = pytest.mark.asyncio

@pytest.mark.parametrize(
    "genre_id, expected_status",
    [
        ("f39d7b6d-aef2-40b1-aaf0-cf05e7048011", HTTPStatus.OK),     # поменять на существующий в бд UUID
        ("not-a-uuid", HTTPStatus.UNPROCESSABLE_ENTITY),
    ]
)

async def test_genre_details_validation(make_get_request, genre_id, expected_status):
    response = await make_get_request(f"/api/v1/genres/{genre_id}")
    assert response["status"] == expected_status

async def test_genres_list(make_get_request):
    response = await make_get_request("/api/v1/genres/")
    assert response["status"] == HTTPStatus.OK
    assert isinstance(response["body"], list)
    assert len(response["body"]) > 0

async def test_genre_cache(make_get_request, redis_client):
    genres_resp = await make_get_request("/api/v1/genres/")
    assert genres_resp["status"] == HTTPStatus.OK
    assert genres_resp["body"]

    genre_id = genres_resp["body"][0]["id"]

    # Первый запрос
    r1 = await make_get_request(f"/api/v1/genres/{genre_id}")
    assert r1["status"] == HTTPStatus.OK

    keys1 = await redis_client.keys("*")
    assert keys1

    # Второй запрос
    r2 = await make_get_request(f"/api/v1/genres/{genre_id}")
    keys2 = await redis_client.keys("*")

    assert r1["body"] == r2["body"]
    assert len(keys1) == len(keys2)
