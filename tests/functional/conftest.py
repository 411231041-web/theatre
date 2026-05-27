"""Фикстуры и утилиты для функциональных тестов поиска.

В файле определены общие клиенты Elasticsearch, Redis и aiohttp, а также
инструменты для подготовки и загрузки тестовых данных.
"""

import asyncio

import aiohttp
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from settings import test_settings
from testdata.es_mapping import ES_FILM_MAPPING
from testdata.es_mapping import ES_GENRE_MAPPING
from testdata.es_mapping import ES_PERSON_MAPPING
from utils.test_data import build_film_bulk_data
from utils.test_data import build_genre_bulk_data
from utils.test_data import build_person_bulk_data


async def _recreate_index(
    es_client: AsyncElasticsearch, index: str, mapping: dict
) -> None:
    """Удаляет и создаёт индекс Elasticsearch с указанным маппингом.

    Если индекс существует, сначала удаляет его, а затем создаёт заново
    с переданным маппингом.
    """
    if await es_client.indices.exists(index=index):
        await es_client.indices.delete(index=index)
    await es_client.indices.create(index=index, mappings=mapping)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Создаёт отдельный цикл событий для сессии pytest.

    Фикстура создаёт новый цикл событий; его закрытие происходит после
    завершения сессии тестов.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(name="es_client", scope="session")
async def es_client():
    """Создаёт клиент AsyncElasticsearch на время сессии.

    Клиент используется для всех запросов тестовой сессии и закрывается
    после завершения тестов.
    """
    client = AsyncElasticsearch(
        hosts=[test_settings.es_url], verify_certs=False
    )
    yield client
    await client.close()


@pytest_asyncio.fixture(name="es_write_data", scope="session")
def es_write_data(es_client):
    """Возвращает функцию записи данных в Elasticsearch.

    Каждый вызов пересоздаёт индекс и загружает переданный набор данных.
    """

    async def inner(data: list[dict], index: str = "", mapping: dict = None):
        """Записать данные в индекс и обновить его."""
        await _recreate_index(
            es_client, index, mapping
        )
        _, errors = await async_bulk(client=es_client, actions=data)
        if errors:
            raise RuntimeError("Ошибка записи данных в Elasticsearch")

        await es_client.indices.refresh(index=index)

    return inner


@pytest_asyncio.fixture(name="es_film_data", scope="session")
def es_film_data():
    """Возвращает фабрику данных фильмов для тестов.

    Используется для генерации постоянных наборов фильмов с нужным
    префиксом запроса.
    """

    def generate_film_data(
            count: int = 5000, query_prefix: str = "Test movie"
    ) -> list[dict]:
        """Генерирует список bulk-документов для заданного запроса.

        Возвращает данные, готовые для записи в Elasticsearch.
        """
        return build_film_bulk_data(count, query_prefix)

    return generate_film_data


@pytest_asyncio.fixture(name="redis_client", scope="function")
async def redis_client():
    """
    Фикстура для создания и закрытия Redis-клиента.

    Автоматически очищает базу данных перед тестом.
    Закрывает соединение после.
    """
    from redis.asyncio import Redis

    client = Redis(
        host=test_settings.redis_host,
        port=test_settings.redis_port,
        db=0,
    )
    await client.flushdb()
    yield client
    await client.aclose()


@pytest_asyncio.fixture(name="http_session", scope="function")
async def http_session():
    """
    Фикстура для создания и закрытия aiohttp.ClientSession.

    Возвращает только `session`. URL эндпоинта указывается прямо в тестах.
    """
    session = aiohttp.ClientSession()
    yield session
    await session.close()


async def fetch_all_pages(
    session: aiohttp.ClientSession,
    url: str,
    params: dict | None = None,
    page_size: int = 100,
) -> dict[str, object]:
    """
    Получить все элементы, постранично обходя API.

    Если точка API разрешает максимум 100 записей на страницу, то
    метод делает несколько последовательных запросов, пока не соберёт
    все элементы.

    Args:
        session: aiohttp-клиент для запросов.
        url: Базовый URL эндпоинта.
        params: Дополнительные query-параметры.
        page_size: Запрашиваемый размер страницы, максимум 100.

    Returns:
        dict[str, object]: Результат с полями `status` и `items`.
            `status` — HTTP-статус последнего запроса.
            `items` — список полученных объектов.
            `error` — необязательное описание ошибки при частичном
                или неверном ответе.
    """
    params = dict(params or {})
    page_size = min(page_size, 100)
    params["page_size"] = page_size
    page_number = 1
    all_items: list[dict] = []

    while True:
        params["page_number"] = page_number
        async with session.get(url, params=params) as response:
            status = response.status
            if status != 200:
                body = await response.json()
                if (
                    status == 422
                    and page_number > 1
                    and isinstance(body, dict)
                    and isinstance(body.get("detail"), list)
                    and any(
                        isinstance(item, dict)
                        and item.get("loc") == ["query", "page_number"]
                        and isinstance(item.get("msg"), str)
                        and "less than or equal to" in item.get("msg")
                        for item in body["detail"]
                    )
                ):
                    break

                return {
                    "status": status,
                    "items": all_items,
                    "error": body,
                }

            page = await response.json()

        if not isinstance(page, list):
            return {
                "status": 500,
                "items": all_items,
                "error": "Ожидался список данных на каждой странице",
            }

        all_items.extend(page)
        if len(page) < page_size:
            break

        page_number += 1

    return {
        "status": 200,
        "items": all_items,
    }


@pytest_asyncio.fixture(name="es_test_films", scope="function")
async def es_test_films(es_write_data, es_film_data):
    """Заполняет Elasticsearch тестовыми фильмами перед запуском.

    Создаёт набор из 5000 документов и загружает его в тестовый индекс.
    """
    bulk_query = es_film_data(count=5000, query_prefix="Test movie")
    await es_write_data(
        bulk_query,
        index=test_settings.es_film_index,
        mapping=ES_FILM_MAPPING
    )


@pytest_asyncio.fixture(name="es_genre_data", scope="session")
def es_genre_data():
    """Возвращает фабрику данных жанров для тестов.

    Используется для генерации постоянных наборов жанров с нужным
    префиксом запроса.
    """

    def generate_genre_data(
            count: int = 5000, query_prefix: str = "Genre"
    ) -> list[dict]:
        """Генерирует список bulk-документов для заданного запроса.

        Возвращает данные, готовые для записи в Elasticsearch.
        """
        return build_genre_bulk_data(count, query_prefix)

    return generate_genre_data


@pytest_asyncio.fixture(name="es_test_genres", scope="function")
async def es_test_genres(es_write_data, es_genre_data):
    """Заполняет Elasticsearch тестовыми жанрами перед запуском.

    Создаёт набор из 5000 документов и загружает его в тестовый индекс.
    """
    bulk_query = es_genre_data(count=5000, query_prefix="Genre")
    await es_write_data(
        bulk_query,
        index=test_settings.es_genre_index,
        mapping=ES_GENRE_MAPPING
    )


@pytest_asyncio.fixture(name="es_person_data", scope="session")
def es_person_data():
    """Возвращает фабрику данных персон для тестов.

    Используется для генерации постоянных наборов персон с нужным
    префиксом запроса.
    """

    def generate_person_data(
            count: int = 5000, query_prefix: str = "Test person"
    ) -> list[dict]:
        """Генерирует список bulk-документов для заданного запроса.

        Возвращает данные, готовые для записи в Elasticsearch.
        """
        return build_person_bulk_data(count, query_prefix)

    return generate_person_data


@pytest_asyncio.fixture(name="es_test_persons", scope="function")
async def es_test_persons(es_write_data, es_person_data):
    """Заполняет Elasticsearch тестовыми персонами перед запуском.

    Создаёт набор из 5000 документов и загружает его в тестовый индекс.
    """
    bulk_query = es_person_data(count=5000, query_prefix="Test person")
    await es_write_data(
        bulk_query,
        index=test_settings.es_person_index,
        mapping=ES_PERSON_MAPPING
    )
