from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from models.base import SchemaBase
from models.genre import GenreShort
from models.person import PersonInFilm


class FilmType(str, Enum):
    """
    Тип контента (фильм или телешоу).

    Attributes:
        MOVIE: Кинofilm.
        TV_SHOW: Телешоу.
    """

    MOVIE = "movie"
    TV_SHOW = "tv show"


class FilmBase(SchemaBase):
    """
    Базовая схема для фильма (без связанных данных).

    Attributes:
        id: Уникальный идентификатор фильма.
        title: Название фильма.
        description: Описание фильма (опционально).
        creation_date: Дата создания (опционально).
        rating: Рейтинг фильма (от 1.0 до 10.0, опционально).
        type: Тип контента (фильм или телешоу).
        created: Дата создания записи.
        modified: Дата последнего изменения.
    """

    id: UUID
    title: str
    description: str | None = Field(default=None)
    creation_date: date | None = Field(default=None)
    rating: float | None = Field(default=None, ge=1.0, le=10.0)
    type: FilmType
    created: datetime
    modified: datetime


class Film(FilmBase):
    """
    Полная схема фильма со связанными данными.

    Attributes:
        genres: Список жанров фильма.
        persons: Список участников фильма.
    """

    genres: list[GenreShort] = Field(default_factory=list)
    persons: list[PersonInFilm] = Field(default_factory=list)
