import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, TypeVar

from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError


ModelType = TypeVar("ModelType", bound=BaseModel)


class CacheBackend(ABC):
    """Абстрактный интерфейс для кэширования."""

    @abstractmethod
    async def get_model(
        self,
        key: str,
        model_cls: type[ModelType],
    ) -> ModelType | None:
        """Получить модель из кэша по ключу."""

    @abstractmethod
    async def set_model(
        self,
        key: str,
        value: BaseModel,
        expire: int,
    ) -> None:
        """Сохранить модель в кэше."""

    @abstractmethod
    async def get_json(self, key: str) -> Any | None:
        """Получить JSON-данные из кэша."""

    @abstractmethod
    async def set_json(
        self,
        key: str,
        value: Any,
        expire: int,
    ) -> None:
        """Сохранить JSON-данные в кэше."""


class RedisCacheBackend(CacheBackend):
    """Реализация кэша на основе Redis."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get_model(
        self,
        key: str,
        model_cls: type[ModelType],
    ) -> ModelType | None:
        return await get_cached_model(self.redis, key, model_cls)

    async def set_model(
        self,
        key: str,
        value: BaseModel,
        expire: int,
    ) -> None:
        await set_cached_model(self.redis, key, value, expire)

    async def get_json(self, key: str) -> Any | None:
        return await get_cached_json(self.redis, key)

    async def set_json(
        self,
        key: str,
        value: Any,
        expire: int,
    ) -> None:
        await set_cached_json(self.redis, key, value, expire)


def build_cache_key(namespace: str, **params: Any) -> str:
    """
    Сгенерировать уникальный ключ для кэша на основе namespace и параметров.

    Создает хэш из параметров с использованием SHA256 для обеспечения
    уникальности и предсказуемости ключей.

    Args:
        namespace: Пространство имен для кэша (например, "films:get_by_id").
        **params: Параметры, которые будут включены в ключ.

    Returns:
        str: Уникальный ключ для кэша в формате "namespace:hash".
    """
    payload = json.dumps(
        params,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


async def get_cached_model(
    redis: Redis,
    key: str,
    model_cls: type[ModelType],
) -> ModelType | None:
    """
    Получить закэшированную модель из Redis.

    Args:
        redis: Клиент Redis.
        key: Ключ кэша.
        model_cls: Класс модели для валидации.

    Returns:
        ModelType | None: Экземпляр модели или None, если данные не
            найдены или невалидны.
    """
    try:
        payload = await redis.get(key)
    except RedisError:
        return None

    if payload is None:
        return None

    try:
        return model_cls.model_validate_json(payload)
    except (TypeError, ValueError):
        return None


async def set_cached_model(
    redis: Redis,
    key: str,
    value: BaseModel,
    expire: int,
) -> None:
    """
    Сохранить модель в кэш Redis.

    Args:
        redis: Клиент Redis.
        key: Ключ кэша.
        value: Модель для сохранения.
        expire: Время жизни кэша в секундах.
    """
    try:
        await redis.set(key, value.model_dump_json(), ex=expire)
    except RedisError:
        return


async def get_cached_models(
    redis: Redis,
    key: str,
    model_cls: type[ModelType],
) -> list[ModelType] | None:
    """
    Получить список закэшированных моделей из Redis.

    Args:
        redis: Клиент Redis.
        key: Ключ кэша.
        model_cls: Класс модели для валидации.

    Returns:
        list[ModelType] | None: Список моделей или None, если данные не
            найдены или невалидны.
    """
    try:
        payload = await redis.get(key)
    except RedisError:
        return None

    if payload is None:
        return None

    try:
        raw_items = json.loads(payload)
    except (TypeError, ValueError):
        return None

    if not isinstance(raw_items, list):
        return None

    try:
        return [model_cls.model_validate(item) for item in raw_items]
    except (TypeError, ValueError):
        return None


async def set_cached_models(
    redis: Redis,
    key: str,
    values: Sequence[BaseModel],
    expire: int,
) -> None:
    """
    Сохранить список моделей в кэш Redis.

    Args:
        redis: Клиент Redis.
        key: Ключ кэша.
        values: Список моделей для сохранения.
        expire: Время жизни кэша в секундах.
    """
    payload = [item.model_dump(mode="json") for item in values]
    try:
        await redis.set(key, json.dumps(payload), ex=expire)
    except RedisError:
        return


async def get_cached_json(
    redis: Redis,
    key: str,
) -> Any | None:
    """
    Получить закэшированные данные в формате JSON из Redis.

    Args:
        redis: Клиент Redis.
        key: Ключ кэша.

    Returns:
        Any | None: Данные в формате JSON или None, если данные не
            найдены или невалидны.
    """
    try:
        payload = await redis.get(key)
    except RedisError:
        return None

    if payload is None:
        return None

    try:
        return json.loads(payload)
    except (TypeError, ValueError):
        return None


async def set_cached_json(
    redis: Redis,
    key: str,
    value: Any,
    expire: int,
) -> None:
    """
    Сохранить данные в формате JSON в кэш Redis.

    Args:
        redis: Клиент Redis.
        key: Ключ кэша.
        value: Данные для сохранения.
        expire: Время жизни кэша в секундах.
    """
    try:
        await redis.set(key, json.dumps(value), ex=expire)
    except RedisError:
        return
