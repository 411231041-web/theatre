from typing import Generic, TypeVar

from pydantic import ConfigDict, Field
from pydantic import BaseModel


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Универсальная схема ответа для пагинации.

    Attributes:
        count: Общее количество элементов.
        total_pages: Общее количество страниц.
        prev: Номер предыдущей страницы или None.
        next: Номер следующей страницы или None.
        results: Список элементов текущей страницы.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    count: int
    total_pages: int
    prev: int | None = None
    next: int | None = None
    results: list[T] = Field(default_factory=list)
