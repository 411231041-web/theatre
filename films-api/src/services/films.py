from uuid import UUID

from elasticsearch import AsyncElasticsearch
from redis.asyncio import Redis

from core.config import get_settings
from models.film_api import FilmDetail, FilmShort
from services.base import BaseService
from services.cache import RedisCacheBackend
from services.mappers import FilmMapper
from services.repositories import ElasticsearchRepository


class FilmService(BaseService[FilmDetail, FilmShort]):
    """Сервис для работы с фильмами."""

    @staticmethod
    def _map_to_short(source: dict) -> FilmShort:
        """Преобразовать ES-данные в FilmShort."""
        return FilmMapper.to_short(source)

    @staticmethod
    def _map_to_detail(source: dict) -> FilmDetail:
        """Преобразовать ES-данные в FilmDetail."""
        return FilmMapper.to_detail(source)

    async def get_by_id(self, film_id: UUID) -> FilmDetail | None:
        """
        Получить фильм по идентификатору с кэшированием.

        Args:
            film_id: Уникальный идентификатор фильма (UUID).

        Returns:
            FilmDetail | None: Детальная информация о фильме или None.
        """
        cache_key = self._build_cache_key(
            "films:get_by_id",
            film_id=str(film_id),
        )
        cached_film = await self._get_from_cache_model(
            cache_key,
            FilmDetail,
        )
        if cached_film is not None:
            return cached_film

        source = await self.repository.get_by_id(film_id)
        if source is None:
            return None

        film = self._map_to_detail(source)
        await self._set_cache_model(cache_key, film)
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
            sort: Поле для сортировки (например, "-imdb_rating").
            genre: Идентификатор жанра для фильтрации.
            title: Название фильма для поиска.

        Returns:
            dict[str, list[FilmShort] | int]: Список фильмов и total_hits.
        """
        cache_key = self._build_cache_key(
            "films:list",
            page_size=page_size,
            page_number=page_number,
            sort=sort,
            genre=genre,
            title=title,
        )
        cached_payload = await self._get_from_cache_json(cache_key)
        if isinstance(cached_payload, dict):
            cached_films = cached_payload.get("films")
            cached_total_hits = cached_payload.get("total_hits")
            if (
                isinstance(cached_films, list)
                and isinstance(cached_total_hits, int)
            ):
                films = [
                    FilmShort.model_validate(item)
                    for item in cached_films
                ]
                return {"films": films, "total_hits": cached_total_hits}

        sort_order = "desc" if sort.startswith("-") else "asc"
        sort_field = sort.lstrip("-")

        query_body = self._build_filter_query(title=title, genre=genre)

        offset = (page_number - 1) * page_size
        sources, total = await self.repository.search(
            query_body=query_body,
            sort_field=sort_field,
            sort_order=sort_order,
            offset=offset,
            limit=page_size,
        )

        films = [self._map_to_short(source) for source in sources]
        await self._set_cache_json(
            cache_key,
            {
                "films": [film.model_dump(mode="json") for film in films],
                "total_hits": total,
            },
        )
        return {"films": films, "total_hits": total}

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
            query: Текстовый запрос для поиска.
            page_size: Количество записей на страницу.
            page_number: Номер страницы.
            sort: Поле для сортировки (например, "-imdb_rating").

        Returns:
            dict[str, list[FilmShort] | int]: Список фильмов и total_hits.
        """
        cache_key = self._build_cache_key(
            "films:search",
            query=query,
            page_size=page_size,
            page_number=page_number,
            sort=sort,
        )
        cached_payload = await self._get_from_cache_json(cache_key)
        if isinstance(cached_payload, dict):
            cached_films = cached_payload.get("films")
            cached_total_hits = cached_payload.get("total_hits")
            if (
                isinstance(cached_films, list)
                and isinstance(cached_total_hits, int)
            ):
                films = [
                    FilmShort.model_validate(item)
                    for item in cached_films
                ]
                return {"films": films, "total_hits": cached_total_hits}

        sort_order = "desc" if sort.startswith("-") else "asc"
        sort_field = sort.lstrip("-")

        query_body = {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "description"],
                "type": "best_fields",
            }
        }

        offset = (page_number - 1) * page_size
        sources, total = await self.repository.search(
            query_body=query_body,
            sort_field=sort_field,
            sort_order=sort_order,
            offset=offset,
            limit=page_size,
        )

        films = [self._map_to_short(source) for source in sources]
        await self._set_cache_json(
            cache_key,
            {
                "films": [film.model_dump(mode="json") for film in films],
                "total_hits": total,
            },
        )
        return {"films": films, "total_hits": total}

    @staticmethod
    def _build_filter_query(
        title: str | None = None,
        genre: str | None = None,
    ) -> dict:
        """Построить ES-запрос с фильтрацией."""
        if title and genre:
            return {
                "bool": {
                    "must": [
                        {"term": {"genre": str(genre)}},
                        {"match_phrase": {"title": title}},
                    ]
                }
            }
        elif title:
            return {"match_phrase": {"title": title}}
        elif genre:
            return {"term": {"genre": str(genre)}}
        return {"match_all": {}}


def get_film_service(
    elastic: AsyncElasticsearch,
    redis: Redis,
) -> FilmService:
    """
    Создать и вернуть экземпляр FilmService с зависимостями.

    Args:
        elastic: Клиент Elasticsearch для доступа к фильмам.
        redis: Клиент Redis для кэширования результатов.

    Returns:
        FilmService: Инициализированный сервис с репозиторием и кэшем.
    """
    settings = get_settings()
    repository = ElasticsearchRepository(
        elastic=elastic,
        index_name=settings.elasticsearch_films_index,
        source_fields=[
            "id",
            "title",
            "imdb_rating",
            "description",
            "genre",
            "actors",
            "writers",
            "directors",
        ],
    )
    cache_backend = RedisCacheBackend(redis)
    return FilmService(
        repository=repository,
        cache=cache_backend,
        settings=settings,
    )
