# Package initializer for functional tests

from utils.test_data import _generate_random_text
from utils.test_data import _prepare_bulk_actions
from utils.test_data import build_film_bulk_data
from utils.test_data import build_genre_bulk_data
from utils.test_data import build_person_bulk_data

__all__ = [
    "_generate_random_text",
    "_prepare_bulk_actions",
    "build_film_bulk_data",
    "build_genre_bulk_data",
    "build_person_bulk_data",
]
