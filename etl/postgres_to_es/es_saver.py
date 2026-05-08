"""Операции с Elasticsearch для ETL-конвейера."""

from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from .logger import logger
from .backoff import RetryConfig


class ElasticsearchSaver:
    """Сохраняет преобразованные документы в Elasticsearch."""

    def __init__(
        self,
        es_url: str,
        index_name: str,
        retry_config: RetryConfig,
    ):
        """Инициализируем компонент сохранения в Elasticsearch."""
        self.es_url = es_url
        self.index_name = index_name
        self.retry_config = retry_config
        self._client = None

    def connect(self) -> None:
        """Устанавливаем соединение с Elasticsearch."""
        def _connect():
            self._client = Elasticsearch([self.es_url])
            # Проверяем соединение
            self._client.info()
            logger.info(f"Connected to Elasticsearch at {self.es_url}")

        self.retry_config.execute_with_retry(_connect)

    def close(self) -> None:
        """Закрываем соединение с Elasticsearch."""
        if self._client:
            self._client.close()
            logger.info("Closed Elasticsearch connection")

    def ensure_index_exists(self, settings: Dict[str, Any]) -> None:
        """Проверяем, что индекс существует и имеет корректный маппинг."""
        def _ensure():
            if not self._client:
                self.connect()

            if not self._client.indices.exists(index=self.index_name):
                logger.info(f"Creating index {self.index_name}")
                self._client.indices.create(
                    index=self.index_name, body=settings)
            else:
                logger.info(f"Index {self.index_name} already exists")

        self.retry_config.execute_with_retry(_ensure)

    def bulk_write(self, documents: List[Dict[str, Any]]) -> int:
        """Записываем документы в Elasticsearch через массовую операцию API."""
        if not documents:
            return 0

        def _bulk_write():
            if not self._client:
                self.connect()

            # Подготавливаем действия для bulk-операции
            actions = []
            for doc in documents:
                doc_id = doc["id"]
                action = {
                    "_op_type": "index",
                    "_index": self.index_name,
                    "_id": doc_id,
                    "_source": doc,
                }
                actions.append(action)

            # Выполняем bulk-операцию
            success_count, errors = bulk(
                self._client,
                actions,
                chunk_size=500,
                raise_on_error=False,
                stats_only=False,
            )

            if errors:
                raise RuntimeError(
                    f"Bulk write failed for {len(errors)} documents: "
                    f"{errors[:2]}"
                )

            logger.info(
                "Successfully wrote %s/%s documents to %s",
                success_count,
                len(documents),
                self.index_name,
            )
            return success_count

        return self.retry_config.execute_with_retry(_bulk_write)
