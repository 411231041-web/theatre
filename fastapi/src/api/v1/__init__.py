"""
Модуль API версии 1.

Содержит роутеры для работы с фильмами, жанрами и персоналиями.
"""

from api.v1.films import router as films_router
from api.v1.genres import router as genres_router
from api.v1.persons import router as persons_router

__all__ = ["films_router", "genres_router", "persons_router"]
