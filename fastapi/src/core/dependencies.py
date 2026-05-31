"""
Управление зависимостями приложения (IoC контейнер).

Централизованное место для создания и инъекции сервисов, клиентов БД и
других зависимостей. Обеспечивает переиспользование в роутерах, тестах и
фоновых задачах.
"""

from elasticsearch import AsyncElasticsearch
from redis.asyncio import Redis
from db.elasticsearch import get_elastic_client
from db.redis import get_redis_client
from services.films import FilmService, get_film_service
from services.genres import GenreService, get_genre_service
from services.persons import PersonService, get_person_service


def create_film_service(
    elastic: AsyncElasticsearch,
    redis: Redis,
) -> FilmService:
    """
    Создать сервис фильмов с инициализацией всех зависимостей.

    Args:
        elastic: Клиент Elasticsearch для доступа к данным фильмов.
        redis: Клиент Redis для кэширования результатов.

    Returns:
        FilmService: Инициализированный сервис с репозиторием и кэшем.
    """
    return get_film_service(elastic, redis)


def create_genre_service(
    elastic: AsyncElasticsearch,
    redis: Redis,
) -> GenreService:
    """
    Создать сервис жанров с инициализацией всех зависимостей.

    Args:
        elastic: Клиент Elasticsearch для доступа к данным жанров.
        redis: Клиент Redis для кэширования результатов.

    Returns:
        GenreService: Инициализированный сервис с репозиторием и кэшем.
    """
    return get_genre_service(elastic, redis)


def create_person_service(
    elastic: AsyncElasticsearch,
    redis: Redis,
) -> PersonService:
    """
    Создать сервис персон с инициализацией всех зависимостей.

    Args:
        elastic: Клиент Elasticsearch для доступа к данным персон.
        redis: Клиент Redis для кэширования результатов.

    Returns:
        PersonService: Инициализированный сервис с репозиторием и кэшем.
    """
    return get_person_service(elastic, redis)


# Dependency injection functions for FastAPI routers
# These are used with Depends() in route handlers


def get_films_dependency() -> FilmService:
    """
    Фабрика зависимостей для инъекции сервиса фильмов в роутеры.

    Используется как: `Depends(get_films_dependency)` в обработчиках маршрутов.

    Returns:
        FilmService: Инициализированный сервис фильмов.
    """
    return create_film_service(get_elastic_client(), get_redis_client())


def get_genres_dependency() -> GenreService:
    """
    Фабрика зависимостей для инъекции сервиса жанров в роутеры.

    Используется как: `Depends(get_genres_dependency)` в обработчиках
    маршрутов.

    Returns:
        GenreService: Инициализированный сервис жанров.
    """
    return create_genre_service(get_elastic_client(), get_redis_client())


def get_persons_dependency() -> PersonService:
    """
    Фабрика зависимостей для инъекции сервиса персон в роутеры.

    Используется как: `Depends(get_persons_dependency)` в обработчиках
    маршрутов.

    Returns:
        PersonService: Инициализированный сервис персон.
    """
    return create_person_service(get_elastic_client(), get_redis_client())
