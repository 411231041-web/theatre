from uuid import UUID

from pydantic import Field

from src.models.base import SchemaBase


class FilmInPerson(SchemaBase):
    """
    Схема фильма внутри персоны.

    Attributes:
        uuid: Уникальный идентификатор фильма.
        roles: Список ролей персоны в фильме.
    """

    uuid: UUID
    roles: list[str] = Field(default_factory=list)


class PersonShort(SchemaBase):
    """
    Краткая схема персоны для списков.

    Attributes:
        uuid: Уникальный идентификатор персоны.
        full_name: Имя и фамилия персоны.
    """

    uuid: UUID
    full_name: str


class PersonDetail(SchemaBase):
    """
    Детальная схема персоны для API.

    Attributes:
        uuid: Уникальный идентификатор персоны.
        full_name: Имя и фамилия персоны.
        films: Список фильмов с ролями персоны.
    """

    uuid: UUID
    full_name: str
    films: list[FilmInPerson] = Field(default_factory=list)


class PersonSearchResult(SchemaBase):
    """
    Результат поиска персоны.

    Attributes:
        uuid: Уникальный идентификатор персоны.
        full_name: Имя и фамилия персоны.
        films: Список фильмов с ролями персоны.
    """

    uuid: UUID
    full_name: str
    films: list[FilmInPerson] = Field(default_factory=list)
