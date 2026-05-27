from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from redis.asyncio import Redis

from core.config import Settings, get_settings
from models.genre_api import GenreDetail, GenreShort
from services.cache import (
    build_cache_key,
    get_cached_json,
    get_cached_model,
    set_cached_model,
    set_cached_json,
)


class GenreService:
    """
    Сервис для работы с жанрами.

    Обеспечивает взаимодействие с Elasticsearch для получения данных о жанрах
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
        Инициализация сервиса жанров.

        Args:
            elastic: Клиент Elasticsearch.
            redis: Клиент Redis.
            settings: Конфигурация приложения.
        """
        self.elastic = elastic
        self.redis = redis
        self.settings = settings

    async def get_by_id(self, genre_id: UUID) -> GenreDetail | None:
        """
        Получить жанр по идентификатору с кэшированием.

        Сначала проверяет кэш в Redis, при отсутствии данных обращается
        к Elasticsearch и сохраняет результат в кэш.

        Args:
            genre_id: Уникальный идентификатор жанра (UUID).

        Returns:
            GenreDetail | None: Детальная информация о жанре или None,
                если не найден.
        """
        cache_key = build_cache_key("genres:get_by_id", genre_id=str(genre_id))
        cached_genre = await get_cached_model(
            self.redis,
            cache_key,
            GenreDetail,
        )
        if cached_genre is not None:
            return cached_genre

        try:
            response = await self.elastic.get(
                index=self.settings.elasticsearch_genres_index,
                id=str(genre_id),
            )
        except NotFoundError:
            return None

        source = response.get("_source") or {}
        genre = self._map_genre_detail(source)
        await set_cached_model(
            self.redis,
            cache_key,
            genre,
            self.settings.redis_cache_expire,
        )
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
            sort: Поле для сортировки (например, "-name" для
                убывающего порядка).
            name: Название жанра для поиска (поиск по частичному совпадению).
            page_size: Количество записей на страницу (по умолчанию 50).
            page_number: Номер страницы (по умолчанию 1).

        Returns:
            dict[str, list[GenreShort] | int]:
                Словарь с списком кратких данных о жанрах и
                общим количеством записей.
        """
        cache_key = build_cache_key(
            "genres:list",
            sort=sort,
            name=name,
            page_size=page_size,
            page_number=page_number,
        )
        cached_payload = await get_cached_json(self.redis, cache_key)
        if isinstance(cached_payload, dict):
            cached_genres = cached_payload.get("genres")
            cached_total_hits = cached_payload.get("total_hits")
            if (
                isinstance(cached_genres, list)
                and isinstance(cached_total_hits, int)
            ):
                genres = [GenreShort(**genre) for genre in cached_genres]
                return {"genres": genres, "total_hits": cached_total_hits}

        sort_order = "desc" if sort.startswith("-") else "asc"
        query: dict = {"match_all": {}}
        if name:
            query = {
                "match": {
                    "name": {
                        "query": name,
                    }
                }
            }

        response = await self.elastic.search(
            index=self.settings.elasticsearch_genres_index,
            body={
                "query": query,
                "sort": [{"name.raw": {"order": sort_order}}],
                "from": (page_number - 1) * page_size,
                "size": page_size,
                "_source": ["id", "name"],
                "track_total_hits": True,
            },
        )

        total_hits = response.get("hits", {}).get("total", {}).get("value", 0)

        hits = response.get("hits", {}).get("hits", [])
        genres = [
            self._map_genre_short(hit.get("_source") or {}) for hit in hits
        ]
        # Сохраняем в кеш структуру с данными и общим числом результатов,
        # чтобы при последующих запросах можно было получить списки и
        # общее количество без обращения в Elasticsearch.
        await set_cached_json(
            self.redis,
            cache_key,
            {
                "genres": [g.model_dump(mode="json") for g in genres],
                "total_hits": total_hits,
            },
            self.settings.redis_cache_expire,
        )
        return {"genres": genres, "total_hits": total_hits}

    @staticmethod
    def _map_genre_short(source: dict) -> GenreShort:
        """
        Преобразовать исходные данные Elasticsearch в объект GenreShort.

        Args:
            source: Словарь с данными из Elasticsearch.

        Returns:
            GenreShort: Объект краткой информации о жанре.
        """
        return GenreShort(
            uuid=source["id"],
            name=source.get("name", ""),
        )

    @staticmethod
    def _map_genre_detail(source: dict) -> GenreDetail:
        """
        Преобразовать исходные данные Elasticsearch в объект GenreDetail.

        Args:
            source: Словарь с данными из Elasticsearch.

        Returns:
            GenreDetail: Объект детальной информации о жанре.
        """
        return GenreDetail(
            uuid=source["id"],
            name=source.get("name", ""),
            description=source.get("description"),
        )


def get_genre_service(
    elastic: AsyncElasticsearch,
    redis: Redis,
) -> GenreService:
    """
    Создать и вернуть экземпляр GenreService с зависимостями.

    Args:
        elastic: Клиент Elasticsearch.
        redis: Клиент Redis.

    Returns:
        GenreService: Экземпляр сервиса для работы с жанрами.
    """
    return GenreService(
        elastic=elastic,
        redis=redis,
        settings=get_settings(),
    )
