from fastapi import APIRouter

from src.api.v1.films import router as films_router
from src.api.v1.genres import router as genres_router
from src.api.v1.persons import router as persons_router

router = APIRouter(prefix="/api/v1")
"""
Роутер для API версии 1.

Объединяет все роутеры для различных сущностей (фильмы, жанры, персоны)
под единым префиксом /api/v1.

Attributes:
    prefix (str): Префикс для всех вложенных роутов.
"""

router.include_router(films_router)
router.include_router(genres_router)
router.include_router(persons_router)
