from uuid import UUID

from pydantic import Field

from models.base import SchemaBase


class GenreShort(SchemaBase):
    """
    Краткая схема жанра для API.

    Attributes:
        uuid: Уникальный идентификатор жанра.
        name: Название жанра.
    """

    uuid: UUID
    name: str


class GenreDetail(SchemaBase):
    """
    Детальная схема жанра для API.

    Attributes:
        uuid: Уникальный идентификатор жанра.
        name: Название жанра.
        description: Описание жанра (опционально).
    """

    uuid: UUID
    name: str
    description: str | None = Field(default=None)
