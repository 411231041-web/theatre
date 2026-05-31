"""Утилиты для работы с Elasticsearch в функциональных тестах.

Содержит функцию для пересоздания индекса с указанным маппингом.
"""

from elasticsearch import AsyncElasticsearch
from typing import Dict


async def recreate_index(
    es_client: AsyncElasticsearch, index: str, mapping: Dict
) -> None:
    """Удаляет и создаёт индекс Elasticsearch с указанным маппингом.

    Если индекс существует, сначала удаляет его, а затем создаёт заново
    с переданным маппингом.

    Параметры
    ---------
    es_client: AsyncElasticsearch
        Клиент Elasticsearch.
    index: str
        Имя индекса.
    mapping: Dict
        Маппинг индекса.
    """
    if await es_client.indices.exists(index=index):
        await es_client.indices.delete(index=index)
    await es_client.indices.create(index=index, mappings=mapping)
