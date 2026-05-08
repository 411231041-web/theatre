from elasticsearch import AsyncElasticsearch

from src.core.config import get_settings

_client: AsyncElasticsearch | None = None
"""
Глобальный клиент Elasticsearch для повторного использования в приложении.
"""


def get_elastic_client() -> AsyncElasticsearch:
    """
    Получить клиент Elasticsearch с ленивой инициализацией.

    Создает клиент при первом вызове и возвращает существующий экземпляр
    при последующих вызовах.

    Returns:
        AsyncElasticsearch: Клиент для взаимодействия с Elasticsearch.
    """
    global _client

    if _client is None:
        settings = get_settings()
        _client = AsyncElasticsearch(hosts=[settings.elasticsearch_url])

    return _client


async def close_elastic_client() -> None:
    """
    Закрыть соединение с Elasticsearch.

    Освобождает ресурсы и закрывает соединение с Elasticsearch.
    """
    global _client

    if _client is not None:
        await _client.close()
        _client = None
