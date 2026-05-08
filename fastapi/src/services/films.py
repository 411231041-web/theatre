from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from redis.asyncio import Redis

from src.core.config import Settings, get_settings
from src.models.film_api import (
    FilmDetail,
    FilmShort,
    GenreInFilm,
    PersonInFilm,
)
from src.services.cache import (
    build_cache_key,
    get_cached_model,
    get_cached_models,
    set_cached_model,
    set_cached_models,
)


class FilmService:
    """
    Сервис для работы с фильмами.

    Обеспечивает взаимодействие с Elasticsearch для получения данных о фильмах
    и Redis для кэширования результатов.

    Attributes:
        elastic: Клиент для взаимодействия с Elasticsearch.
        redis: Клиент для взаимодействия с Redis.
        settings: Конфигурация приложения.
    """

    def __init__(
        self,
        elastic: AsyncElasticsearch,
        redis: Redis,
        settings: Settings,
    ) -> None:
        """
        Инициализация сервиса фильмов.

        Args:
            elastic: Клиент Elasticsearch.
            redis: Клиент Redis.
            settings: Конфигурация приложения.
        """
        self.elastic = elastic
        self.redis = redis
        self.settings = settings

    async def get_by_id(self, film_id: UUID) -> FilmDetail | None:
        """
        Получить фильм по идентификатору с кэшированием.

        Сначала проверяет кэш в Redis, при отсутствии данных обращается
        к Elasticsearch и сохраняет результат в кэш.

        Args:
            film_id: Уникальный идентификатор фильма (UUID).

        Returns:
            FilmDetail | None: Детальная информация о фильме или None, если не найден.
        """
        cache_key = build_cache_key("films:get_by_id", film_id=str(film_id))
        cached_film = await get_cached_model(self.redis, cache_key, FilmDetail)
        if cached_film is not None:
            return cached_film

        try:
            response = await self.elastic.get(
                index=self.settings.elasticsearch_index,
                id=str(film_id),
            )
        except NotFoundError:
            return None

        source = response.get("_source") or {}
        film = self._map_film_detail(source)
        await set_cached_model(
            self.redis,
            cache_key,
            film,
            self.settings.redis_cache_expire,
        )
        return film

    async def list_films(
        self,
        *,
        page_size: int,
        page_number: int,
        sort: str,
        genre: str | None,
    ) -> list[FilmShort]:
        """
        Получить список фильмов с пагинацией, сортировкой и фильтрацией по жанру.

        Args:
            page_size: Количество записей на страницу.
            page_number: Номер страницы.
            sort: Поле для сортировки (например, "-imdb_rating" для убывающего порядка).
            genre: Идентификатор жанра для фильтрации.

        Returns:
            list[FilmShort]: Список кратких данных о фильмах.
        """
        cache_key = build_cache_key(
            "films:list",
            page_size=page_size,
            page_number=page_number,
            sort=sort,
            genre=genre,
        )
        cached_films = await get_cached_models(
            self.redis,
            cache_key,
            FilmShort,
        )
        if cached_films is not None:
            return cached_films

        sort_order = "desc" if sort.startswith("-") else "asc"
        sort_field = sort.lstrip("-")

        query: dict = {"match_all": {}}
        if genre is not None:
            query = {"term": {"genres": str(genre)}}

        response = await self.elastic.search(
            index=self.settings.elasticsearch_index,
            body={
                "query": query,
                "sort": [{sort_field: {"order": sort_order}}],
                "from": (page_number - 1) * page_size,
                "size": page_size,
                "_source": ["id", "title", "imdb_rating"],
            },
        )

        hits = response.get("hits", {}).get("hits", [])
        films = [
            self._map_film_short(hit.get("_source") or {})
            for hit in hits
        ]
        await set_cached_models(
            self.redis,
            cache_key,
            films,
            self.settings.redis_cache_expire,
        )
        return films

    @staticmethod
    def _map_film_short(source: dict) -> FilmShort:
        """
        Преобразовать исходные данные Elasticsearch в объект FilmShort.

        Args:
            source: Словарь с данными из Elasticsearch.

        Returns:
            FilmShort: Объект краткой информации о фильме.
        """
        return FilmShort(
            uuid=source["id"],
            title=source.get("title", ""),
            imdb_rating=source.get("imdb_rating"),
        )

    @staticmethod
    def _map_people(items: list[dict]) -> list[PersonInFilm]:
        """
        Преобразовать список людей из Elasticsearch в объекты PersonInFilm.

        Args:
            items: Список словарей с данными о людях.

        Returns:
            list[PersonInFilm]: Список объектов участников фильма.
        """
        return [
            PersonInFilm(uuid=item["id"], full_name=item["name"])
            for item in items
            if item.get("id") and item.get("name")
        ]

    def _map_film_detail(self, source: dict) -> FilmDetail:
        """
        Преобразовать исходные данные Elasticsearch в объект FilmDetail.

        Args:
            source: Словарь с данными из Elasticsearch.

        Returns:
            FilmDetail: Объект детальной информации о фильме.
        """
        genres = [
            GenreInFilm(name=genre_name)
            for genre_name in source.get("genres", [])
            if genre_name
        ]

        return FilmDetail(
            uuid=source["id"],
            title=source.get("title", ""),
            imdb_rating=source.get("imdb_rating"),
            description=source.get("description"),
            genre=genres,
            actors=self._map_people(source.get("actors", [])),
            writers=self._map_people(source.get("writers", [])),
            directors=self._map_people(source.get("directors", [])),
        )


def get_film_service(
    elastic: AsyncElasticsearch,
    redis: Redis,
) -> FilmService:
    """
    Создать и вернуть экземпляр FilmService с зависимостями.

    Args:
        elastic: Клиент Elasticsearch.
        redis: Клиент Redis.

    Returns:
        FilmService: Экземпляр сервиса для работы с фильмами.
    """
    return FilmService(
        elastic=elastic,
        redis=redis,
        settings=get_settings(),
    )
