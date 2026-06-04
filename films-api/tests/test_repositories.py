"""Тесты для репозиториев Elasticsearch."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.repositories import ElasticsearchRepository


@pytest.fixture
def mock_elastic():
    """Создать мок Elasticsearch клиента."""
    return MagicMock()


@pytest.fixture
def repository(mock_elastic):
    """Создать репозиторий с мок-клиентом."""
    return ElasticsearchRepository(
        elastic=mock_elastic,
        index_name="test_index",
        source_fields=["id", "name", "description"],
    )


@pytest.mark.asyncio
async def test_get_by_id_returns_source(mock_elastic, repository):
    """Тест получения сущности по ID.

    Проверяет, что репозиторий корректно возвращает _source документа.
    """
    entity_id = uuid4()
    source_data = {"id": str(entity_id), "name": "Test"}

    mock_elastic.get = AsyncMock(
        return_value={"_source": source_data}
    )

    result = await repository.get_by_id(entity_id)

    assert result == source_data
    mock_elastic.get.assert_awaited_once_with(
        index="test_index",
        id=str(entity_id),
    )


@pytest.mark.asyncio
async def test_get_by_id_returns_none_on_not_found(mock_elastic):
    """Тест обработки 404 при получении по ID.

    Проверяет, что репозиторий возвращает None при отсутствии документа.
    """
    from elasticsearch import NotFoundError

    mock_elastic.get = AsyncMock(
        side_effect=NotFoundError(404, "Not found", {})
        )
    repository = ElasticsearchRepository(
        elastic=mock_elastic,
        index_name="test_index",
    )

    result = await repository.get_by_id(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_search_returns_hits_and_total(mock_elastic, repository):
    """Тест поиска с сортировкой и пагинацией.

    Проверяет, что репозиторий корректно парсит результаты поиска.
    """
    mock_elastic.search = AsyncMock(
        return_value={
            "hits": {
                "total": {"value": 100},
                "hits": [
                    {"_source": {"id": "1", "name": "Item 1"}},
                    {"_source": {"id": "2", "name": "Item 2"}},
                ],
            }
        }
    )

    sources, total = await repository.search(
        query_body={"match_all": {}},
        sort_field="name",
        sort_order="asc",
        offset=0,
        limit=10,
    )

    assert len(sources) == 2
    assert total == 100
    assert sources[0]["id"] == "1"
    assert sources[1]["id"] == "2"

    mock_elastic.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_with_filters(mock_elastic, repository):
    """Тест поиска с фильтрацией.

    Проверяет, что репозиторий корректно передает query_body в ES.
    """
    query_body = {"match": {"name": "test"}}

    mock_elastic.search = AsyncMock(
        return_value={"hits": {"total": {"value": 0}, "hits": []}}
    )

    await repository.search(
        query_body=query_body,
        sort_field="name",
        sort_order="desc",
        offset=20,
        limit=50,
    )

    call_args = mock_elastic.search.call_args
    assert call_args.kwargs["body"]["query"] == query_body
    assert call_args.kwargs["body"]["from"] == 20
    assert call_args.kwargs["body"]["size"] == 50
    assert call_args.kwargs["body"]["sort"] == [{"name": {"order": "desc"}}]


@pytest.mark.asyncio
async def test_search_returns_empty_on_no_hits(mock_elastic, repository):
    """Тест поиска без результатов.

    Проверяет, что репозиторий корректно обрабатывает пустые результаты.
    """
    mock_elastic.search = AsyncMock(
        return_value={"hits": {"total": {"value": 0}, "hits": []}}
    )

    sources, total = await repository.search(
        query_body={"match_all": {}},
        sort_field="id",
        sort_order="asc",
        offset=0,
        limit=10,
    )

    assert sources == []
    assert total == 0


@pytest.mark.asyncio
async def test_search_respects_source_fields(mock_elastic):
    """Тест выборки только нужных полей.

    Проверяет, что репозиторий передает source_fields в запрос.
    """
    repository = ElasticsearchRepository(
        elastic=mock_elastic,
        index_name="test_index",
        source_fields=["id", "title", "rating"],
    )

    mock_elastic.search = AsyncMock(
        return_value={"hits": {"total": {"value": 0}, "hits": []}}
    )

    await repository.search(
        query_body={"match_all": {}},
        sort_field="rating",
        sort_order="desc",
        offset=0,
        limit=10,
    )

    call_args = mock_elastic.search.call_args
    assert call_args.kwargs["body"]["_source"] == [
        "id",
        "title",
        "rating",
    ]
