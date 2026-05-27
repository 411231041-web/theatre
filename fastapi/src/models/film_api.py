from uuid import UUID

from pydantic import Field

from models.base import SchemaBase


class FilmShort(SchemaBase):
    """
    Краткая схема фильма для списков.

    Attributes:
        uuid: Уникальный идентификатор фильма.
        title: Название фильма.
        imdb_rating: Рейтинг IMDb (опционально).
        genres: Список жанров фильма.
    """

    uuid: UUID
    title: str
    imdb_rating: float | None = Field(default=None)
    genres: list[str] = Field(default_factory=list)


class GenreInFilm(SchemaBase):
    """
    Схема жанра внутри фильма.

    Attributes:
        uuid: Уникальный идентификатор жанра (опционально).
        name: Название жанра.
    """

    uuid: UUID | None = Field(default=None)
    name: str


class PersonInFilm(SchemaBase):
    """
    Схема участника фильма (актер, режиссер, сценарист).

    Attributes:
        uuid: Уникальный идентификатор персоны.
        full_name: Имя и фамилия персоны.
    """

    uuid: UUID
    full_name: str


class FilmDetail(SchemaBase):
    """
    Детальная схема фильма для API.

    Attributes:
        uuid: Уникальный идентификатор фильма.
        title: Название фильма.
        imdb_rating: Рейтинг IMDb (опционально).
        description: Описание фильма (опционально).
        genre: Список жанров.
        actors: Список актеров.
        writers: Список сценаристов.
        directors: Список режиссеров.
    """

    uuid: UUID
    title: str
    imdb_rating: float | None = Field(default=None)
    description: str | None = Field(default=None)
    genre: list[GenreInFilm] = Field(default_factory=list)
    actors: list[PersonInFilm] = Field(default_factory=list)
    writers: list[PersonInFilm] = Field(default_factory=list)
    directors: list[PersonInFilm] = Field(default_factory=list)
