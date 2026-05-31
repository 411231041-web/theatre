"""Утилиты для API v1.

Здесь хранятся общие функции для роутеров v1, не завязанные на
конкретный домен: фильмы, жанры, персоны.
"""

import math


def calculate_total_pages(total_hits: int, page_size: int) -> int:
    """Вычислить число страниц по общему числу результатов."""
    return max(1, math.ceil(total_hits / page_size))


def paginated_result(
    items: list,
    total_hits: int,
    page_number: int,
    page_size: int,
) -> dict[str, int | None | list]:
    """Вернуть ответ в формате page meta + results для пагинации."""
    total_pages = calculate_total_pages(total_hits, page_size)
    return {
        "count": total_hits,
        "total_pages": total_pages,
        "prev": page_number - 1 if page_number > 1 else None,
        "next": page_number + 1 if page_number < total_pages else None,
        "results": items,
    }
