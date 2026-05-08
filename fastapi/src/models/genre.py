from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.models.base import SchemaBase


class GenreShort(SchemaBase):
    """
    Краткая схема жанра для списков.

    Attributes:
        id: Уникальный идентификатор жанра.
        name: Название жанра.
    """

    id: UUID
    name: str


class GenreBase(GenreShort):
    """
    Базовая схема жанра (без полного описания).

    Attributes:
        id: Уникальный идентификатор жанра.
        name: Название жанра.
        description: Описание жанра (опционально).
        created: Дата создания записи.
        modified: Дата последнего изменения.
    """

    id: UUID
    description: str | None = Field(default=None)
    created: datetime
    modified: datetime


class Genre(GenreBase):
    """
    Полная схема жанра.

    Наследует все атрибуты GenreBase.
    """
