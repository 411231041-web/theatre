from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from api.v1.router import router as api_v1_router
from db.elasticsearch import close_elastic_client
from db.redis import close_redis_client


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """
    Управляет жизненным циклом приложения FastAPI.

    Инициализирует ресурсы при запуске и освобождает их при остановке.
    В данном случае закрывает соединения с Elasticsearch и Redis при
    выключении.

    Args:
        _app: Экземпляр приложения FastAPI (не используется, но требуется
            сигнатурой).

    Yields:
        None
    """
    yield
    await close_elastic_client()
    await close_redis_client()


app = FastAPI(
    title="Read-only API для онлайн-кинотеатра",
    description=(
        "Информация о фильмах, жанрах и людях, участвовавших в "
        "создании произведения"
    ),
    lifespan=lifespan,
    version="1.0.0",
    # Адрес документации в красивом интерфейсе
    docs_url="/api/v1/openapi",
    # Адрес документации в формате OpenAPI
    openapi_url="/api/v1/openapi.json",
    # Можно сразу сделать небольшую оптимизацию сервиса
    # и заменить стандартный JSON-сериализатор на более шуструю версию,
    # написанную на Rust
    default_response_class=ORJSONResponse,
)
"""
Экземпляр приложения FastAPI для сервиса фильмов.

Настроен с использованием:
- Названия приложения: "Read-only API для онлайн-кинотеатра"
- Контекстного менеджера `lifespan` для управления ресурсами
- API роутера версии 1

Attributes:
    title (str): Название приложения.
    lifespan (Callable): Контекстный менеджер для управления
        жизненным циклом.
"""

app.include_router(api_v1_router)


@app.get("/")
async def root() -> dict[str, str]:
    """
    Корневой endpoint для проверки работоспособности сервиса.

    Returns:
        dict[str, str]: Словарь со статусом "ok" при успешной проверке.
    """
    return {"status": "ok"}
