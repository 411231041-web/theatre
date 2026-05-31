"""Пакет-инициализатор для вспомогательных утилит функциональных тестов.

Экспортирует фабрики данных и вспомогательные функции для генерации
bulk-документов Elasticsearch.
"""

from .test_data_helpers import _generate_random_text
from .test_data_helpers import _prepare_bulk_actions
from .test_data_helpers import build_film_bulk_data
from .test_data_helpers import build_genre_bulk_data
from .test_data_helpers import build_person_bulk_data

__all__ = [
    "_generate_random_text",
    "_prepare_bulk_actions",
    "build_film_bulk_data",
    "build_genre_bulk_data",
    "build_person_bulk_data",
]
