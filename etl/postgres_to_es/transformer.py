"""Преобразование данных из записей PostgreSQL в документы Elasticsearch."""

from typing import Dict, List, Any
from .logger import logger


def transform_film_to_document(film_data: Dict[str, Any]) -> Dict[str, Any]:
    """Преобразуем запись фильма из PostgreSQL в документ Elasticsearch."""
    # Извлекаем базовые поля
    doc_id = str(film_data.get("id"))
    title = film_data.get("title") or "Unknown"
    description = film_data.get("description") or ""
    rating = film_data.get("imdb_rating")

    # Обрабатываем рейтинг: приводим к числу с плавающей точкой или None
    imdb_rating = None
    if rating is not None:
        try:
            imdb_rating = float(rating)
        except (ValueError, TypeError):
            imdb_rating = None

    # Нормализуем массивы из агрегатов PostgreSQL JSONB
    genres = [str(g) for g in (film_data.get("genres") or []) if g]
    directors_names = [str(name) for name in (
        film_data.get("directors_names") or []) if name]
    actors_names = [str(name) for name in (
        film_data.get("actors_names") or []) if name]
    writers_names = [str(name) for name in (
        film_data.get("writers_names") or []) if name]

    # Обрабатываем вложенные объекты с идентификатором и именем
    directors = []
    if film_data.get("directors"):
        directors = [
            {"id": str(d["id"]), "name": str(d["name"])}
            for d in film_data["directors"]
            if d and d.get("id") and d.get("name")
        ]

    actors = []
    if film_data.get("actors"):
        actors = [
            {"id": str(a["id"]), "name": str(a["name"])}
            for a in film_data["actors"]
            if a and a.get("id") and a.get("name")
        ]

    writers = []
    if film_data.get("writers"):
        writers = [
            {"id": str(w["id"]), "name": str(w["name"])}
            for w in film_data["writers"]
            if w and w.get("id") and w.get("name")
        ]

    # Формируем документ Elasticsearch по схеме
    document = {
        "id": doc_id,
        "title": title,
        "description": description,
        "genres": genres,
        "imdb_rating": imdb_rating,
        "directors_names": directors_names,
        "actors_names": actors_names,
        "writers_names": writers_names,
        "directors": directors,
        "actors": actors,
        "writers": writers,
    }

    return document


def transform_batch(films_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Преобразуем пакет записей фильмов в документы Elasticsearch.

    Обрабатывает список записей фильмов, преобразуя каждую в документ ES.
    В случае ошибок преобразования одной записи логирует ошибку и продолжает
    обработку остальных записей.

    Args:
        films_data: Список словарей с данными фильмов из PostgreSQL

    Returns:
        Список документов для индексации в Elasticsearch
    """
    documents = []
    for film in films_data:
        try:
            doc = transform_film_to_document(film)
            documents.append(doc)
        except Exception as e:
            logger.error(f"Error transforming film {film.get('id')}: {e}")

    return documents


def transform_genre_to_document(genre_data: Dict[str, Any]) -> Dict[str, Any]:
    """Преобразуем запись жанра из PostgreSQL в документ Elasticsearch."""
    return {
        "id": str(genre_data.get("id")),
        "name": genre_data.get("name") or "",
        "description": genre_data.get("description") or "",
    }


def transform_genres_batch(
    genres_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Преобразуем пакет записей жанров в документы Elasticsearch.

    Обрабатывает список записей жанров, преобразуя каждую в документ ES.
    В случае ошибок преобразования одной записи логирует ошибку и продолжает
    обработку остальных записей.

    Args:
        genres_data: Список словарей с данными жанров из PostgreSQL

    Returns:
        Список документов для индексации в Elasticsearch
    """
    documents = []
    for genre in genres_data:
        try:
            doc = transform_genre_to_document(genre)
            documents.append(doc)
        except Exception as e:
            logger.error(f"Error transforming genre {genre.get('id')}: {e}")

    return documents


def transform_person_to_document(
    person_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Преобразуем запись человека из PostgreSQL в документ Elasticsearch.

    Создает документ с информацией о человеке и списком фильмов,
    в которых он участвовал, включая роли.

    Args:
        person_data: Словарь с данными человека из PostgreSQL

    Returns:
        Документ для индексации в Elasticsearch
    """
    films = []
    for film in person_data.get("films") or []:
        film_id = film.get("id") or film.get("uuid")
        if not film_id:
            continue

        roles = [str(role) for role in (film.get("roles") or []) if role]
        films.append({
            "id": str(film_id),
            "roles": roles,
        })

    return {
        "id": str(person_data.get("id")),
        "full_name": person_data.get("full_name") or "",
        "films": films,
    }


def transform_persons_batch(
    persons_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Преобразуем пакет записей людей в документы Elasticsearch."""
    documents = []
    for person in persons_data:
        try:
            doc = transform_person_to_document(person)
            documents.append(doc)
        except Exception as e:
            logger.error(f"Error transforming person {person.get('id')}: {e}")

    return documents
