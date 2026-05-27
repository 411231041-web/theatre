from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from redis.asyncio import Redis

from core.config import Settings, get_settings
from models.person_api import PersonDetail, PersonSearchResult
from services.cache import (
    build_cache_key,
    get_cached_json,
    get_cached_model,
    set_cached_json,
    set_cached_model,
)


class PersonService:
    """
    Сервис для работы с персонами.

    Обеспечивает взаимодействие с Elasticsearch для получения данных о персонах
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
        Инициализация сервиса персон.

        Args:
            elastic: Клиент Elasticsearch.
            redis: Клиент Redis.
            settings: Конфигурация приложения.
        """
        self.elastic = elastic
        self.redis = redis
        self.settings = settings

    async def get_by_id(self, person_id: UUID) -> PersonDetail | None:
        """
        Получить персону по идентификатору с кэшированием.

        Сначала проверяет кэш в Redis, при отсутствии данных обращается
        к Elasticsearch и сохраняет результат в кэш.

        Args:
            person_id: Уникальный идентификатор персоны (UUID).

        Returns:
            PersonDetail | None: Детальная информация о персоне или None,
                если не найдена.
        """
        cache_key = build_cache_key(
            "persons:get_by_id",
            person_id=str(person_id),
        )
        cached_person = await get_cached_model(
            self.redis,
            cache_key,
            PersonDetail,
        )
        if cached_person is not None:
            return cached_person

        try:
            response = await self.elastic.get(
                index=self.settings.elasticsearch_persons_index,
                id=str(person_id),
            )
        except NotFoundError:
            return None

        source = response.get("_source") or {}
        person = self._map_person_detail(source)
        await set_cached_model(
            self.redis,
            cache_key,
            person,
            self.settings.redis_cache_expire,
        )
        return person

    async def search_persons(
        self,
        *,
        query: str,
        sort: str,
        role: str | None,
        page_size: int = 50,
        page_number: int = 1,
    ) -> dict[str, list[PersonSearchResult] | int]:
        """
        Выполнить поиск персон по запросу с фильтрацией по роли.

        Args:
            query: Поисковый запрос.
            sort: Поле для сортировки (например, "-full_name" для
                убывающего порядка).
            role: Роль для фильтрации (actor, director, writer).
            page_size: Количество записей на страницу (по умолчанию 50).
            page_number: Номер страницы (по умолчанию 1).

        Returns:
            list[PersonSearchResult]: Список найденных персон с краткой
                информацией о фильмах.
        """
        cache_key = build_cache_key(
            "persons:search",
            query=query,
            sort=sort,
            role=role,
            page_size=page_size,
            page_number=page_number,
        )
        cached_payload = await get_cached_json(self.redis, cache_key)
        if isinstance(cached_payload, dict):
            cached_persons = cached_payload.get("persons")
            cached_total_hits = cached_payload.get("total_hits")
            if (
                isinstance(cached_persons, list)
                and isinstance(cached_total_hits, int)
            ):
                persons = [
                    PersonSearchResult.model_validate(item)
                    for item in cached_persons
                ]
                return {"persons": persons, "total_hits": cached_total_hits}

        sort_order = "desc" if sort.startswith("-") else "asc"
        sort_field = sort.lstrip("-")
        # Use keyword subfield for text fields to avoid fielddata errors
        if sort_field == "full_name":
            sort_field = f"{sort_field}.raw"

        search_query: dict = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["full_name^3", "full_name.raw"],
                            "type": "best_fields",
                        }
                    }
                ]
            }
        }
        if role:
            search_query["bool"]["filter"] = [
                {
                    "nested": {
                        "path": "films",
                        "query": {
                            "term": {"films.roles": role}
                        },
                    }
                }
            ]

        response = await self.elastic.search(
            index=self.settings.elasticsearch_persons_index,
            body={
                "query": search_query,
                "sort": [{sort_field: {"order": sort_order}}],
                "from": (page_number - 1) * page_size,
                "size": page_size,
                "_source": ["id", "full_name", "films"],
                "track_total_hits": True,
            },
        )

        total_hits = response.get("hits", {}).get("total", {}).get("value", 0)

        hits = response.get("hits", {}).get("hits", [])
        persons = [
            self._map_person_search_result(hit.get("_source") or {}, role)
            for hit in hits
        ]
        await set_cached_json(
            self.redis,
            cache_key,
            {
                "persons": [
                    person.model_dump(mode="json")
                    for person in persons
                ],
                "total_hits": total_hits,
            },
            self.settings.redis_cache_expire,
        )
        return {"persons": persons, "total_hits": total_hits}

    async def get_films_by_person(
        self,
        person_id: UUID,
        *,
        page_size: int = 50,
        page_number: int = 1,
    ) -> list[dict]:
        """
        Получить список фильмов по идентификатору персоны с пагинацией.

        Args:
            person_id: Уникальный идентификатор персоны (UUID).
            page_size: Количество записей на страницу (по умолчанию 50).
            page_number: Номер страницы (по умолчанию 1).

        Returns:
            list[dict]: Список фильмов с информацией об участии персоны.
        """
        cache_key = build_cache_key(
            "persons:films",
            person_id=str(person_id),
            page_size=page_size,
            page_number=page_number,
        )
        cached_films = await get_cached_json(self.redis, cache_key)
        if isinstance(cached_films, list):
            return cached_films

        try:
            response = await self.elastic.get(
                index=self.settings.elasticsearch_persons_index,
                id=str(person_id),
            )
        except NotFoundError:
            return []

        source = response.get("_source") or {}
        films = source.get("films", [])

        start = (page_number - 1) * page_size
        end = start + page_size

        paged_films = films[start:end]
        await set_cached_json(
            self.redis,
            cache_key,
            paged_films,
            self.settings.redis_cache_expire,
        )
        return paged_films

    @staticmethod
    def _map_person_detail(source: dict) -> PersonDetail:
        """
        Преобразовать исходные данные Elasticsearch в объект PersonDetail.

        Args:
            source: Словарь с данными из Elasticsearch.

        Returns:
            PersonDetail: Объект детальной информации о персоне с фильмами.
        """
        films = [
            {"uuid": film["id"], "roles": film.get("roles", [])}
            for film in source.get("films", [])
            if film.get("id")
        ]
        return PersonDetail(
            uuid=source["id"],
            full_name=source.get("full_name", ""),
            films=films,
        )

    @staticmethod
    def _map_person_search_result(
        source: dict,
        role: str | None = None,
    ) -> PersonSearchResult:
        """
        Преобразовать исходные данные Elasticsearch в объект
            PersonSearchResult.

        Args:
            source: Словарь с данными из Elasticsearch.

        Returns:
            PersonSearchResult: Объект результата поиска персоны с фильмами.
        """
        films: list[dict] = []
        for film in source.get("films", []):
            if not film.get("id"):
                continue
            film_roles = film.get("roles", [])
            if role is None:
                films.append({"uuid": film["id"], "roles": film_roles})
            else:
                if role in film_roles:
                    films.append({"uuid": film["id"], "roles": [role]})
        return PersonSearchResult(
            uuid=source["id"],
            full_name=source.get("full_name", ""),
            films=films,
        )


def get_person_service(
    elastic: AsyncElasticsearch,
    redis: Redis,
) -> PersonService:
    """
    Создать и вернуть экземпляр PersonService с зависимостями.

    Args:
        elastic: Клиент Elasticsearch.
        redis: Клиент Redis.

    Returns:
        PersonService: Экземпляр сервиса для работы с персонами.
    """
    return PersonService(
        elastic=elastic,
        redis=redis,
        settings=get_settings(),
    )
