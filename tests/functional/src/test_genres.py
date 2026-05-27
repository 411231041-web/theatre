"""Функциональные тесты эндпоинта /api/v1/genres

Проверяется валидация запросов, пагинация, кеширование Redis и обработка
фразовых запросов.
"""

import uuid
import pytest
from settings import test_settings
from conftest import build_genre_bulk_data
from conftest import fetch_all_pages
from utils.helpers import assert_validation_error


@pytest.mark.asyncio
async def test_genres_validation_sort(http_session):
    """Проверяет валидацию параметра сортировки.

    Запрос с невалидным значением sort должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"sort": "invalid"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix='string_pattern_mismatch',
        loc_contains='["query","sort"]',
        ctx_contains={"pattern": r"^-?name$"},
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

    Запрос с sort=nonexistent_field должен привести к ошибке валидации и
    ответу со статусом 422.
    Запрос с sort="" должен привести к ошибке валидации и
    ответу со статусом 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"sort": sort_value}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix='string_pattern_mismatch',
        loc_contains='["query","sort"]',
        ctx_contains={"pattern": r"^-?name$"},
    )


@pytest.mark.parametrize(
    "page_size",
    [
        -1, 0, 101,
    ],
)
@pytest.mark.asyncio
async def test_genres_validation_page_size_bounds(
    page_size, http_session
):
    """Проверяет валидацию параметра page_size.

    Запрос с невалидным значением page_size должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": page_size}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        loc_contains='["query","page_size"]',
    )


@pytest.mark.asyncio
async def test_genres_validation_page_size_wrong_type(
    es_test_genres, http_session
):
    """Проверяет валидацию типа параметра page_size.

    Запрос с невалидным типом для page_size должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": "not_a_number"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix='int_parsing',
        loc_contains='["query","page_size"]',
        msg_substring='unable to parse string as an integer'
    )


@pytest.mark.parametrize(
    "page_number",
    [
        -1, 0, 101,
    ],
)
@pytest.mark.asyncio
async def test_genres_validation_page_number_bounds(
    page_number, es_test_genres, http_session
):
    """Проверяет валидацию параметра page_number.

    Запрос с невалидным значением page_number должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_number": page_number}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        loc_contains='["query","page_number"]',
    )


@pytest.mark.asyncio
async def test_genres_validation_page_number_wrong_type(
    es_test_genres, http_session
):
    """Проверяет валидацию типа параметра page_number.

    Запрос с невалидным типом для page_number должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_number": "not_a_number"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        422,
        body['detail'][0],
        type_prefix='int_parsing',
        loc_contains='["query","page_number"]',
        msg_substring='unable to parse string as an integer'
    )


@pytest.mark.asyncio
async def test_genres_return_n_genres(es_test_genres, http_session):
    """Проверяет, что эндпоинт возвращает правильное количество записей.

    Запрос с page_size=50 должен вернуть 50 жанров.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_length=50,
        body_item={"uuid": str, "name": str}
    )


@pytest.mark.asyncio
async def test_genres_return_all_genres(es_test_genres, http_session):
    """Проверяет, что эндпоинт возвращает все записи при запросе всех страниц.

    Запрос с page_size=50 и перебором всех страниц должен вернуть все
    5000 жанров.
    """
    result = await fetch_all_pages(
        http_session,
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    )

    assert_validation_error(
        result["status"],
        200,
        result["items"],
        body_length=5000,
        body_item={"uuid": str, "name": str}
    )


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

    Запрос с невалидным UUID должен вернуть 422, с несуществующим - 404,
    с существующим - 200.
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
    await es_write_data(bulk_query, index=test_settings.es_genre_index)

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
        msg_substring = None
        detail = body
    else:
        if expected_status == 422:
            type_prefix = "uuid_parsing"
            loc_contains = '["path","genre_id"]'
            msg_substring = "invalid character"
        else:
            type_prefix = None
            loc_contains = None
            msg_substring = None

        uuid_val = None
        name_val = None
        expected_uuid = None
        expected_name = None
        detail = (body["detail"][0] if expected_status == 422 else body)

    assert_validation_error(
        status,
        expected_status,
        detail,
        type_prefix=type_prefix,
        loc_contains=loc_contains,
        uuid=uuid_val,
        uuid_expected=expected_uuid,
        caption=name_val,
        caption_expected=expected_name,
        msg_substring=msg_substring
    )


@pytest.mark.asyncio
async def test_genres_get_film_by_uuid(
    es_write_data, redis_client, http_session,
):
    """Проверяет получение информации о жанре по UUID.

    Запрос к /api/v1/genres/{genre_id} должен вернуть информацию о жанре.
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
    await es_write_data(bulk_query, index=test_settings.es_genre_index)

    async with session.get(
        test_settings.service_url
        + f"/api/v1/genres/{genre_id}"
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        uuid=body.get("uuid"),
        uuid_expected=genre_id,
        caption=body.get("name"),
        caption_expected=bulk_query[0]["_source"]["name"],
    )


@pytest.mark.asyncio
async def test_genres_uses_redis_cache(
    es_test_genres, redis_client, http_session
):
    """Проверяет, что эндпоинт использует Redis для кеширования.

    После выполнения запроса должен появиться ключ кеша.
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_length=50,
        body_item={"uuid": str, "name": str}
    )

    cache_keys = await redis_client.keys("genres:*")
    assert len(cache_keys) > 0


@pytest.mark.asyncio
async def test_genres_uses_redis_cache_on_repeat_query(
    es_test_genres, es_client, redis_client, http_session
):
    """Проверяет, что повторный запрос использует кеш Redis.

    После первого запроса индекс удаляется, и второй запрос должен
    вернуть данные из кеша.
    """
    session = http_session

    # Первый запрос
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    ) as response:
        first_body = await response.json()
        first_status = response.status

    assert_validation_error(
        first_status,
        200,
        first_body,
        body_length=50,
        body_item={"uuid": str, "name": str}
    )

    cache_keys = await redis_client.keys("genres:*")
    assert len(cache_keys) > 0

    # Удаляем индекс, чтобы убедиться, что данные будут получены из кеша
    await es_client.indices.delete(index=test_settings.es_genre_index)

    # Второй запрос
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"page_size": 50}
    ) as response:
        second_body = await response.json()
        second_status = response.status

    assert_validation_error(
        second_status,
        200,
        second_body,
        body_length=50,
        body_item={"uuid": str, "name": str}
    )

    assert second_body == first_body


@pytest.mark.asyncio
async def test_genres_find_by_name(es_test_genres, http_session):
    """Проверяет, что эндпоинт может найти жанры по имени.

    Запрос с name="practicum" должен вернуть жанры, содержащие это имя.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"name": "practicum"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "name": str}
    )

    assert len(body) > 0
    for genre in body:
        assert "practicum" in genre["name"].lower()


@pytest.mark.asyncio
async def test_genres_find_by_name_no_results(
    es_test_genres, http_session
):
    """Проверяет, что эндпоинт возвращает пустой список.

    Запрос с name="nonexistentphrase" должен вернуть пустой список.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"name": "nonexistentphrase"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_length=0
    )


@pytest.mark.asyncio
async def test_genres_find_by_filter_name(
    es_test_genres, http_session
):
    """Проверяет, что эндпоинт может найти жанры по имени.

    Запрос с filter[name]="practicum" должен вернуть жанры, содержащие это имя.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"filter[name]": "practicum"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "name": str}
    )

    assert len(body) > 0
    for genre in body:
        assert "practicum" in genre["name"].lower()


@pytest.mark.asyncio
async def test_genres_find_by_filter_name_no_results(
    es_test_genres, http_session
):
    """Проверяет, что эндпоинт возвращает пустой список.

    Запрос с filter[name]="nonexistentphrase" должен вернуть пустой список.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"filter[name]": "nonexistentphrase"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_length=0
    )


@pytest.mark.asyncio
async def test_genres_sort_ordering_by_name(es_test_genres, http_session):
    """Проверяет, что сортировка по имени работает корректно.

    Запрос с sort=name должен вернуть жанры, отсортированные по имени
    в порядке возрастания.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"sort": "name", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "name": str}
    )

    names = [genre["name"] for genre in body]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_genres_sort_ordering_by_name_descending(
    es_test_genres, http_session
):
    """Проверяет, что сортировка по имени в обратном порядке работает.

    Запрос с sort=-name должен вернуть жанры, отсортированные по имени
    в порядке убывания.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/genres",
        params={"sort": "-name", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "name": str}
    )

    names = [genre["name"] for genre in body]
    assert names == sorted(names, reverse=True)
