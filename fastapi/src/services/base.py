"""
Базовые сервисы с общей логикой работы с кэшем и данными.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic

from core.config import Settings
from services.cache import (
    build_cache_key,
    CacheBackend,
)
from services.repositories import BaseRepository

TShort = TypeVar("TShort")
TDetail = TypeVar("TDetail")


class BaseService(ABC, Generic[TDetail, TShort]):
    """Базовый сервис с логикой кэширования и получения данных."""

    def __init__(
        self,
        repository: BaseRepository,
        cache: CacheBackend,
        settings: Settings,
    ) -> None:
        """
        Инициализация базового сервиса.

        Args:
            repository: Репозиторий для доступа к данным.
            cache: Абстрактный бекенд кэша.
            settings: Конфигурация приложения.
        """
        self.repository = repository
        self.cache = cache
        self.settings = settings

    @staticmethod
    @abstractmethod
    def _map_to_short(source: dict) -> TShort:
        """Преобразовать ES-данные в краткую модель."""
        pass

    @staticmethod
    @abstractmethod
    def _map_to_detail(source: dict) -> TDetail:
        """Преобразовать ES-данные в детальную модель."""
        pass

    def _get_cache_expire(self) -> int:
        """Получить время жизни кэша."""
        return self.settings.redis_cache_expire

    async def _get_from_cache_model(
        self,
        cache_key: str,
        model_type: type[TDetail],
    ) -> TDetail | None:
        """Получить модель из кэша."""
        return await self.cache.get_model(cache_key, model_type)

    async def _get_from_cache_json(
        self,
        cache_key: str,
    ) -> dict | list | None:
        """Получить JSON из кэша."""
        return await self.cache.get_json(cache_key)

    async def _set_cache_model(
        self,
        cache_key: str,
        model: TDetail,
    ) -> None:
        """Сохранить модель в кэш."""
        await self.cache.set_model(
            cache_key,
            model,
            self._get_cache_expire(),
        )

    async def _set_cache_json(
        self,
        cache_key: str,
        data: dict | list,
    ) -> None:
        """Сохранить JSON в кэш."""
        await self.cache.set_json(
            cache_key,
            data,
            self._get_cache_expire(),
        )

    def _build_cache_key(
        self,
        prefix: str,
        **kwargs,
    ) -> str:
        """Построить ключ кэша."""
        return build_cache_key(prefix, **kwargs)
