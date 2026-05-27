"""Утилиты для генерации тестовых данных.

Содержит функции для генерации случайного текста, формирования bulk-документов
для Elasticsearch и подготовки тестовых данных для фильмов, жанров и персон.
"""

import datetime
import random
import string
import uuid

from settings import test_settings


def _generate_random_text(prefix: str, length: int = 16) -> str:
    """Возвращает случайный текст с указанным префиксом.

    Формирует строку из префикса и случайных буквенно-цифровых
    символов заданной длины. Полностью детерминирован для избежания флаков.
    """
    return prefix + " " + "".join(
        random.choices(string.ascii_letters + string.digits, k=length)
    )


def _prepare_bulk_actions(
    documents: list[dict], index: str = ""
) -> list[dict]:
    """Формирует список действий bulk для документов Elasticsearch.

    Каждый документ упаковывается в действие с индексом, _id и
    _source для массовой записи в Elasticsearch.
    """
    return [
        {"_index": index, "_id": doc["id"], "_source": doc}
        for doc in documents
    ]


def _create_film_doc(prefix: str, use_practicum: bool = False, index: int = None) -> dict:
    """Создаёт один документ фильма с указанным префиксом."""
    if use_practicum:
        # index == 0: только "practicum"
        # остальные: "{prefix} practicum"
        title = "practicum" if index == 0 else f"{prefix} practicum"
    else:
        # Все остальные содержат префикс (обычно "Test movie")
        title = _generate_random_text(prefix)
    
    return {
        "id": str(uuid.uuid4()),
        "imdb_rating": round(5.0 + random.random() * 5.0, 1),
        "genre": [random.choice(["Drama", "Action", "Comedy", "Sci-Fi"])],
        "title": title,
        "description": _generate_random_text("Description", 48),
        "director": [_generate_random_text("Director", 10)],
        "actors_names": [
            _generate_random_text("Actor", 8),
            _generate_random_text("Actor", 8),
        ],
        "writers_names": [
            _generate_random_text("Writer", 8),
            _generate_random_text("Writer", 8),
        ],
        "actors": [
            {
                "id": str(uuid.uuid4()),
                "name": _generate_random_text("Actor", 8),
            },
            {
                "id": str(uuid.uuid4()),
                "name": _generate_random_text("Actor", 8),
            },
        ],
        "writers": [
            {
                "id": str(uuid.uuid4()),
                "name": _generate_random_text("Writer", 8),
            },
            {
                "id": str(uuid.uuid4()),
                "name": _generate_random_text("Writer", 8),
            },
        ],
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "film_work_type": "movie",
    }


def _create_genre_doc(prefix: str, use_practicum: bool = False, index: int = None) -> dict:
    """Создаёт один документ жанра с указанным префиксом."""
    if use_practicum:
        # index == 0: только "practicum"
        # остальные: "{prefix} practicum"
        name = "practicum" if index == 0 else f"{prefix} practicum"
    else:
        # Все остальные содержат префикс (обычно "Test")
        name = _generate_random_text(prefix)
    
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": _generate_random_text("Description", 48),
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
    }


def _create_person_doc(prefix: str, use_practicum: bool = False, index: int = None) -> dict:
    """Создаёт один документ персоны с указанным префиксом."""
    if use_practicum:
        # index == 0: только "practicum"
        # остальные: "{prefix} practicum"
        full_name = "practicum" if index == 0 else f"{prefix} practicum"
    else:
        # Все остальные содержат префикс (обычно "Test person")
        full_name = _generate_random_text(prefix)
    
    return {
        "id": str(uuid.uuid4()),
        "full_name": full_name,
        "films": [
            {
                "id": str(uuid.uuid4()),
                "roles": [random.choice(["actor", "director", "writer"])],
            }
            for _ in range(3)
        ],
    }


def build_film_bulk_data(count: int, query_prefix: str) -> list[dict]:
    """Подготавливает набор документов фильмов для bulk-загрузки.

    Генерирует 20 тестовых данных со словом 'practicum' в title,
    остальные со случайным текстом но с префиксом query_prefix.
    Возвращает список действий bulk для Elasticsearch.
    """
    practicum_count = min(20, count)
    documents = []
    
    # Первые 20 документов с "practicum"
    for i in range(practicum_count):
        documents.append(_create_film_doc(query_prefix, use_practicum=True, index=i))
    
    # Остальные документы - содержат префикс но не "practicum"
    for _ in range(count - practicum_count):
        documents.append(_create_film_doc(query_prefix, use_practicum=False))
    
    return _prepare_bulk_actions(documents, index=test_settings.es_film_index)


def build_genre_bulk_data(count: int, query_prefix: str) -> list[dict]:
    """Подготавливает набор документов жанров для bulk-загрузки.

    Генерирует 20 тестовых данных со словом 'practicum' в name,
    остальные со случайным текстом но с префиксом query_prefix.
    Возвращает список действий bulk для Elasticsearch.
    """
    practicum_count = min(20, count)
    documents = []
    
    # Первые 20 документов с "practicum"
    for i in range(practicum_count):
        documents.append(_create_genre_doc(query_prefix, use_practicum=True, index=i))
    
    # Остальные документы - содержат префикс но не "practicum"
    for _ in range(count - practicum_count):
        documents.append(_create_genre_doc(query_prefix, use_practicum=False))
    
    return _prepare_bulk_actions(
        documents, index=test_settings.es_genre_index
    )


def build_person_bulk_data(count: int, query_prefix: str) -> list[dict]:
    """Подготавливает набор документов персон для bulk-загрузки.

    Генерирует 20 тестовых данных со словом 'practicum' в full_name,
    остальные со случайным текстом но с префиксом query_prefix.
    Возвращает список действий bulk для Elasticsearch.
    """
    practicum_count = min(20, count)
    documents = []
    
    # Первые 20 документов с "practicum"
    for i in range(practicum_count):
        documents.append(_create_person_doc(query_prefix, use_practicum=True, index=i))
    
    # Остальные документы - содержат префикс но не "practicum"
    for _ in range(count - practicum_count):
        documents.append(_create_person_doc(query_prefix, use_practicum=False))
    
    return _prepare_bulk_actions(
        documents, index=test_settings.es_person_index
    )
