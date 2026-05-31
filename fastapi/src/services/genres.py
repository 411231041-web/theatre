from uuid import UUID

from elasticsearch import AsyncElasticsearch
from redis.asyncio import Redis

from core.config import get_settings
from models.genre_api import GenreDetail, GenreShort
from services.base import BaseService
from services.cache import RedisCacheBackend
from services.mappers import GenreMapper
from services.repositories import ElasticsearchRepository


class GenreService(BaseService[GenreDetail, GenreShort]):
    """Сервис для работы с жанрами."""

    @staticmethod
    def _map_to_short(source: dict) -> GenreShort:
        """Преобразовать ES-данные в GenreShort."""
        return GenreMapper.to_short(source)

    @staticmethod
    def _map_to_detail(source: dict) -> GenreDetail:
        """Преобразовать ES-данные в GenreDetail."""
        return GenreMapper.to_detail(source)

    async def get_by_id(self, genre_id: UUID) -> GenreDetail | None:
        """
        Получить жанр по идентификатору с кэшированием.

        Args:
            genre_id: Уникальный идентификатор жанра (UUID).

        Returns:
            GenreDetail | None: Детальная информация о жанре или None.
        """
        cache_key = self._build_cache_key(
            "genres:get_by_id",
            genre_id=str(genre_id),
        )
        cached_genre = await self._get_from_cache_model(
            cache_key,
            GenreDetail,
        )
        if cached_genre is not None:
            return cached_genre

        source = await self.repository.get_by_id(genre_id)
        if source is None:
            return None

        genre = self._map_to_detail(source)
        await self._set_cache_model(cache_key, genre)
        return genre

    async def list_genres(
        self,
        *,
        sort: str,
        name: str | None,
        page_size: int = 50,
        page_number: int = 1,
    ) -> dict[str, list[GenreShort] | int]:
        """
        Получить список жанров с пагинацией и фильтрацией по названию.

        Args:
            sort: Поле для сортировки (например, "-name").
            name: Название жанра для поиска.
            page_size: Количество записей на страницу.
            page_number: Номер страницы.

        Returns:
            dict[str, list[GenreShort] | int]: Список жанров и total_hits.
        """
        cache_key = self._build_cache_key(
            "genres:list",
            sort=sort,
            name=name,
            page_size=page_size,
            page_number=page_number,
        )
        cached_payload = await self._get_from_cache_json(cache_key)
        if isinstance(cached_payload, dict):
            cached_genres = cached_payload.get("genres")
            cached_total_hits = cached_payload.get("total_hits")
            if (
                isinstance(cached_genres, list)
                and isinstance(cached_total_hits, int)
            ):
                genres = [
                    GenreShort.model_validate(item)
                    for item in cached_genres
                ]
                return {"genres": genres, "total_hits": cached_total_hits}

        sort_order = "desc" if sort.startswith("-") else "asc"
        sort_field = sort.lstrip("-")

        query_body = {"match_all": {}}
        if name:
            query_body = {"match": {"name": {"query": name}}}

        offset = (page_number - 1) * page_size
        sources, total = await self.repository.search(
            query_body=query_body,
            sort_field=f"{sort_field}.raw",
            sort_order=sort_order,
            offset=offset,
            limit=page_size,
        )

        genres = [self._map_to_short(source) for source in sources]
        await self._set_cache_json(
            cache_key,
            {
                "genres": [g.model_dump(mode="json") for g in genres],
                "total_hits": total,
            },
        )
        return {"genres": genres, "total_hits": total}


def get_genre_service(
    elastic: AsyncElasticsearch,
    redis: Redis,
) -> GenreService:
    """
    Создать и вернуть экземпляр GenreService с зависимостями.

    Args:
        elastic: Клиент Elasticsearch для доступа к жанрам.
        redis: Клиент Redis для кэширования результатов.

    Returns:
        GenreService: Инициализированный сервис с репозиторием и кэшем.
    """
    settings = get_settings()
    repository = ElasticsearchRepository(
        elastic=elastic,
        index_name=settings.elasticsearch_genres_index,
        source_fields=["id", "name", "description"],
    )
    cache_backend = RedisCacheBackend(redis)
    return GenreService(
        repository=repository,
        cache=cache_backend,
        settings=settings,
    )
