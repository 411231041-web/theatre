"""Функциональные тесты эндпоинта /api/v1/persons.

Проверяется валидация запросов, поиск персон, получение детальной информации,
просмотр фильмов по персоне и кеширование результатов Redis.
"""

import uuid
import pytest
from settings import test_settings
from conftest import fetch_all_pages
from conftest import build_person_bulk_data


@pytest.mark.asyncio
async def test_persons_search_validation_query_required(http_session):
    """Проверяет, что отсутствие query возвращает 422.

    Запрос без параметра query должен привести к ошибке валидации
    и ответу со статусом 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search"
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 422
    assert "query" in body["detail"][0]["loc"]
    assert body["detail"][0]["msg"] == (
        "String should have at least 1 character"
    )


@pytest.mark.asyncio
async def test_persons_search_validation_query_empty(http_session):
    """Проверяет, что пустой query возвращает ошибку валидации.

    Запрос с query= пустой строка должен вернуть подробное сообщение
    о минимальной длине строки.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": ""},
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 422
    assert "query" in body["detail"][0]["loc"]
    assert body["detail"][0]["msg"] == (
        "String should have at least 1 character"
    )


@pytest.mark.asyncio
async def test_persons_search_validation_sort(http_session):
    """Проверяет валидацию параметра сортировки.

    Запрос с невалидным значением sort должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "sort": "invalid"},
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 422
    assert "sort" in body["detail"][0]["loc"]
    assert (
        body["detail"][0]["msg"] ==
        "String should match pattern '^-?full_name$'"
    )


@pytest.mark.parametrize(
    ("sort_value", "expected_message"),
    [
        ("nonexistent_field", "String should match pattern '^-?full_name$'"),
        ("", "String should match pattern '^-?full_name$'"),
    ]
)
@pytest.mark.asyncio
async def test_persons_validation_sort_invalid_field(
    sort_value, expected_message, es_test_persons, http_session
):
    """Проверяет, что сортировка по несуществующему полю возвращает 422.

    Запрос с sort=nonexistent_field должен привести к ошибке валидации и
    ответу со статусом 422.
    Запрос с sort="" должен привести к ошибке валидации и
    ответу со статусом 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "sort": sort_value}
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 422
    assert (
        body["detail"][0]["msg"] == expected_message
    )


@pytest.mark.parametrize(
    "page_size, expected_message",
    [
        (-1, "Input should be greater than or equal to 1"),
        (0, "Input should be greater than or equal to 1"),
        (101, "Input should be less than or equal to 100"),
    ],
)
@pytest.mark.asyncio
async def test_persons_search_validation_page_size_bounds(
    page_size, expected_message, http_session
):
    """Проверяет валидацию параметра page_size.

    Запрос с невалидным значением page_size должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "page_size": page_size},
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 422
    assert "page_size" in body["detail"][0]["loc"]
    assert body["detail"][0]["msg"] == expected_message


@pytest.mark.asyncio
async def test_persons_search_validation_page_size_wrong_type(
    es_test_persons, http_session
):
    """Проверяет валидацию типа параметра page_size.

    Запрос с невалидным типом для page_size должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "page_size": "not_a_number"},
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 422
    assert "page_size" in body["detail"][0]["loc"]
    assert body["detail"][0]["msg"] == (
        "Input should be a valid integer, "
        "unable to parse string as an integer"
    )


@pytest.mark.parametrize(
    "page_number, expected_message",
    [
        (-1, "Input should be greater than or equal to 1"),
        (0, "Input should be greater than or equal to 1"),
        (101, "Input should be less than or equal to 100"),
    ],
)
@pytest.mark.asyncio
async def test_persons_search_validation_page_number_bounds(
    page_number, expected_message, es_test_persons, http_session
):
    """Проверяет валидацию параметра page_number.

    Запрос с невалидным значением page_number должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test practicum", "page_number": page_number},
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 422
    assert "page_number" in body["detail"][0]["loc"]
    assert body["detail"][0]["msg"] == expected_message


@pytest.mark.asyncio
async def test_persons_search_validation_page_number_wrong_type(
    es_test_persons, http_session
):
    """Проверяет валидацию типа параметра page_number.

    Запрос с невалидным типом для page_number должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test practicum", "page_number": "not_a_number"},
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 422
    assert "page_number" in body["detail"][0]["loc"]
    assert body["detail"][0]["msg"] == (
        "Input should be a valid integer, "
        "unable to parse string as an integer"
    )


@pytest.mark.asyncio
async def test_persons_search_returns_specific_person(
    es_test_persons, http_session
):
    """Проверяет, что поиск по имени возвращает конкретную персону.

    Запрос с query, содержащим имя персоны, должен вернуть эту персону в
    результатах поиска.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "practicum"},
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 200
    assert len(body) > 0
    assert any(item["full_name"] == "practicum" for item in body)
    for item in body:
        assert "uuid" in item
        assert item.get("films")


@pytest.mark.asyncio
async def test_persons_search_filters_by_role_alias(
    es_test_persons, http_session
):
    """Проверяет фильтрацию по роли через alias filter[role].

    Запрос с filter[role]=director должен вернуть только персону, которая
    является режиссером.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "filter[role]": "director"},
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 200
    assert len(body) > 0
    assert all(
        "uuid" in item and "full_name" in item
        for item in body
    )
    for item in body:
        for film in item.get("films", []):
            assert "roles" in film
            assert film["roles"] == ["director"]


@pytest.mark.parametrize(
    ("person_id", "expected_status"),
    [
        ("ef86b8ff-3c82-4d31-ad8e-72b69f4e3f96", 200),  # Существующий UUID
        ("ef86b8ff-3c82-4d31-ad8e-72b69f4e3f97", 404),  # Не существующий UUID
        ("invalid-uuid", 422),  # Невалидный UUID
    ]
)
@pytest.mark.asyncio
async def test_persons_get_by_uuid_validation(
    person_id, expected_status, es_write_data, redis_client, http_session
):
    """Проверяет валидацию person_id.

    Запрос с несуществующим person_id должен вернуть 404,
    а с невалидным UUID - 422.
    """
    session = http_session
    # 1. Генерируем данные для ES
    bulk_query = build_person_bulk_data(count=60, query_prefix="Test person")

    if expected_status == 200:
        bulk_query[0]["_id"] = person_id
        bulk_query[0]["_source"]["id"] = person_id

    if expected_status == 404:
        current_ids = {row["_id"] for row in bulk_query}
        for row in bulk_query:
            if row["_id"] == person_id:
                new_id = str(uuid.uuid4())
                while new_id == person_id or new_id in current_ids:
                    new_id = str(uuid.uuid4())
                current_ids.remove(row["_id"])
                row["_id"] = new_id
                row["_source"]["id"] = new_id
                current_ids.add(new_id)

    # 2. Загружаем данные в ES
    await es_write_data(bulk_query, index=test_settings.es_person_index)

    async with session.get(
        test_settings.service_url + f"/api/v1/persons/{person_id}"
    ) as response:
        body = await response.json()
        status = response.status

    if expected_status == 200:
        assert body["uuid"] == person_id
        assert body["full_name"] == bulk_query[0]["_source"]["full_name"]
    assert status == expected_status


@pytest.mark.asyncio
async def test_persons_get_person_by_uuid(
    es_write_data, redis_client, http_session,
):
    """Проверяет получение информации о персоне по UUID.

    Запрос к /api/v1/persons/{person_id} должен вернуть информацию о персоне.
    в которых участвовала персона, с указанием ролей.
    """
    session = http_session
    person_id = "ef86b8ff-3c82-4d31-ad8e-72b69f4e3f96"
    # 1. Генерируем данные для ES
    bulk_query = build_person_bulk_data(count=60, query_prefix="Test person")

    current_ids = {row["_id"] for row in bulk_query}
    for row in bulk_query:
        if row["_id"] == person_id:
            new_id = str(uuid.uuid4())
            while new_id == person_id or new_id in current_ids:
                new_id = str(uuid.uuid4())
            current_ids.remove(row["_id"])
            row["_id"] = new_id
            row["_source"]["id"] = new_id
            current_ids.add(new_id)

    bulk_query[0]["_id"] = person_id
    bulk_query[0]["_source"]["id"] = person_id

    # 2. Загружаем данные в ES
    await es_write_data(bulk_query, index=test_settings.es_person_index)

    async with session.get(
        test_settings.service_url
        + f"/api/v1/persons/{person_id}"
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 200
    assert body["uuid"] == person_id
    assert body["full_name"] == bulk_query[0]["_source"]["full_name"]


@pytest.mark.asyncio
async def test_persons_search_return_n_persons(es_test_persons, http_session):
    """Проверяет, что эндпоинт возвращает правильное количество записей.

    Запрос с page_size=50 должен вернуть 50 жанров.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 200
    assert all(
        "uuid" in item and "full_name" in item
        for item in body
    )
    assert len(body) == 50


@pytest.mark.asyncio
async def test_persons_search_returns_all_persons(
    es_test_persons, http_session
):
    """Проверяет, что эндпоинт возвращает все записи при запросе всех страниц.

    Запрос с page_size=50 и перебором всех страниц должен вернуть все
    5000 персон.
    """
    result = await fetch_all_pages(
        http_session,
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test practicum"},
        page_size=50,
    )

    assert result["status"] == 200
    assert len(result["items"]) == 5000
    assert all(
        "uuid" in item and "full_name" in item
        for item in result["items"]
    )


@pytest.mark.asyncio
async def test_persons_search_uses_redis_cache(
    es_test_persons, redis_client, http_session
):
    """Проверяет, что результаты запроса кэшируются в Redis.

    После выполнения запроса должен появиться ключ кеша.
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 200
    assert all(
        "uuid" in item and "full_name" in item
        for item in body
    )
    assert len(body) == 50

    cache_keys = await redis_client.keys("persons:search:*")
    assert len(cache_keys) > 0


@pytest.mark.asyncio
async def test_persons_search_uses_redis_cache_on_repeat_query(
    es_test_persons, es_client, redis_client, http_session
):
    """Проверяет повторный запрос с использованием кэша Redis.

    После первого запроса индекс удаляется, и второй запрос должен
    вернуть данные из кеша.
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "page_size": 50}
    ) as first_response:
        first_body = await first_response.json()
        first_status = first_response.status

    assert first_status == 200
    assert all(
        "uuid" in item and "full_name" in item
        for item in first_body
    )
    assert len(first_body) == 50

    cache_keys = await redis_client.keys("persons:search:*")
    assert len(cache_keys) > 0

    # Удаляем индекс, чтобы убедиться, что второй запрос берет данные из Redis.
    await es_client.indices.delete(index=test_settings.es_person_index)

    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "page_size": 50}
    ) as second_response:
        second_body = await second_response.json()
        second_status = second_response.status

    assert second_status == 200
    assert all(
        "uuid" in item and "full_name" in item
        for item in second_body
    )
    assert len(second_body) == 50
    assert second_body == first_body
