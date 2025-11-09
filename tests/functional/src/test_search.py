import pytest

from tests.functional.settings import test_settings

pytestmark = pytest.mark.asyncio


# 1) все граничные случаи по валидации данных;
@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        # --- Позитивные границы ---
        ({"query": "a", "page_number": 1, "page_size": 1},              {"status": 200}),
        ({"query": "star", "page_number": 1, "page_size": 1000},        {"status": 200}),
        ({"query": "star"},                                             {"status": 200}),  # page_number=1, page_size=50 по умолчанию
        ({"query": " "},                                                {"status": 200}),  # пробел валиден при min_length=1

        # --- Негативные границы: query ---
        ({"query": "" , "page_number": 1, "page_size": 50},             {"status": 422}),
        ({              "page_number": 1, "page_size": 50},             {"status": 422}),  # отсутствует query

        # --- Негативные границы: page_number ---
        ({"query": "star", "page_number": 0,  "page_size": 50},         {"status": 422}),
        ({"query": "star", "page_number": -1, "page_size": 50},         {"status": 422}),
        ({"query": "star", "page_number": "abc", "page_size": 50},      {"status": 422}),  # неверный тип

        # --- Негативные границы: page_size ---
        ({"query": "star", "page_number": 1, "page_size": 0},           {"status": 422}),
        ({"query": "star", "page_number": 1, "page_size": 1001},        {"status": 422}),
        ({"query": "star", "page_number": 1, "page_size": "1.5"},       {"status": 422}),  # неверный тип

        # --- Валидатор ES окна (MAX_WINDOW=10000, при page_size=50) ---
        ({"query": "star", "page_number": 200, "page_size": 50},        {"status": 200}),  # на границе (9950+50=10000)
        ({"query": "star", "page_number": 201, "page_size": 50},        {"status": 422}),  # перебор (10000+50>10000)
    ]
)
async def test_search_validation(make_get_request, query_data, expected_answer):  
    response = await make_get_request('/api/v1/films/search', query_data)
    assert response["status"] == expected_answer["status"]

# 2) Вывести только N записей
@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        ({"query": "star", "page_number": 1, "page_size": 1}, {"status": 200, "length": 1}),
        ({"query": "star", "page_number": 1, "page_size": 3}, {"status": 200, "length": 3}),
    ],
)
async def test_search_limit_n(make_get_request, query_data, expected_answer):
    response = await make_get_request("/api/v1/films/search", query_data)
    assert response["status"] == expected_answer["status"]
    assert len(response["body"]) == expected_answer["length"]


# 3) поиск записи или записей по фразе
@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        ({"query": "star", "page_number": 1, "page_size": 1}, {"status": 200, "length": 1}),
        ({"query": "blablacar", "page_number": 1, "page_size": 10}, {"status": 200, "length": 0}),
    ],
)
async def test_search_by_phrase(make_get_request, query_data, expected_answer):
    response = await make_get_request("/api/v1/films/search", query_data)
    assert response["status"] == expected_answer["status"]
    assert len(response["body"]) == expected_answer["length"]

#4) поиск с учётом кеша в Redis.
async def test_search_cache(make_get_request, redis_client):
    params = {"query": "star wars", "page_number": 1, "page_size": 3}

    # первый запрос для создания записи в redis 
    r1 = await make_get_request("/api/v1/films/search", params)
    assert r1["status"] == 200

    keys1 = await redis_client.keys("*")
    assert keys1
    
    # второй запрос данных из кеша
    r2 = await make_get_request("/api/v1/films/search", params)
    keys2 = await redis_client.keys("*")

    # проверяе что запрос без кеша равен запросу из кеша
    assert r1["body"] == r2["body"]
    assert len(keys1) == len(keys2)
