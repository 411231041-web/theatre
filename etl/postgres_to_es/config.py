"""Настройки конфигурации ETL-конвейера."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки ETL с поддержкой переменных окружения."""

    # Настройки PostgreSQL
    postgres_host: str = Field(
        default="localhost", validation_alias="SQL_HOST"
    )
    postgres_port: int = Field(default=5432, validation_alias="SQL_PORT")
    postgres_db: str = Field(
        default="movies_database", validation_alias="POSTGRES_DB"
    )
    postgres_user: str = Field(
        default="postgres", validation_alias="POSTGRES_USER"
    )
    postgres_password: str = Field(
        default="postgres", validation_alias="POSTGRES_PASSWORD"
    )

    # Настройки Elasticsearch
    elasticsearch_host: str = Field(
        default="localhost", validation_alias="ELASTICSEARCH_HOST"
    )
    elasticsearch_port: int = Field(
        default=9200, validation_alias="ELASTICSEARCH_PORT"
    )
    elasticsearch_index: str = Field(
        default="movies", validation_alias="ELASTICSEARCH_FILMS_INDEX"
    )

    # Настройки ETL
    etl_state_file: str = Field(
        default="etl_films_state.json", validation_alias="ETL_STATE_FILE"
    )
    batch_size: int = Field(default=100, validation_alias="ETL_BATCH_SIZE")
    poll_interval: int = Field(
        default=10, validation_alias="ETL_POLL_INTERVAL"
    )

    # Настройки повторных попыток
    max_retries: int = Field(default=5, validation_alias="ETL_MAX_RETRIES")
    initial_backoff: float = Field(
        default=1.0, validation_alias="ETL_INITIAL_BACKOFF"
    )
    max_backoff: float = Field(
        default=60.0, validation_alias="ETL_MAX_BACKOFF"
    )
    backoff_multiplier: float = Field(
        default=2.0, validation_alias="ETL_BACKOFF_MULTIPLIER"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def postgres_dsn(self) -> str:
        """DSN подключения к PostgreSQL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def elasticsearch_url(self) -> str:
        """Базовый URL Elasticsearch."""
        return f"http://{self.elasticsearch_host}:{self.elasticsearch_port}"


def get_settings() -> Settings:
    """Получаем настройки приложения."""
    return Settings()
