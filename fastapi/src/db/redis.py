from redis.asyncio import Redis

from src.core.config import get_settings

_client: Redis | None = None
"""
Глобальный клиент Redis для повторного использования в приложении.
"""


def get_redis_client() -> Redis:
    """
    Получить клиент Redis с ленивой инициализацией.

    Создает клиент при первом вызове и возвращает существующий экземпляр
    при последующих вызовах.

    Returns:
        Redis: Клиент для взаимодействия с Redis.
    """
    global _client

    if _client is None:
        settings = get_settings()
        _client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

    return _client


async def close_redis_client() -> None:
    """
    Закрыть соединение с Redis.

    Освобождает ресурсы и закрывает соединение с Redis.
    """
    global _client

    if _client is not None:
        await _client.aclose()
        _client = None
