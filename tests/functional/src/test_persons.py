"""Функциональные тесты эндпоинта /api/v1/persons.

Проверяется валидация запросов, поиск персон, получение детальной информации,
просмотр фильмов по персоне и кеширование результатов Redis.
"""

import uuid
import pytest
from settings import test_settings
from utils.assert_helpers import (
    assert_validation_error_status,
    assert_validation_error_type,
    assert_validation_error_location,
    assert_validation_error_context,
    assert_body_length,
    assert_body_item,
    assert_uuid_equal,
    assert_field_equal,
)
from testdata.es_mapping import ES_PERSON_MAPPING
from utils.http_helpers import fetch_all_pages
from utils.test_data_helpers import build_person_bulk_data


@pytest.mark.asyncio
async def test_persons_search_validation_query_required(http_session):
    """Проверяет, что отсутствие `query` возвращает 422.

    Запрос без параметра `query` должен привести к ошибке валидации
    и ответу со статусом 422.

    Параметры
    ---------
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search"
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 422, body['detail'][0])
    assert_validation_error_type(body['detail'][0], type_prefix='missing')
    assert_validation_error_location(
        body['detail'][0], loc_contains='["query","query"]'
    )


@pytest.mark.asyncio
async def test_persons_search_validation_query_empty(http_session):
    """Проверяет, что пустой `query` возвращает ошибку валидации.

    Запрос с `query` равным пустой строке должен вернуть подробное
    сообщение о минимальной длине строки.

    Параметры
    ---------
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": ""},
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 422, body['detail'][0])
    assert_validation_error_type(
        body['detail'][0], type_prefix='string_too_short'
    )
    assert_validation_error_location(
        body['detail'][0], loc_contains='["query","query"]'
    )
    assert_validation_error_context(
        body['detail'][0], ctx_contains={"min_length": 1}
    )


@pytest.mark.asyncio
async def test_persons_search_validation_sort(http_session):
    """Проверяет валидацию параметра сортировки.

    Запрос с невалидным значением `sort` должен вернуть 422.

    Параметры
    ---------
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "sort": "invalid"},
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 422, body['detail'][0])
    assert_validation_error_type(
        body['detail'][0], type_prefix='string_pattern_mismatch'
    )
    assert_validation_error_location(
        body['detail'][0], loc_contains='["query","sort"]'
    )
    assert_validation_error_context(
        body['detail'][0], ctx_contains={"pattern": r"^-?full_name$"}
    )


@pytest.mark.asyncio
async def test_persons_validation_sort_invalid_field(
    es_test_persons, http_session
):
    """Проверяет, что сортировка по несуществующему полю возвращает 422.

    Запрос с `sort=nonexistent_field` должен привести к ошибке
    валидации и ответу со статусом 422.

    Параметры
    ---------
    es_test_persons: fixture
        Фикстура, заполняющая ES тестовыми персонами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "sort": "nonexistent_field"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 422, body['detail'][0])
    assert_validation_error_type(
        body['detail'][0], type_prefix='string_pattern_mismatch'
    )
    assert_validation_error_location(
        body['detail'][0], loc_contains='["query","sort"]'
    )
    assert_validation_error_context(
        body['detail'][0], ctx_contains={"pattern": r"^-?full_name$"}
    )


@pytest.mark.parametrize(
    "page_size",
    [
        -1, 0, 101, "not_a_number",
    ],
)
@pytest.mark.asyncio
async def test_persons_search_validation_page_size_bounds(
    page_size, http_session
):
    """Проверяет валидацию параметра `page_size`.

    Запрос с невалидным значением `page_size` должен вернуть 422.

    Параметры
    ---------
    page_size: int | str
        Тестовое значение параметра `page_size`.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "page_size": page_size},
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 422, body['detail'][0])
    assert_validation_error_type(
        body['detail'][0],
        type_prefix=["less_than_equal", "greater_than_equal", "int_parsing"],
    )
    assert_validation_error_location(
        body['detail'][0], loc_contains='["query","page_size"]'
    )
    assert_validation_error_context(
        body['detail'][0],
        ctx_contains=(
            None if page_size == "not_a_number"
            else [{"le": 100}, {"ge": 1}]
        ),
    )


@pytest.mark.parametrize(
    "page_number",
    [
        -1, 0, "not_a_number",
    ],
)
@pytest.mark.asyncio
async def test_persons_search_validation_page_number_bounds(
    page_number, es_test_persons, http_session
):
    """Проверяет валидацию параметра `page_number`.

    Запрос с невалидным значением `page_number` должен вернуть 422.

    Параметры
    ---------
    page_number: int | str
        Тестовое значение `page_number`.
    es_test_persons: fixture
        Фикстура, заполняющая ES тестовыми персонами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test practicum", "page_number": page_number},
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 422, body['detail'][0])
    assert_validation_error_type(
        body['detail'][0],
        type_prefix=["greater_than_equal", "int_parsing"],
    )
    assert_validation_error_location(
        body['detail'][0], loc_contains='["query","page_number"]'
    )
    assert_validation_error_context(
        body['detail'][0],
        ctx_contains=(
            None if page_number == "not_a_number"
            else [{"ge": 1}]
        ),
    )


@pytest.mark.asyncio
async def test_persons_search_returns_specific_person(
    es_write_data, http_session
):
    """Проверяет, что поиск по имени возвращает конкретную персону.

    Запрос с `query`, содержащим имя персоны, должен вернуть эту персону
    в результатах поиска.

    Параметры
    ---------
    es_write_data: fixture
        Функция загрузки данных в Elasticsearch.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session

    # 1. Генерируем данные для ES
    bulk_query = build_person_bulk_data(count=60, query_prefix="Test person")

    name = "UnicumPracticum"

    bulk_query[0]["_source"]["full_name"] = name

    # 2. Загружаем данные в ES
    await es_write_data(
        bulk_query,
        index=test_settings.es_person_index,
        mapping=ES_PERSON_MAPPING
    )

    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": name},
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_item(body, {"uuid": str})
    assert_field_equal(body["results"][0]["full_name"], name)


@pytest.mark.asyncio
async def test_persons_search_filters_by_role_alias(
    es_test_persons, http_session
):
    """Проверяет фильтрацию по роли через alias `filter[role]`.

    Запрос с `filter[role]=director` должен вернуть только персону, которая
    является режиссером.

    Параметры
    ---------
    es_test_persons: fixture
        Фикстура, заполняющая ES тестовыми персонами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "filter[role]": "director"},
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_item(body, {"uuid": str, "full_name": str})

    assert len(body["results"]) > 0
    for item in body["results"]:
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
    """Проверяет валидацию `person_id` при запросе по UUID.

    Запрос с несуществующим `person_id` должен вернуть 404, а с
    невалидным UUID — 422.

    Параметры
    ---------
    person_id: str
        Тестовый UUID или строка.
    expected_status: int
        Ожидаемый HTTP-статус ответа.
    es_write_data: fixture
        Функция загрузки данных в Elasticsearch.
    redis_client: fixture
        Асинхронный клиент Redis.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии.

    Возвращает
    ---------
    None
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
    await es_write_data(
        bulk_query,
        index=test_settings.es_person_index,
        mapping=ES_PERSON_MAPPING
    )

    async with session.get(
        test_settings.service_url + f"/api/v1/persons/{person_id}"
    ) as response:
        body = await response.json()
        status = response.status

    if expected_status == 200:
        uuid_val = body["uuid"]
        name_val = body["full_name"]
        expected_uuid = person_id
        expected_name = bulk_query[0]["_source"]["full_name"]
        type_prefix = None
        loc_contains = None
    else:
        if expected_status == 422:
            type_prefix = "uuid_parsing"
            loc_contains = '["path","person_id"]'
        else:
            type_prefix = None
            loc_contains = None

        uuid_val = None
        name_val = None
        expected_uuid = None
        expected_name = None

    detail_obj = (body["detail"][0] if expected_status == 422 else body)
    assert_validation_error_status(status, expected_status, detail_obj)
    assert_validation_error_type(detail_obj, type_prefix=type_prefix)
    assert_validation_error_location(detail_obj, loc_contains=loc_contains)
    assert_uuid_equal(uuid_val, expected_uuid)
    assert_field_equal(name_val, expected_name)


@pytest.mark.asyncio
async def test_persons_get_person_by_uuid(
    es_write_data, redis_client, http_session,
):
    """Проверяет получение информации о персоне по UUID.

    Запрос к `/api/v1/persons/{person_id}` должен вернуть информацию о
    персоне и список фильмов, в которых персона участвовала.

    Параметры
    ---------
    es_write_data: fixture
        Функция загрузки данных в Elasticsearch.
    redis_client: fixture
        Асинхронный клиент Redis.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии.

    Возвращает
    ---------
    None
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
    await es_write_data(
        bulk_query,
        index=test_settings.es_person_index,
        mapping=ES_PERSON_MAPPING
    )

    async with session.get(
        test_settings.service_url
        + f"/api/v1/persons/{person_id}"
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_uuid_equal(body.get("uuid"), person_id)
    assert_field_equal(
        body.get("full_name"),
        bulk_query[0]["_source"]["full_name"]
    )


@pytest.mark.asyncio
async def test_persons_search_return_n_persons(es_test_persons, http_session):
    """Проверяет, что эндпоинт возвращает правильное количество записей.

    Запрос с page_size=50 должен вернуть 50 персон.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_length(body, 50)
    assert_body_item(body, {"uuid": str, "full_name": str})


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

    assert_validation_error_status(result["status"], 200, result["items"])
    assert_body_length(result["items"], 5000)
    assert_body_item(result["items"], {"uuid": str, "full_name": str})


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

    assert_validation_error_status(status, 200, body)
    assert_body_length(body, 50)
    assert_body_item(body, {"uuid": str, "full_name": str})

    cache_keys = await redis_client.keys("persons:search:*")
    assert len(cache_keys) > 0


@pytest.mark.asyncio
async def test_persons_search_uses_redis_cache_on_repeat_query(
    es_test_persons, es_client_factory, redis_client, http_session
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

    assert_validation_error_status(first_status, 200, first_body)
    assert_body_length(first_body, 50)
    assert_body_item(first_body, {"uuid": str, "full_name": str})

    cache_keys = await redis_client.keys("persons:search:*")
    assert len(cache_keys) > 0

    # Удаляем индекс, чтобы убедиться, что второй запрос берет данные
    # из Redis.
    client = es_client_factory()
    try:
        await client.indices.delete(index=test_settings.es_person_index)
    finally:
        await client.close()

    async with session.get(
        test_settings.service_url + "/api/v1/persons/search",
        params={"query": "Test", "page_size": 50}
    ) as second_response:
        second_body = await second_response.json()
        second_status = second_response.status

    assert_validation_error_status(second_status, 200, second_body)
    assert_body_length(second_body, 50)
    assert_body_item(second_body, {"uuid": str, "full_name": str})
    assert second_body == first_body
