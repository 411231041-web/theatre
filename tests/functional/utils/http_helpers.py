"""HTTP-утилиты для функциональных тестов.

Содержит функцию для постраничного получения всех элементов API.
"""

import aiohttp
from typing import Dict, Any


async def fetch_all_pages(
    session: aiohttp.ClientSession,
    url: str,
    params: Dict | None = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    """Получить все элементы, постранично обходя API.

    Параметры и поведение соответствуют реализации в исходном
    `conftest.py`.
    """
    params = dict(params or {})
    page_size = min(page_size, 100)
    params["page_size"] = page_size
    page_number = 1
    all_items: list[dict] = []

    while True:
        params["page_number"] = page_number
        async with session.get(url, params=params) as response:
            status = response.status
            body = await response.json()
            if status != 200:
                return {
                    "status": status,
                    "items": all_items,
                    "error": body,
                }

        if (
            not isinstance(body, dict)
            or not isinstance(body.get("results"), list)
        ):
            return {
                "status": 500,
                "items": all_items,
                "error": (
                    "Ожидался пагинированный ответ с полем 'results'"
                ),
            }

        page_items = body["results"]
        all_items.extend(page_items)
        if body.get("next") is None or len(page_items) < page_size:
            break

        page_number += 1

    return {
        "status": 200,
        "items": all_items,
    }
