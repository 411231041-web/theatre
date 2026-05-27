from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from redis.asyncio import Redis

from core.config import Settings, get_settings
from models.film_api import (
    FilmDetail,
    FilmShort,
    GenreInFilm,
    PersonInFilm,
)
from services.cache import (
    build_cache_key,
    get_cached_json,
    get_cached_model,
    set_cached_json,
    set_cached_model,
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
            FilmDetail | None: Детальная информация о фильме или None,
                если не найден.
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
        title: str | None = None,
    ) -> dict[str, list[FilmShort] | int]:
        """
        Получить список фильмов с пагинацией и фильтрацией по жанру.

        Args:
            page_size: Количество записей на страницу.
            page_number: Номер страницы.
            sort: Поле для сортировки (например, "-imdb_rating" для
                убывающего порядка).
            genre: Идентификатор жанра для фильтрации.

        Returns:
            dict[str, list[FilmShort] | int]: Словарь с списком кратких
                данных о фильмах и общим количеством результатов.
        """
        cache_key = build_cache_key(
            "films:list",
            page_size=page_size,
            page_number=page_number,
            sort=sort,
            genre=genre,
            title=title,
        )
        cached_payload = await get_cached_json(self.redis, cache_key)
        if isinstance(cached_payload, dict):
            cached_films = cached_payload.get("films")
            cached_total_hits = cached_payload.get("total_hits")
            if (
                isinstance(cached_films, list)
                and isinstance(cached_total_hits, int)
            ):
                films = [FilmShort.model_validate(item)
                         for item in cached_films]
                return {"films": films, "total_hits": cached_total_hits}

        sort_order = "desc" if sort.startswith("-") else "asc"
        sort_field = sort.lstrip("-")

        if title is not None and genre is not None:
            query_body = {
                "bool": {
                    "must": [
                        {"term": {"genre": str(genre)}},
                        {
                            "match_phrase": {
                                "title": title,
                            }
                        },
                    ]
                }
            }
        elif title is not None:
            query_body = {
                "match_phrase": {
                    "title": title,
                }
            }
        elif genre is not None:
            query_body = {"term": {"genre": str(genre)}}
        else:
            query_body = {"match_all": {}}

        response = await self.elastic.search(
            index=self.settings.elasticsearch_index,
            body={
                "query": query_body,
                "sort": [{sort_field: {"order": sort_order}}],
                "from": (page_number - 1) * page_size,
                "size": page_size,
                "_source": [
                    "id",
                    "title",
                    "imdb_rating",
                    "description",
                    "genre",
                ],
                "track_total_hits": True,
            },
        )

        total_hits = response.get("hits", {}).get("total", {}).get("value", 0)

        hits = response.get("hits", {}).get("hits", [])
        films = [
            self._map_film_short(hit.get("_source") or {}) for hit in hits
        ]
        await set_cached_json(
            self.redis,
            cache_key,
            {
                "films": [film.model_dump(mode="json") for film in films],
                "total_hits": total_hits,
            },
            self.settings.redis_cache_expire,
        )
        return {"films": films, "total_hits": total_hits}

    async def search_films(
        self,
        *,
        query: str,
        page_size: int,
        page_number: int,
        sort: str,
    ) -> dict[str, list[FilmShort] | int]:
        """
        Поиск фильмов по текстовому запросу с пагинацией и сортировкой.

        Args:
            query: Текстовый запрос для поиска (по названию и описанию).
            page_size: Количество записей на страницу.
            page_number: Номер страницы.
            sort: Поле для сортировки (например, "-imdb_rating" для убывающего
                  порядка).

        Returns:
            dict[str, list[FilmShort] | int]: Словарь с списком кратких
                данных о найденных фильмах и общим количеством результатов.
        """
        cache_key = build_cache_key(
            "films:search",
            query=query,
            page_size=page_size,
            page_number=page_number,
            sort=sort,
        )
        cached_payload = await get_cached_json(self.redis, cache_key)
        if isinstance(cached_payload, dict):
            cached_films = cached_payload.get("films")
            cached_total_hits = cached_payload.get("total_hits")
            if (
                isinstance(cached_films, list)
                and isinstance(cached_total_hits, int)
            ):
                films = [FilmShort.model_validate(item)
                         for item in cached_films]
                return {"films": films, "total_hits": cached_total_hits}

        sort_order = "desc" if sort.startswith("-") else "asc"
        sort_field = sort.lstrip("-")

        response = await self.elastic.search(
            index=self.settings.elasticsearch_index,
            body={
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^3", "description"],
                        "type": "best_fields",
                    }
                },
                "sort": [{sort_field: {"order": sort_order}}],
                "from": (page_number - 1) * page_size,
                "size": page_size,
                "_source": [
                    "id",
                    "title",
                    "imdb_rating",
                    "description",
                    "genre",
                ],
                "track_total_hits": True,
            },
        )

        total_hits = response.get("hits", {}).get("total", {}).get("value", 0)

        hits = response.get("hits", {}).get("hits", [])
        films = [
            self._map_film_short(hit.get("_source") or {}) for hit in hits
        ]
        await set_cached_json(
            self.redis,
            cache_key,
            {
                "films": [film.model_dump(mode="json") for film in films],
                "total_hits": total_hits,
            },
            self.settings.redis_cache_expire,
        )
        return {"films": films, "total_hits": total_hits}

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
            description=source.get("description"),
            genres=source.get("genre", []),
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
            for genre_name in source.get("genre", [])
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
