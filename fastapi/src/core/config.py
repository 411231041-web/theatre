from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Конфигурация приложения для подключения к Elasticsearch и Redis.

    Атрибуты настраиваются через переменные окружения.
    """

    elasticsearch_host: str = Field(
        default="localhost",
        alias="ELASTICSEARCH_HOST",
    )
    """
    Хост Elasticsearch (по умолчанию: localhost).
    """

    elasticsearch_port: int = Field(default=9200, alias="ELASTICSEARCH_PORT")
    """
    Порт Elasticsearch (по умолчанию: 9200).
    """

    elasticsearch_index: str = Field(
        default="movies",
        alias="ELASTICSEARCH_FILMS_INDEX",
    )
    """
    Имя индекса для фильмов в Elasticsearch (по умолчанию: movies).
    """

    elasticsearch_genres_index: str = Field(
        default="genres",
        alias="ELASTICSEARCH_GENRES_INDEX",
    )
    """
    Имя индекса для жанров в Elasticsearch (по умолчанию: genres).
    """

    elasticsearch_persons_index: str = Field(
        default="persons",
        alias="ELASTICSEARCH_PERSONS_INDEX",
    )
    """
    Имя индекса для персон в Elasticsearch (по умолчанию: persons).
    """

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    """
    Хост Redis (по умолчанию: localhost).
    """

    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    """
    Порт Redis (по умолчанию: 6379).
    """

    redis_db: int = Field(default=0, alias="REDIS_DB")
    """
    Номер базы данных Redis (по умолчанию: 0).
    """

    redis_cache_expire: int = Field(
        default=300,
        alias="REDIS_CACHE_EXPIRE",
    )
    """
    Время жизни кэша в Redis в секундах (по умолчанию: 300).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    """
    Конфигурация Pydantic Settings:
    - env_file: Путь к файлу .env
    - env_file_encoding: Кодировка файла .env
    - case_sensitive: Регистрозависимость переменных
    - extra: Игнорировать неизвестные переменные
    """

    @property
    def elasticsearch_url(self) -> str:
        """
        Сформировать полный URL для подключения к Elasticsearch.

        Returns:
            str: URL в формате "http://host:port".
        """
        return f"http://{self.elasticsearch_host}:{self.elasticsearch_port}"

    @property
    def redis_url(self) -> str:
        """
        Сформировать полный URL для подключения к Redis.

        Returns:
            str: URL в формате "redis://host:port/db".
        """
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Получить экземпляр конфигурации с кэшированием.

    Использует lru_cache для создания единственного экземпляра Settings
    в течение жизненного цикла приложения.

    Returns:
        Settings: Экземпляр конфигурации.
    """
    return Settings()
