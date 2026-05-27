"""Функциональные тесты эндпоинта /api/v1/films/search

Проверяется валидация запросов, пагинация, кеширование Redis и обработка
фразовых запросов.
"""

import pytest
from settings import test_settings
from conftest import build_film_bulk_data
from conftest import fetch_all_pages
from utils.helpers import assert_validation_error


@pytest.mark.asyncio
async def test_films_search_validations_query_required(http_session):
    """Проверяет, что отсутствие query возвращает 422.

    Запрос без параметра query должен привести к ошибке валидации
    и ответу со статусом 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films/search"
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix='missing',
        loc_contains='["query","query"]',
        msg_substring='required'
    )

@pytest.mark.asyncio
async def test_films_search_validations_query_empty(http_session):
    """Проверяет, что пустой query возвращает ошибку валидации.

    Запрос с query= пустой строка должен вернуть подробное сообщение
    о минимальной длине строки.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": ""}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix='string_too_short',
        loc_contains='["query","query"]',
        ctx_contains={"min_length": 1}
    )


@pytest.mark.asyncio
async def test_films_search_validation_sort(http_session):
    """Проверяет валидацию параметра сортировки.

    Запрос с невалидным значением sort должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "Test", "sort": "invalid"},
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix='string_pattern_mismatch',
        loc_contains='["query","sort"]',
        ctx_contains={"pattern": r"^-?imdb_rating$"},
    )


@pytest.mark.asyncio
async def test_films_validation_sort_invalid_field(
    es_test_films, http_session
):
    """Проверяет, что сортировка по несуществующему полю возвращает 422.

    Запрос с sort=nonexistent_field должен привести к ошибке валидации и
    ответу со статусом 422.
    Запрос с sort="" должен привести к ошибке валидации и
    ответу со статусом 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "Test", "sort": "nonexistent_field"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix='string_pattern_mismatch',
        loc_contains='["query","sort"]',
        ctx_contains={"pattern": r"^-?imdb_rating$"},
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
    """Проверяет ограничения page_size при валидации запроса.

    Должна возвращаться ошибка при значениях меньше 1 и больше 100.
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "test practicum", "page_size": page_size}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix=["less_than_equal", "greater_than_equal", "int_parsing"],
        loc_contains='["query","page_size"]',
        ctx_contains=(
            None if page_size == "not_a_number"
            else [{"le": 100}, {"ge": 1}]
        ),
        msg_substring=(
            "unable to parse string as an integer"
            if page_size == "not_a_number"
            else None
        )
    )


@pytest.mark.parametrize(
    "page_number",
    [
        -1, 0, 101, "not_a_number",
    ],
)
@pytest.mark.asyncio
async def test_films_search_validation_page_number_bounds(
    page_number, es_test_films, http_session
):
    """Проверяет, что невалидное значение page_number возвращает 422.

    Запрос с невалидным значением page_number должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "test practicum", "page_number": page_number}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix=["less_than_equal", "greater_than_equal", "int_parsing"],
        loc_contains='["query","page_number"]',
        ctx_contains=(
            None if page_number == "not_a_number"
            else [{"ge": 1}, {"le": 100}]
        ),
        msg_substring=(
            "unable to parse string as an integer"
            if page_number == "not_a_number"
            else None
        )
    )


@pytest.mark.asyncio
async def test_films_search_returns_n_films(es_test_films, http_session):
    """Проверяет, что API возвращает указанное число записей.

    Запрос с page_size=50 должен вернуть ровно 50 элементов.
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "test", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_length=50,
        body_item={"uuid": str, "title": str}
    )


@pytest.mark.asyncio
async def test_films_search_returns_all_films(
    es_test_films, http_session
):
    """Проверяет, что полный результат поиска можно получить постранично.

    Запрос с page_size=50 и перебором всех страниц должен вернуть все
    5000 фильмов для запроса query=Test.
    """
    result = await fetch_all_pages(
        http_session,
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "Test practicum"},
        page_size=50
    )

    assert_validation_error(
        result["status"],
        200,
        result["items"],
        body_length=5000,
        body_item={"uuid": str, "title": str}
    )


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

    Загрузить документы с конкретным названием и проверить ответы
    на фразовые запросы.
    """
    session = http_session
    # 1. Генерируем данные для ES
    bulk_query = build_film_bulk_data(count=60, query_prefix="Test film")

    # 2. Загружаем данные в ES
    await es_write_data(bulk_query, index=test_settings.es_film_index)

    # 3. Запрашиваем данные из ES по API
    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": search_data}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "title": str},
        body_length=expected_answer
    )


@pytest.mark.asyncio
async def test_films_search_uses_redis_cache(
    es_test_films, redis_client, http_session
):
    """Проверяет, что результаты запроса кэшируются в Redis.

    После выполнения запроса должен появиться ключ кеша.
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "test", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "title": str},
        body_length=50,
    )

    cache_keys = await redis_client.keys("films:search:*")
    assert len(cache_keys) > 0


@pytest.mark.asyncio
async def test_films_search_uses_redis_cache_on_repeat_query(
    es_test_films, es_client, redis_client, http_session
):
    """Проверяет повторный запрос с использованием кэша Redis.

    После первого запроса индекс удаляется, и второй запрос должен
    вернуть данные из кеша.
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "test", "page_size": 50}
    ) as first_response:
        first_body = await first_response.json()
        first_status = first_response.status

    assert_validation_error(
        first_status,
        200,
        first_body,
        body_item={"uuid": str, "title": str},
        body_length=50,
    )

    cache_keys = await redis_client.keys("films:search:*")
    assert len(cache_keys) > 0

    # Удаляем индекс, чтобы убедиться, что второй запрос берет данные из Redis.
    await es_client.indices.delete(index=test_settings.es_film_index)

    async with session.get(
        test_settings.service_url + "/api/v1/films/search",
        params={"query": "test", "page_size": 50}
    ) as second_response:
        second_body = await second_response.json()
        second_status = second_response.status

    assert_validation_error(
        second_status,
        200,
        second_body,
        body_item={"uuid": str, "title": str},
        body_length=50,
    )

    assert second_body == first_body
