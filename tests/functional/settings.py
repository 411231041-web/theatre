"""Настройки тестовой среды, загружаемые через Pydantic.

Содержит класс `TestSettings` с параметрами подключения к Elasticsearch,
Redis и базовому URL тестового сервиса.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class TestSettings(BaseSettings):
    es_host: str = Field(alias="ELASTICSEARCH_HOST")
    es_port: int = Field(alias="ELASTICSEARCH_PORT")
    es_film_index: str = Field(alias="ELASTICSEARCH_FILMS_INDEX")
    es_genre_index: str = Field(alias="ELASTICSEARCH_GENRES_INDEX")
    es_person_index: str = Field(alias="ELASTICSEARCH_PERSONS_INDEX")
    es_id_field: str = Field(alias="ES_ID_FIELD")
    es_index_mapping: str = Field(alias="ES_INDEX_MAPPING")

    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(alias="REDIS_PORT")
    service_url: str = Field(alias="SERVICE_URL")

    @property
    def es_url(self) -> str:
        """Сформировать полный URL для подключения к Elasticsearch."""
        return f"http://{self.es_host}:{self.es_port}"


test_settings = TestSettings()
