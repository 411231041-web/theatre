from unittest.mock import AsyncMock
from uuid import uuid4

from src.api.v1 import films as films_api
from src.models.film_api import FilmDetail, FilmShort


class StubFilmService:
    """
    Заглушка для FilmService в тестах.

    Позволяет мокать методы сервиса для тестирования API.
    """

    def __init__(self):
        self.list_films = AsyncMock()
        self.get_by_id = AsyncMock()


def test_films_list_returns_data_and_forwards_filters(client):
    """
    Тест получения списка фильмов с фильтрацией.

    Проверяет, что API корректно передает параметры фильтрации в сервис.
    """
    service = StubFilmService()
    service.list_films.return_value = [
        FilmShort(uuid=uuid4(), title="Film 1", imdb_rating=8.0),
        FilmShort(uuid=uuid4(), title="Film 2", imdb_rating=7.4),
    ]

    app = client.app
    app.dependency_overrides[films_api.get_service] = lambda: service

    response = client.get(
        "/api/v1/films/"
        "?filter[genre]=comedy"
        "&page_size=5&page_number=2"
        "&sort=imdb_rating"
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    service.list_films.assert_awaited_once_with(
        page_size=5,
        page_number=2,
        sort="imdb_rating",
        genre="comedy",
    )


def test_films_list_rejects_invalid_sort(client):
    """
    Тест валидации параметра сортировки.

    Проверяет, что API возвращает ошибку 422 при передаче недопустимого поля сортировки.
    """
    response = client.get("/api/v1/films/?sort=title")

    assert response.status_code == 422


def test_film_details_returns_404_when_not_found(client):
    """
    Тест обработки случая, когда фильм не найден.

    Проверяет, что API возвращает 404 при отсутствии фильма.
    """
    service = StubFilmService()
    service.get_by_id.return_value = None

    app = client.app
    app.dependency_overrides[films_api.get_service] = lambda: service

    response = client.get(f"/api/v1/films/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Film not found"}


def test_film_details_returns_film(client):
    """
    Тест получения детальной информации о фильме.

    Проверяет, что API корректно возвращает данные фильма.
    """
    service = StubFilmService()
    film_id = uuid4()
    service.get_by_id.return_value = FilmDetail(
        uuid=film_id,
        title="Test film",
        imdb_rating=8.5,
        description="Description",
        genre=[],
        actors=[],
        writers=[],
        directors=[],
    )

    app = client.app
    app.dependency_overrides[films_api.get_service] = lambda: service

    response = client.get(f"/api/v1/films/{film_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["uuid"] == str(film_id)
    assert body["title"] == "Test film"
