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
from utils.test_data_helpers import build_film_bulk_data
from utils.test_data_helpers import build_genre_bulk_data
from utils.test_data_helpers import build_person_bulk_data
from utils.es_helpers import recreate_index


@pytest_asyncio.fixture(name="es_client_factory", scope="session")
def es_client_factory():
    """Фабрика для создания AsyncElasticsearch клиента.

    Возвращает функцию для создания клиента AsyncElasticsearch
    внутри текущего event loop.

    Возвращает
    ---------
    Callable[[], AsyncElasticsearch]
        Функция для создания нового клиента AsyncElasticsearch,
        подключённого к хосту из конфигурации.
    """
    def make_client():
        """Создать клиент AsyncElasticsearch с настройками проекта.

        Возвращает
        ---------
        AsyncElasticsearch
            Клиент Elasticsearch с проверкой сертификатов отключена.
        """
        return AsyncElasticsearch(
            hosts=[test_settings.es_url], verify_certs=False
        )

    return make_client


@pytest_asyncio.fixture(name="es_write_lock", scope="session")
async def es_write_lock():
    """Создаёт блокировку для синхронизации записей в Elasticsearch.

    Фикстура обеспечивает последовательную запись данных из разных
    тестов в одном event loop, предотвращая конфликты доступа.

    Возвращает
    ---------
    asyncio.Lock
        Блокировка, привязанная к текущему event loop.
    """
    return asyncio.Lock()


@pytest_asyncio.fixture(name="es_write_data", scope="session")
def es_write_data(es_client_factory, es_write_lock):
    """Возвращает функцию записи данных в Elasticsearch.

    Фикстура возвращает async-функцию, принимающую bulk-данные, имя
    индекса и опциональный маппинг. Все записи синхронизируются через
    asyncio.Lock, чтобы избежать конфликтов при параллельном запуске
    тестов.

    Возвращает
    ---------
    Callable[[list[dict], str, dict | None], Coroutine[None, None, None]]
        Асинхронную функцию для записи bulk-данных в Elasticsearch.
    """

    async def inner(data: list[dict], index: str = "",
                    mapping: dict = None) -> None:
        """Записать bulk-данные в индекс Elasticsearch.

        Синхронизирует доступ через `es_write_lock`, создаёт индекс
        при необходимости, загружает документы, обновляет индекс.

        Параметры
        ---------
        data: list[dict]
            Список bulk-документов Elasticsearch.
        index: str
            Имя индекса для записи данных.
        mapping: dict | None
            Опциональный маппинг для создания индекса.

        Возвращает
        ---------
        None

        Вызывает исключения
        ------------------
        RuntimeError
            Если при загрузке документов в Elasticsearch
            возникли ошибки.
        """
        async with es_write_lock:
            client = es_client_factory()
            try:
                exists = await client.indices.exists(index=index)
                if not exists:
                    if mapping is not None:
                        await client.indices.create(
                            index=index, mappings=mapping
                        )
                    else:
                        await client.indices.create(index=index)

                _, errors = await async_bulk(client=client, actions=data)
                if errors:
                    raise RuntimeError(
                        "Ошибка записи данных в Elasticsearch"
                    )

                await client.indices.refresh(index=index)
            finally:
                await client.close()

    return inner


@pytest_asyncio.fixture(name="es_film_data", scope="session")
def es_film_data():
    """Возвращает фабрику для генерации данных фильмов.

    Фикстура предоставляет функцию для создания bulk-документов
    фильмов с произвольным количеством и префиксом названия.

    Возвращает
    ---------
    Callable[[int, str], list[dict]]
        Функция для генерации bulk-документов фильмов.
    """

    def generate_film_data(
            count: int = 5000,
            query_prefix: str = "Test movie"
    ) -> list[dict]:
        """Генерирует bulk-документы фильмов для Elasticsearch.

        Создаёт список документов с поддельными данными фильмов,
        готовых для загрузки в Elasticsearch.

        Параметры
        ---------
        count: int
            Количество генерируемых фильмов (по умолчанию 5000).
        query_prefix: str
            Префикс для названия фильмов (по умолчанию
            "Test movie").

        Возвращает
        ---------
        list[dict]
            Список bulk-документов Elasticsearch для фильмов.
        """
        return build_film_bulk_data(count, query_prefix)

    return generate_film_data


@pytest_asyncio.fixture(name="redis_client", scope="function")
async def redis_client():
    """Создаёт асинхронный Redis-клиент для теста.

    Фикстура инициализирует клиент, очищает базу данных перед
    тестом и автоматически закрывает соединение после завершения
    теста.

    Возвращает
    ---------
    redis.asyncio.Redis
        Асинхронный клиент Redis, подключённый к хосту из
        конфигурации.

    Вызывает исключения
    ------------------
    Exception
        Если соединение с Redis не удалось установить.
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
    """Создаёт асинхронную сессию HTTP для тестов API.

    Фикстура предоставляет aiohttp.ClientSession для выполнения
    HTTP-запросов к API-сервису. Автоматически закрывает сессию
    после завершения теста.

    Возвращает
    ---------
    aiohttp.ClientSession
        Готовая сессия для HTTP-запросов.

    Примечание
    ----------
    URL эндпоинта указывается в параметрах запросов внутри
    тестов.
    """
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest_asyncio.fixture(name="es_test_films", scope="function")
async def es_test_films(
    es_write_data, es_film_data, es_client_factory
):
    """Подготавливает Elasticsearch с тестовыми фильмами.

    Фикстура создаёт и пересоздаёт индекс фильмов, загружает
    набор из 5000 тестовых документов фильмов.

    Параметры
    ---------
    es_write_data: Callable
        Фикстура для записи данных в Elasticsearch.
    es_film_data: Callable
        Фикстура для генерации данных фильмов.
    es_client_factory: Callable
        Фабрика для создания клиента Elasticsearch.

    Возвращает
    ---------
    None
    """
    bulk_query = es_film_data(
        count=5000, query_prefix="Test movie"
    )
    # Пересоздаём индекс для чистого набора данных.
    tmp = es_client_factory()
    try:
        await recreate_index(tmp, test_settings.es_film_index,
                             ES_FILM_MAPPING)
    finally:
        await tmp.close()
    await es_write_data(
        bulk_query,
        index=test_settings.es_film_index,
        mapping=ES_FILM_MAPPING,
    )


@pytest_asyncio.fixture(name="es_genre_data", scope="session")
def es_genre_data():
    """Возвращает фабрику для генерации данных жанров.

    Фикстура предоставляет функцию для создания bulk-документов
    жанров с произвольным количеством и префиксом названия.

    Возвращает
    ---------
    Callable[[int, str], list[dict]]
        Функция для генерации bulk-документов жанров.
    """

    def generate_genre_data(
            count: int = 5000,
            query_prefix: str = "Genre"
    ) -> list[dict]:
        """Генерирует bulk-документы жанров для Elasticsearch.

        Создаёт список документов с поддельными данными жанров,
        готовых для загрузки в Elasticsearch.

        Параметры
        ---------
        count: int
            Количество генерируемых жанров (по умолчанию 5000).
        query_prefix: str
            Префикс для названия жанра (по умолчанию "Genre").

        Возвращает
        ---------
        list[dict]
            Список bulk-документов Elasticsearch для жанров.
        """
        return build_genre_bulk_data(count, query_prefix)

    return generate_genre_data


@pytest_asyncio.fixture(name="es_test_genres", scope="function")
async def es_test_genres(
    es_write_data, es_genre_data, es_client_factory
):
    """Подготавливает Elasticsearch с тестовыми жанрами.

    Фикстура создаёт и пересоздаёт индекс жанров, загружает набор
    из 5000 тестовых документов жанров.

    Параметры
    ---------
    es_write_data: Callable
        Фикстура для записи данных в Elasticsearch.
    es_genre_data: Callable
        Фикстура для генерации данных жанров.
    es_client_factory: Callable
        Фабрика для создания клиента Elasticsearch.

    Возвращает
    ---------
    None
    """
    bulk_query = es_genre_data(
        count=5000, query_prefix="Genre"
    )
    tmp = es_client_factory()
    try:
        await recreate_index(tmp, test_settings.es_genre_index,
                             ES_GENRE_MAPPING)
    finally:
        await tmp.close()
    await es_write_data(
        bulk_query,
        index=test_settings.es_genre_index,
        mapping=ES_GENRE_MAPPING,
    )


@pytest_asyncio.fixture(name="es_person_data", scope="session")
def es_person_data():
    """Возвращает фабрику для генерации данных персон.

    Фикстура предоставляет функцию для создания bulk-документов
    персон с произвольным количеством и префиксом названия.

    Возвращает
    ---------
    Callable[[int, str], list[dict]]
        Функция для генерации bulk-документов персон.
    """

    def generate_person_data(
            count: int = 5000,
            query_prefix: str = "Test person"
    ) -> list[dict]:
        """Генерирует bulk-документы персон для Elasticsearch.

        Создаёт список документов с поддельными данными персон,
        готовых для загрузки в Elasticsearch.

        Параметры
        ---------
        count: int
            Количество генерируемых персон (по умолчанию 5000).
        query_prefix: str
            Префикс для названия персоны (по умолчанию
            "Test person").

        Возвращает
        ---------
        list[dict]
            Список bulk-документов Elasticsearch для персон.
        """
        return build_person_bulk_data(count, query_prefix)

    return generate_person_data


@pytest_asyncio.fixture(name="es_test_persons", scope="function")
async def es_test_persons(
    es_write_data, es_person_data, es_client_factory
):
    """Подготавливает Elasticsearch с тестовыми персонами.

    Фикстура создаёт и пересоздаёт индекс персон, загружает набор
    из 5000 тестовых документов персон.

    Параметры
    ---------
    es_write_data: Callable
        Фикстура для записи данных в Elasticsearch.
    es_person_data: Callable
        Фикстура для генерации данных персон.
    es_client_factory: Callable
        Фабрика для создания клиента Elasticsearch.

    Возвращает
    ---------
    None
    """
    bulk_query = es_person_data(
        count=5000, query_prefix="Test person"
    )
    tmp = es_client_factory()
    try:
        await recreate_index(tmp, test_settings.es_person_index,
                             ES_PERSON_MAPPING)
    finally:
        await tmp.close()
    await es_write_data(
        bulk_query,
        index=test_settings.es_person_index,
        mapping=ES_PERSON_MAPPING,
    )
