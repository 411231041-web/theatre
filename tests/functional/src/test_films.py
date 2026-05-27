"""Функциональные тесты эндпоинта /api/v1/films

Проверяется валидация запросов, пагинация, кеширование Redis и обработка
фразовых запросов.
"""

import uuid
import pytest
from settings import test_settings
from conftest import build_film_bulk_data
from conftest import fetch_all_pages
from utils.helpers import assert_validation_error


@pytest.mark.parametrize(
    "sort_value",
    [
        "nonexistent_field",
        "",
    ]
)
@pytest.mark.asyncio
async def test_films_validation_sort_invalid_field(
    sort_value, es_test_films, http_session
):
    """Проверяет, что сортировка по несуществующему полю возвращает 422.

    Запрос с sort=nonexistent_field должен привести к ошибке валидации и
    ответу со статусом 422.
    Запрос с sort="" должен привести к ошибке валидации и
    ответу со статусом 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
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
        ctx_contains={"pattern": r"^-?imdb_rating$"},
    )


@pytest.mark.parametrize(
    "page_size",
    [
        -1, 0, 101, "not_a_number",
    ],
)
@pytest.mark.asyncio
async def test_films_validation_page_size_bounds(
    page_size, http_session
):
    """Проверяет, что невалидное значение page_size возвращает 422.

    Запрос с невалидным значением page_size должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"page_size": page_size}
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
async def test_films_validation_page_number_bounds(
    page_number, es_test_films, http_session
):
    """Проверяет, что невалидное значение page_number возвращает 422.

    Запрос с невалидным значением page_number должен вернуть 422.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"page_number": page_number}
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
            else [{"le": 100}, {"ge": 1}]
        ),
        msg_substring=(
            "unable to parse string as an integer"
            if page_number == "not_a_number"
            else None
        )
    )


@pytest.mark.asyncio
async def test_films_return_n_films(es_test_films, http_session):
    """Проверяет, что запрос возвращает ожидаемое количество записей.

    Запрос с page_size=50 должен вернуть ровно 50 записей.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"page_size": 50}
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
async def test_films_return_all_films(es_test_films, http_session):
    """Проверяет, что эндпоинт возвращает все записи при запросе всех страниц.

    Запрос с page_size=50 и перебором всех страниц должен вернуть все
    5000 фильмов.
    """
    result = await fetch_all_pages(
        http_session,
        test_settings.service_url + "/api/v1/films",
        params={"page_size": 50}
    )

    assert_validation_error(
        result["status"],
        200,
        result["items"],
        body_length=5000,
        body_item={"uuid": str, "title": str}
    )


@pytest.mark.asyncio
async def test_films_filtering_by_genre(es_test_films, http_session):
    """Проверяет, что фильтрация по жанру работает корректно.

    Запрос с фильтром genre=Action должен вернуть только фильмы
    с жанром Action.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"genre": "Action"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "title": str}
    )
    for film in body:
        assert "Action" in film["genres"]


@pytest.mark.asyncio
async def test_films_filtering_by_genre_alias(es_test_films, http_session):
    """Проверяет, что фильтрация по жанру через alias работает корректно.

    Запрос с фильтром filter[genre]=Action должен вернуть только фильмы
    с жанром Action.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"filter[genre]": "Action"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "title": str}
    )
    for film in body:
        assert "Action" in film["genres"]


@pytest.mark.asyncio
async def test_films_filtering_by_genre_wrong_genre(
    es_test_films, http_session
):
    """Проверяет, что фильтрация по несуществующему жанру возвращает
    пустой список.

    Запрос с фильтром genre=NonExistentGenre должен вернуть пустой список.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"genre": "NonExistentGenre"}
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
async def test_films_filtering_by_genre_wrong_genre_alias(
    es_test_films, http_session
):
    """Проверяет, что фильтрация по несуществующему жанру через alias
    возвращает пустой список.

    Запрос с фильтром filter[genre]=NonExistentGenre должен вернуть пустой
    список.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"filter[genre]": "NonExistentGenre"}
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
async def test_films_sort_ordering_by_rating(es_test_films, http_session):
    """Проверяет, что сортировка по рейтингу работает корректно.

    Запрос с sort=imdb_rating должен вернуть фильмы, отсортированные по
    рейтингу в порядке возрастания.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"sort": "imdb_rating", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "title": str}
    )
    ratings = [film["imdb_rating"] for film in body]
    assert ratings == sorted(ratings)


@pytest.mark.asyncio
async def test_films_sort_ordering_by_rating_descending(
    es_test_films, http_session
):
    """Проверяет, что сортировка по рейтингу в обратном порядке работает
    корректно.

    Запрос с sort=-imdb_rating должен вернуть фильмы, отсортированные по
    рейтингу в порядке убывания.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"sort": "-imdb_rating", "page_size": 50}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str, "title": str}
    )
    ratings = [film["imdb_rating"] for film in body]
    assert ratings == sorted(ratings, reverse=True)


@pytest.mark.asyncio
async def test_films_uses_redis_cache(
    es_test_films, redis_client, http_session
):
    """Проверяет, что результаты запроса кэшируются в Redis.

    После выполнения запроса должен появиться ключ кеша.
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"page_size": 50}
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

    cache_keys = await redis_client.keys("films:*")
    assert len(cache_keys) > 0


@pytest.mark.asyncio
async def test_films_uses_redis_cache_on_repeat_query(
    es_test_films, es_client, redis_client, http_session
):
    """Проверяет повторный запрос с использованием кэша Redis.

    После первого запроса индекс удаляется, и второй запрос должен
    вернуть данные из кеша.
    """
    session = http_session

    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"page_size": 50}
    ) as response:
        first_body = await response.json()
        first_status = response.status

    assert_validation_error(
        first_status,
        200,
        first_body,
        body_length=50,
        body_item={"uuid": str, "title": str}
    )

    cache_keys = await redis_client.keys("films:*")
    assert len(cache_keys) > 0

    # Удаляем индекс, чтобы убедиться, что данные будут получены из кеша
    await es_client.indices.delete(index=test_settings.es_film_index)

    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"page_size": 50}
    ) as second_response:
        second_body = await second_response.json()
        second_status = second_response.status

    assert_validation_error(
        second_status,
        200,
        second_body,
        body_length=50,
        body_item={"uuid": str, "title": str}
    )
    assert second_body == first_body


@pytest.mark.parametrize(
    ("film_id", "expected_status"),
    [
        ("ef86b8ff-3c82-4d31-ad8e-72b69f4e3f96", 200),  # Существующий UUID
        ("ef86b8ff-3c82-4d31-ad8e-72b69f4e3f97", 404),  # Не существующий UUID
        ("invalid-uuid", 422),  # Невалидный UUID
    ]
)
@pytest.mark.asyncio
async def test_films_get_by_uuid_validation(
    film_id, expected_status, es_write_data, redis_client, http_session
):
    """Проверяет валидацию film_id.

    Запрос с несуществующим film_id должен вернуть 404,
    а с невалидным UUID - 422.
    """
    session = http_session
    # 1. Генерируем данные для ES
    bulk_query = build_film_bulk_data(count=60, query_prefix="Test film")

    if expected_status == 200:
        bulk_query[0]["_id"] = film_id
        bulk_query[0]["_source"]["id"] = film_id

    if expected_status == 404:
        current_ids = {row["_id"] for row in bulk_query}
        for row in bulk_query:
            if row["_id"] == film_id:
                new_id = str(uuid.uuid4())
                while new_id == film_id or new_id in current_ids:
                    new_id = str(uuid.uuid4())
                current_ids.remove(row["_id"])
                row["_id"] = new_id
                row["_source"]["id"] = new_id
                current_ids.add(new_id)

    # 2. Загружаем данные в ES
    await es_write_data(bulk_query, index=test_settings.es_film_index)

    async with session.get(
        test_settings.service_url + f"/api/v1/films/{film_id}"
    ) as response:
        body = await response.json()
        status = response.status

    if expected_status == 200:
        uuid = body["uuid"]
        caption = body["title"]
        expected_uuid = film_id
        expected_caption = bulk_query[0]["_source"]["title"]
        type_prefix = None
        loc_contains = None
        msg_substring = None
    else:
        if expected_status == 422:
            type_prefix = "uuid_parsing"
            loc_contains = '["path","film_id"]'
            msg_substring = "invalid character"
        else:
            type_prefix = None
            loc_contains = None
            msg_substring = None

        uuid = None
        caption = None
        expected_uuid = None
        expected_caption = None

    assert_validation_error(
        status,
        expected_status,
        detail=(body["detail"][0] if expected_status == 422 else body),
        type_prefix=type_prefix,
        loc_contains=loc_contains,
        uuid=uuid,
        uuid_expected=expected_uuid,
        caption=caption,
        caption_expected=expected_caption,
        msg_substring=msg_substring
    )


@pytest.mark.asyncio
async def test_films_find_films_by_title(
    es_write_data, redis_client, http_session
):
    """Проверяет, что эндпоинт может найти фильмы по названию.

    Запрос с title="practicum" должен вернуть фильмы, содержащие эту фразу.
    """
    session = http_session

    # 1. Генерируем данные для ES
    bulk_query = build_film_bulk_data(count=60, query_prefix="Test film")

    title = "Unicum practicum"

    bulk_query[0]["_source"]["title"] = title

    # 2. Загружаем данные в ES
    await es_write_data(bulk_query, index=test_settings.es_film_index)

    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"title": title}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_item={"uuid": str},
        caption=body[0]["title"],
        caption_expected=title
    )


@pytest.mark.asyncio
async def test_films_find_films_by_title_no_results(
    es_test_films, http_session
):
    """Проверяет, что эндпоинт возвращает пустой список для
    несуществующего названия.

    Запрос с title="nonexistentphrase" должен вернуть пустой список.
    """
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/films",
        params={"title": "nonexistentphrase"}
    ) as response:
        body = await response.json()
        status = response.status

    assert_validation_error(
        status,
        200,
        body,
        body_length=0
    )
