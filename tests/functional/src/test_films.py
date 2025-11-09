import pytest
from http import HTTPStatus

# --- Тесты поиска фильмов ---
@pytest.mark.parametrize(
    "query, expected_status, expected_count",
    [
        ("Star", HTTPStatus.OK, 50),
        ("NonExistingMovie", HTTPStatus.OK, 0),
        ("", HTTPStatus.UNPROCESSABLE_ENTITY, None),
    ],
)
async def test_search_films(make_raw_get_request, query, expected_status, expected_count):
    response = await make_raw_get_request("/api/v1/films/search", {"query": query})
    assert response.status == expected_status

    if expected_status == HTTPStatus.OK:
        body = await response.json()
        assert isinstance(body, list)
        assert len(body) == expected_count


# --- Тесты получения детальной карточки ---
@pytest.mark.parametrize(
    "film_id, expected_status",
    [
        ("ff750819-6004-426b-ae66-19a3ba15adcc", HTTPStatus.OK),       # заменить на реальный ID
        ("99999999-9999-9999-9999-999999999999", HTTPStatus.NOT_FOUND),
    ],
)
async def test_film_details(make_raw_get_request, film_id, expected_status):
    response = await make_raw_get_request(f"/api/v1/films/{film_id}")
    assert response.status == expected_status

    if expected_status == HTTPStatus.OK:
        body = await response.json()
        assert "id" in body
        assert "title" in body
        assert "imdb_rating" in body
        assert "description" in body
        assert "genre" in body
        assert "actors" in body
        assert "writers" in body
        assert "directors" in body
        assert body["id"] == film_id


# --- Тесты списка фильмов по жанрам и сортировке ---
@pytest.mark.parametrize(
    "params, expected_status, min_count",
    [
        ({"genre": "f39d7b6d-aef2-40b1-aaf0-cf05e7048011"}, HTTPStatus.OK, 1),  # реальный ID жанра
        ({"sort": "-imdb_rating", "page_size": 5}, HTTPStatus.OK, 1),
        ({"page_number": 0}, HTTPStatus.UNPROCESSABLE_ENTITY, None),
    ],
)
async def test_films_list(make_raw_get_request, params, expected_status, min_count):
    response = await make_raw_get_request("/api/v1/films/", params)
    assert response.status == expected_status

    if expected_status == HTTPStatus.OK:
        body = await response.json()
        assert isinstance(body, list)
        assert len(body) >= min_count
        for film in body:
            assert "id" in film
            assert "title" in film
            assert "imdb_rating" in film
