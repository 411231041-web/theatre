"""Функциональные тесты эндпоинта /api/v1/genres

Проверяется валидация запросов, пагинация, кеширование Redis и обработка
фразовых запросов.
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
from testdata.es_mapping import ES_GENRE_MAPPING
from utils.http_helpers import fetch_all_pages
from utils.test_data_helpers import build_genre_bulk_data


@pytest.mark.asyncio
async def test_genres_validation_sort(http_session):
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
        test_settings.service_url + "/api/v1/genres",
        params={"sort": "invalid"}
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
        body['detail'][0], ctx_contains={"pattern": r"^-?name$"}
    )


@pytest.mark.parametrize(
    "sort_value",
    [
        "nonexistent_field",
        "",
    ]
)
@pytest.mark.asyncio
async def test_genres_validation_sort_invalid_field(
    sort_value, es_test_genres, http_session
):
    """Проверяет, что сортировка по несуществующему полю возвращает 422.

    Запрос с `sort=nonexistent_field` или пустым значением должен вернуть
    ошибку валидации и статус 422.

    Параметры
    ---------
    sort_value: str
        Тестовое значение параметра `sort`.
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"sort": sort_value}
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
        body['detail'][0], ctx_contains={"pattern": r"^-?name$"}
    )


@pytest.mark.parametrize(
    "page_size",
    [
        -1, 0, 101, "not_a_number",
    ],
)
@pytest.mark.asyncio
async def test_genres_validation_page_size_bounds(
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
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": page_size}
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
async def test_genres_validation_page_number_bounds(
    page_number, es_test_genres, http_session
):
    """Проверяет валидацию параметра `page_number`.

    Запрос с невалидным значением `page_number` должен вернуть 422.

    Параметры
    ---------
    page_number: int | str
        Тестовое значение `page_number`.
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_number": page_number}
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
async def test_genres_return_n_genres(es_test_genres, http_session):
    """Проверяет, что эндпоинт возвращает правильное количество записей.

    Запрос с `page_size=50` должен вернуть 50 жанров.

    Параметры
    ---------
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_length(body, 50)
    assert_body_item(body, {"uuid": str, "name": str})


@pytest.mark.asyncio
async def test_genres_return_all_genres(es_test_genres, http_session):
    """Проверяет, что эндпоинт возвращает все записи при запросе всех страниц.

    Запрос с `page_size=50` и перебором всех страниц должен вернуть все
    5000 жанров.

    Параметры
    ---------
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запросов.

    Возвращает
    ---------
    None
    """
    result = await fetch_all_pages(
        http_session,
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    )

    assert_validation_error_status(result["status"], 200, result["items"])
    assert_body_length(result["items"], 5000)
    assert_body_item(result["items"], {"uuid": str, "name": str})


@pytest.mark.parametrize(
    ("genre_id", "expected_status"),
    [
        ("ef86b8ff-3c82-4d31-ad8e-72b69f4e3f96", 200),  # Существующий UUID
        ("ef86b8ff-3c82-4d31-ad8e-72b69f4e3f97", 404),  # Не существующий UUID
        ("invalid-uuid", 422),  # Невалидный UUID
    ]
)
@pytest.mark.asyncio
async def test_genres_get_by_uuid_validation(
    genre_id, expected_status, es_write_data, redis_client, http_session
):
    """Проверяет валидацию запроса получения жанра по ID.

    Запрос с невалидным UUID должен вернуть 422, с несуществующим — 404,
    с существующим — 200.

    Параметры
    ---------
    genre_id: str
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
    bulk_query = build_genre_bulk_data(count=60, query_prefix="Test genre")

    if expected_status == 200:
        bulk_query[0]["_id"] = genre_id
        bulk_query[0]["_source"]["id"] = genre_id

    if expected_status == 404:
        current_ids = {row["_id"] for row in bulk_query}
        for row in bulk_query:
            if row["_id"] == genre_id:
                new_id = str(uuid.uuid4())
                while new_id == genre_id or new_id in current_ids:
                    new_id = str(uuid.uuid4())
                current_ids.remove(row["_id"])
                row["_id"] = new_id
                row["_source"]["id"] = new_id
                current_ids.add(new_id)

    # 2. Загружаем данные в ES
    await es_write_data(
        bulk_query,
        index=test_settings.es_genre_index,
        mapping=ES_GENRE_MAPPING
    )

    async with session.get(
        test_settings.service_url + f"/api/v1/genres/{genre_id}"
    ) as response:
        body = await response.json()
        status = response.status

    if expected_status == 200:
        uuid_val = body["uuid"]
        name_val = body["name"]
        expected_uuid = genre_id
        expected_name = bulk_query[0]["_source"]["name"]
        type_prefix = None
        loc_contains = None
    else:
        if expected_status == 422:
            type_prefix = "uuid_parsing"
            loc_contains = '["path","genre_id"]'
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
async def test_genres_get_film_by_uuid(
    es_write_data, redis_client, http_session,
):
    """Проверяет получение информации о жанре по UUID.

    Запрос к `/api/v1/genres/{genre_id}` должен вернуть информацию о жанре.

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

    genre_id = "ef86b8ff-3c82-4d31-ad8e-72b69f4e3f96"

    # 1. Генерируем данные для ES
    bulk_query = build_genre_bulk_data(count=60, query_prefix="Test genre")

    current_ids = {row["_id"] for row in bulk_query}
    for row in bulk_query:
        if row["_id"] == genre_id:
            new_id = str(uuid.uuid4())
            while new_id == genre_id or new_id in current_ids:
                new_id = str(uuid.uuid4())
            current_ids.remove(row["_id"])
            row["_id"] = new_id
            row["_source"]["id"] = new_id
            current_ids.add(new_id)

    bulk_query[0]["_id"] = genre_id
    bulk_query[0]["_source"]["id"] = genre_id

    # 2. Загружаем данные в ES
    await es_write_data(
        bulk_query,
        index=test_settings.es_genre_index,
        mapping=ES_GENRE_MAPPING
    )

    async with session.get(
        test_settings.service_url
        + f"/api/v1/genres/{genre_id}"
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_uuid_equal(body.get("uuid"), genre_id)
    assert_field_equal(body.get("name"), bulk_query[0]["_source"]["name"])


@pytest.mark.asyncio
async def test_genres_uses_redis_cache(
    es_test_genres, redis_client, http_session
):
    """Проверяет, что эндпоинт использует Redis для кеширования.

    После выполнения запроса должен появиться ключ кеша.

    Параметры
    ---------
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    redis_client: fixture
        Асинхронный клиент Redis.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии.

    Возвращает
    ---------
    None
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_length(body, 50)
    assert_body_item(body, {"uuid": str, "name": str})

    cache_keys = await redis_client.keys("genres:*")
    assert len(cache_keys) > 0


@pytest.mark.asyncio
async def test_genres_uses_redis_cache_on_repeat_query(
    es_test_genres, es_client_factory, redis_client, http_session
):
    """Проверяет, что повторный запрос использует кеш Redis.

    После первого запроса индекс удаляется, и второй запрос должен
    вернуть данные из кеша.

    Параметры
    ---------
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    es_client: AsyncElasticsearch
        Клиент Elasticsearch для операций с индексом.
    redis_client: fixture
        Асинхронный клиент Redis.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запросов.

    Возвращает
    ---------
    None
    """
    session = http_session

    # Первый запрос
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    ) as response:
        first_body = await response.json()
        first_status = response.status

    assert_validation_error_status(first_status, 200, first_body)
    assert_body_length(first_body, 50)
    assert_body_item(first_body, {"uuid": str, "name": str})

    cache_keys = await redis_client.keys("genres:*")
    assert len(cache_keys) > 0

    # Удаляем индекс, чтобы убедиться, что данные будут получены из кеша
    client = es_client_factory()
    try:
        await client.indices.delete(index=test_settings.es_genre_index)
    finally:
        await client.close()

    # Второй запрос
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    ) as response:
        second_body = await response.json()
        second_status = response.status

    assert_validation_error_status(second_status, 200, second_body)
    assert_body_length(second_body, 50)
    assert_body_item(second_body, {"uuid": str, "name": str})

    assert second_body == first_body


@pytest.mark.asyncio
async def test_genres_find_by_name(
    es_write_data, redis_client, http_session
):
    """Проверяет, что эндпоинт может найти жанры по имени.

    Запрос с `name="UnicumPracticum"` должен вернуть жанры, содержащие
    это имя.

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

    # 1. Генерируем данные для ES
    bulk_query = build_genre_bulk_data(count=60, query_prefix="Test film")

    name = "UnicumPracticum"

    bulk_query[0]["_source"]["name"] = name

    # 2. Загружаем данные в ES
    await es_write_data(
        bulk_query,
        index=test_settings.es_genre_index,
        mapping=ES_GENRE_MAPPING
    )

    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"name": name}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_item(body, {"uuid": str})
    assert_field_equal(body["results"][0]["name"], name)


@pytest.mark.asyncio
async def test_genres_find_by_name_no_results(
    es_test_genres, http_session
):
    """Проверяет, что эндпоинт возвращает пустой список.

    Запрос с `name="nonexistentphrase"` должен вернуть пустой список.

    Параметры
    ---------
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"name": "nonexistentphrase"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_length(body, 0)


@pytest.mark.asyncio
async def test_genres_find_by_filter_name(
    es_test_genres, http_session
):
    """Проверяет, что эндпоинт может найти жанры по имени через filter.

    Запрос с `filter[name]="practicum"` должен вернуть жанры,
    содержащие это имя.

    Параметры
    ---------
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"filter[name]": "practicum"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_item(body, {"uuid": str, "name": str})

    assert len(body["results"]) > 0
    for genre in body["results"]:
        assert "practicum" in genre["name"].lower()


@pytest.mark.asyncio
async def test_genres_find_by_filter_name_no_results(
    es_test_genres, http_session
):
    """Проверяет, что эндпоинт возвращает пустой список.

    Запрос с `filter[name]="nonexistentphrase"` должен вернуть пустой
    список.

    Параметры
    ---------
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"filter[name]": "nonexistentphrase"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_length(body, 0)


@pytest.mark.asyncio
async def test_genres_sort_ordering_by_name(es_test_genres, http_session):
    """Проверяет, что сортировка по имени работает корректно.

    Запрос с `sort=name` должен вернуть жанры, отсортированные по имени
    в порядке возрастания.

    Параметры
    ---------
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"sort": "name", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_item(body, {"uuid": str, "name": str})

    names = [genre["name"] for genre in body["results"]]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_genres_sort_ordering_by_name_descending(
    es_test_genres, http_session
):
    """Проверяет, что сортировка по имени в обратном порядке работает.

    Запрос с `sort=-name` должен вернуть жанры, отсортированные по имени
    в порядке убывания.

    Параметры
    ---------
    es_test_genres: fixture
        Фикстура, заполняющая ES тестовыми жанрами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии.

    Возвращает
    ---------
    None
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"sort": "-name", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error_status(status, 200, body)
    assert_body_item(body, {"uuid": str, "name": str})

    names = [genre["name"] for genre in body["results"]]
    assert names == sorted(names, reverse=True)
