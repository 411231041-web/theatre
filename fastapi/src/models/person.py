from datetime import datetime
from enum import Enum
from uuid import UUID

from src.models.base import SchemaBase


class PersonRole(str, Enum):
    """
    Роль персоны в фильме.

    Attributes:
        ACTOR: Актёр.
        DIRECTOR: Режиссер.
        WRITER: Сценарист.
    """

    ACTOR = "actor"
    DIRECTOR = "director"
    WRITER = "writer"


class PersonBase(SchemaBase):
    """
    Базовая схема персоны.

    Attributes:
        id: Уникальный идентификатор персоны.
        full_name: Имя и фамилия персоны.
    """

    id: UUID
    full_name: str


class PersonInFilm(PersonBase):
    """
    Схема персоны внутри фильма.

    Attributes:
        id: Уникальный идентификатор персоны.
        full_name: Имя и фамилия персоны.
        role: Роль персоны в фильме.
    """

    role: PersonRole


class Person(PersonBase):
    """
    Полная схема персоны.

    Attributes:
        id: Уникальный идентификатор персоны.
        full_name: Имя и фамилия персоны.
        created: Дата создания записи.
        modified: Дата последнего изменения.
    """

    created: datetime
    modified: datetime
