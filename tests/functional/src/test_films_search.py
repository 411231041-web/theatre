"""Функциональные тесты эндпоинта /api/v1/films/search

Проверяется валидация запросов, пагинация, кеширование Redis и обработка
фразовых запросов.
"""

import pytest
from settings import test_settings
from utils.assert_helpers import (
    assert_validation_error_status,
    assert_validation_error_type,
    assert_validation_error_location,
    assert_validation_error_context,
    assert_body_length,
    assert_body_item,
    get_json,
)
from utils.http_helpers import fetch_all_pages
from utils.test_data_helpers import build_film_bulk_data


@pytest.mark.asyncio
async def test_films_search_validations_query_required(http_session):
    """Проверяет, что отсутствие query возвращает 422.

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
    status, body = await get_json(
        session.get(test_settings.service_url + "/api/v1/films/search")
    )

    assert_validation_error_status(status, 422, body['detail'][0])
    assert_validation_error_type(body['detail'][0], type_prefix='missing')
    assert_validation_error_location(
        body['detail'][0], loc_contains='["query","query"]'
    )


@pytest.mark.asyncio
async def test_films_search_validations_query_empty(http_session):
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
    status, body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": ""}
        )
    )

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
async def test_films_search_validation_sort(http_session):
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
    status, body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": "Test", "sort": "invalid"},
        )
    )

    assert_validation_error_status(status, 422, body['detail'][0])
    assert_validation_error_type(
        body['detail'][0], type_prefix='string_pattern_mismatch'
    )
    assert_validation_error_location(
        body['detail'][0], loc_contains='["query","sort"]'
    )
    assert_validation_error_context(
        body['detail'][0], ctx_contains={"pattern": r"^-?imdb_rating$"}
    )


@pytest.mark.asyncio
async def test_films_validation_sort_invalid_field(
    es_test_films, http_session
):
    """Проверяет, что сортировка по несуществующему полю возвращает 422.

    Запрос с `sort=nonexistent_field` должен привести к ошибке
    валидации и ответу со статусом 422.

    Параметры
    ---------
    es_test_films: fixture
        Фикстура, заполняющая ES тестовыми фильмами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    status, body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": "Test", "sort": "nonexistent_field"}
        )
    )

    assert_validation_error_status(status, 422, body['detail'][0])
    assert_validation_error_type(
        body['detail'][0], type_prefix='string_pattern_mismatch'
    )
    assert_validation_error_location(
        body['detail'][0], loc_contains='["query","sort"]'
    )
    assert_validation_error_context(
        body['detail'][0], ctx_contains={"pattern": r"^-?imdb_rating$"}
    )


@pytest.mark.parametrize(
    "page_size",
    [
        -1, 0, 101, "not_a_number",
    ],
)
@pytest.mark.asyncio
async def test_films_search_validation_page_size_bounds(
    page_size, http_session
):
    """Проверяет ограничения `page_size` при валидации запроса.

    Должна возвращаться ошибка при значениях меньше 1 и больше 100.

    Параметры
    ---------
    page_size: int | str
        Тестовое значение параметра `page_size` (может быть строкой).
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session

    status, body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": "test practicum", "page_size": page_size}
        )
    )

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
async def test_films_search_validation_page_number_bounds(
    page_number, es_test_films, http_session
):
    """Проверяет, что невалидное значение `page_number` возвращает 422.

    Параметры
    ---------
    page_number: int | str
        Тестовое значение `page_number`.
    es_test_films: fixture
        Фикстура, заполняющая ES тестовыми фильмами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session
    status, body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": "test practicum", "page_number": page_number}
        )
    )

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
async def test_films_search_returns_n_films(es_test_films, http_session):
    """Проверяет, что API возвращает указанное число записей.

    Запрос с `page_size=50` должен вернуть ровно 50 элементов.

    Параметры
    ---------
    es_test_films: fixture
        Фикстура, заполняющая ES тестовыми фильмами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запроса.

    Возвращает
    ---------
    None
    """
    session = http_session

    status, body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": "test", "page_size": 50}
        )
    )

    assert_validation_error_status(status, 200, body)
    assert_body_length(body, 50)
    assert_body_item(body, {"uuid": str, "title": str})


@pytest.mark.asyncio
async def test_films_search_returns_all_films(
    es_test_films, http_session
):
    """Проверяет, что полный результат поиска можно получить постранично.

    Запрос с `page_size=50` и перебором всех страниц должен вернуть все
    5000 фильмов для запроса `query=Test`.

    Параметры
    ---------
    es_test_films: fixture
        Фикстура, заполняющая ES тестовыми фильмами.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запросов.

    Возвращает
    ---------
    None
    """
    result = await fetch_all_pages(
        http_session,
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "Test practicum"},
        page_size=50
    )

    assert_validation_error_status(result["status"], 200, result["items"])
    assert_body_length(result["items"], 5000)
    assert_body_item(result["items"], {"uuid": str, "title": str})


@pytest.mark.parametrize(
    "search_data, expected_answer",
    [
        ("Test film", 50),
        ("Mashed potato", 0),
    ],
)
@pytest.mark.asyncio
async def test_films_search_phrase_query(
    search_data, expected_answer, es_write_data, http_session
):
    """Проверяет поиск по фразе с загруженными данными.

    Загружает документы с конкретным названием и проверяет ответы
    на фразовые запросы.

    Параметры
    ---------
    search_data: str
        Тестовая поисковая фраза.
    expected_answer: int
        Ожидаемое количество результатов.
    es_write_data: fixture
        Функция загрузки данных в Elasticsearch.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запросов.

    Возвращает
    ---------
    None
    """
    session = http_session
    # 1. Генерируем данные для ES
    bulk_query = build_film_bulk_data(count=60, query_prefix="Test film")

    # 2. Загружаем данные в ES
    await es_write_data(bulk_query, index=test_settings.es_film_index)

    # 3. Запрашиваем данные из ES по API
    status, body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": search_data}
        )
    )

    assert_validation_error_status(status, 200, body)
    assert_body_item(body, {"uuid": str, "title": str})
    assert_body_length(body, expected_answer)


@pytest.mark.asyncio
async def test_films_search_uses_redis_cache(
    es_test_films, redis_client, http_session
):
    """Проверяет, что результаты запроса кэшируются в Redis.

    После выполнения запроса должен появиться ключ кеша.

    Параметры
    ---------
    es_test_films: fixture
        Фикстура, заполняющая ES тестовыми фильмами.
    redis_client: fixture
        Асинхронный клиент Redis.
    http_session: aiohttp.ClientSession
        Фикстура aiohttp-сессии для выполнения запросов.

    Возвращает
    ---------
    None
    """
    session = http_session

    status, body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": "test", "page_size": 50}
        )
    )

    assert_validation_error_status(status, 200, body)
    assert_body_item(body, {"uuid": str, "title": str})
    assert_body_length(body, 50)

    cache_keys = await redis_client.keys("films:search:*")
    assert len(cache_keys) > 0


@pytest.mark.asyncio
async def test_films_search_uses_redis_cache_on_repeat_query(
    es_test_films, es_client_factory, redis_client, http_session
):
    """Проверяет повторный запрос с использованием кэша Redis.

    После первого запроса индекс удаляется, и второй запрос должен
    вернуть данные из кеша.

    Параметры
    ---------
    es_test_films: fixture
        Фикстура, заполняющая ES тестовыми фильмами.
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

    first_status, first_body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": "test", "page_size": 50}
        )
    )

    assert_validation_error_status(first_status, 200, first_body)
    assert_body_item(first_body, {"uuid": str, "title": str})
    assert_body_length(first_body, 50)

    cache_keys = await redis_client.keys("films:search:*")
    assert len(cache_keys) > 0

    # Удаляем индекс, чтобы убедиться, что второй запрос берет данные
    # из Redis.
    client = es_client_factory()
    try:
        await client.indices.delete(index=test_settings.es_film_index)
    finally:
        await client.close()

    second_status, second_body = await get_json(
        session.get(
            test_settings.service_url + "/api/v1/films/search",
            params={"query": "test", "page_size": 50}
        )
    )

    assert_validation_error_status(second_status, 200, second_body)
    assert_body_item(second_body, {"uuid": str, "title": str})
    assert_body_length(second_body, 50)

    assert second_body == first_body
