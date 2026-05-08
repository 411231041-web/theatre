"""
Модуль моделей данных.

Содержит схемы Pydantic для работы с фильмами, жанрами и персоналиями.
"""

from src.models.film import Film, FilmBase, FilmType
from src.models.genre import Genre, GenreBase, GenreShort
from src.models.person import Person, PersonBase, PersonInFilm, PersonRole

__all__ = [
    "Film",
    "FilmBase",
    "FilmType",
    "Genre",
    "GenreBase",
    "GenreShort",
    "Person",
    "PersonBase",
    "PersonInFilm",
    "PersonRole",
]
