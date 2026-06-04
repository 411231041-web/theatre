"""
Модуль моделей данных.

Содержит схемы Pydantic для работы с фильмами, жанрами и персоналиями.
"""

from models.film import Film, FilmBase, FilmType
from models.genre import Genre, GenreBase, GenreShort
from models.person import Person, PersonBase, PersonInFilm, PersonRole

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
