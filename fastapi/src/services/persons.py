from uuid import UUID

from elasticsearch import AsyncElasticsearch
from redis.asyncio import Redis

from core.config import get_settings
from models.person_api import (
    FilmInPerson,
    PersonDetail,
    PersonSearchResult,
)
from services.base import BaseService
from services.cache import RedisCacheBackend
from services.mappers import PersonMapper
from services.repositories import ElasticsearchRepository


class PersonService(BaseService[PersonDetail, PersonSearchResult]):
    """Сервис для работы с персонами."""

    @staticmethod
    def _map_to_short(source: dict) -> PersonSearchResult:
        """Преобразовать ES-данные в PersonSearchResult."""
        return PersonMapper.to_short(source)

    @staticmethod
    def _map_to_detail(source: dict) -> PersonDetail:
        """Преобразовать ES-данные в PersonDetail."""
        return PersonMapper.to_detail(source)

    async def get_by_id(self, person_id: UUID) -> PersonDetail | None:
        """
        Получить персону по идентификатору с кэшированием.

        Args:
            person_id: Уникальный идентификатор персоны (UUID).

        Returns:
            PersonDetail | None: Детальная информация о персоне или None.
        """
        cache_key = self._build_cache_key(
            "persons:get_by_id",
            person_id=str(person_id),
        )
        cached_person = await self._get_from_cache_model(
            cache_key,
            PersonDetail,
        )
        if cached_person is not None:
            return cached_person

        source = await self.repository.get_by_id(person_id)
        if source is None:
            return None

        person = self._map_to_detail(source)
        await self._set_cache_model(cache_key, person)
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
            sort: Поле для сортировки (например, "-full_name").
            role: Роль для фильтрации (actor, director, writer).
            page_size: Количество записей на страницу.
            page_number: Номер страницы.

        Returns:
            dict[str, list[PersonSearchResult] | int]: Список персон и
            total_hits.
        """
        cache_key = self._build_cache_key(
            "persons:search",
            query=query,
            sort=sort,
            role=role,
            page_size=page_size,
            page_number=page_number,
        )
        cached_payload = await self._get_from_cache_json(cache_key)
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
        if sort_field == "full_name":
            sort_field = f"{sort_field}.raw"

        query_body = self._build_search_query(query=query, role=role)

        offset = (page_number - 1) * page_size
        sources, total = await self.repository.search(
            query_body=query_body,
            sort_field=sort_field,
            sort_order=sort_order,
            offset=offset,
            limit=page_size,
        )

        persons = [
            PersonMapper.to_search_result(source, role=role)
            for source in sources
        ]
        await self._set_cache_json(
            cache_key,
            {
                "persons": [
                    person.model_dump(mode="json")
                    for person in persons
                ],
                "total_hits": total,
            },
        )
        return {"persons": persons, "total_hits": total}

    async def get_films_by_person(
        self,
        person_id: UUID,
        *,
        page_size: int = 50,
        page_number: int = 1,
    ) -> list[FilmInPerson]:
        """
        Получить список фильмов по идентификатору персоны с пагинацией.

        Args:
            person_id: Уникальный идентификатор персоны (UUID).
            page_size: Количество записей на страницу.
            page_number: Номер страницы.

        Returns:
            list[FilmInPerson]: Список фильмов с информацией о ролях.
        """
        cache_key = self._build_cache_key(
            "persons:films",
            person_id=str(person_id),
            page_size=page_size,
            page_number=page_number,
        )
        cached_films = await self._get_from_cache_json(cache_key)
        if isinstance(cached_films, list):
            return [FilmInPerson.model_validate(item) for item in cached_films]

        source = await self.repository.get_by_id(person_id)
        if source is None:
            return []

        films = PersonMapper.to_films(source)
        start = (page_number - 1) * page_size
        end = start + page_size
        paged_films = films[start:end]

        await self._set_cache_json(
            cache_key,
            [film.model_dump(mode="json") for film in paged_films],
        )
        return paged_films

    @staticmethod
    def _build_search_query(
        query: str,
        role: str | None = None,
    ) -> dict:
        """Построить ES-запрос для поиска персон."""
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
                        "query": {"term": {"films.roles": role}},
                    }
                }
            ]
        return search_query


def get_person_service(
    elastic: AsyncElasticsearch,
    redis: Redis,
) -> PersonService:
    """
    Создать и вернуть экземпляр PersonService с зависимостями.

    Args:
        elastic: Клиент Elasticsearch для доступа к персонам.
        redis: Клиент Redis для кэширования результатов.

    Returns:
        PersonService: Инициализированный сервис с репозиторием и кэшем.
    """
    settings = get_settings()
    repository = ElasticsearchRepository(
        elastic=elastic,
        index_name=settings.elasticsearch_persons_index,
        source_fields=["id", "full_name", "films"],
    )
    cache_backend = RedisCacheBackend(redis)
    return PersonService(
        repository=repository,
        cache=cache_backend,
        settings=settings,
    )
