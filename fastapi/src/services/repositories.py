"""
Абстрактные репозитории для работы с хранилищем.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError

TEntity = TypeVar("TEntity")


class BaseRepository(ABC, Generic[TEntity]):
    """Абстрактный базовый репозиторий."""

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> dict | None:
        """Получить сущность по ID."""
        pass

    @abstractmethod
    async def search(
        self,
        query_body: dict,
        sort_field: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        """Поиск с сортировкой и пагинацией."""
        pass


class ElasticsearchRepository(BaseRepository[TEntity]):
    """Реализация репозитория через Elasticsearch."""

    def __init__(
        self,
        elastic: AsyncElasticsearch,
        index_name: str,
        source_fields: list[str] | None = None,
    ) -> None:
        """
        Инициализация ES-репозитория.

        Args:
            elastic: Клиент Elasticsearch.
            index_name: Имя индекса.
            source_fields: Поля для выборки из документа.
        """
        self.elastic = elastic
        self.index_name = index_name
        self.source_fields = source_fields or ["id"]

    async def get_by_id(self, entity_id: UUID) -> dict | None:
        """Получить сущность по ID."""
        try:
            response = await self.elastic.get(
                index=self.index_name,
                id=str(entity_id),
            )
            return response.get("_source")
        except NotFoundError:
            return None

    async def search(
        self,
        query_body: dict,
        sort_field: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        """Поиск с сортировкой и пагинацией."""
        response = await self.elastic.search(
            index=self.index_name,
            body={
                "query": query_body,
                "sort": [{sort_field: {"order": sort_order}}],
                "from": offset,
                "size": limit,
                "_source": self.source_fields,
                "track_total_hits": True,
            },
        )

        hits = response.get("hits", {}).get("hits", [])
        total = response.get("hits", {}).get("total", {}).get("value", 0)
        return [hit.get("_source") or {} for hit in hits], total
