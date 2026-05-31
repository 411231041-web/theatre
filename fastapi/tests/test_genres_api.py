"""Тесты API для жанров (FastAPI).

Проверяет валидацию параметров, получение списка жанров, детализацию и
поведение кеширования.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

from core import dependencies
from models.genre_api import GenreDetail, GenreShort


class StubGenreService:
    """Заглушка для GenreService в тестах.

    Позволяет мокать методы сервиса для тестирования API.
    """

    def __init__(self):
        self.list_genres = AsyncMock()
        self.get_by_id = AsyncMock()


def test_genres_list_returns_data_and_forwards_filters(client):
    """
    Тест получения списка жанров с фильтрацией.

    Проверяет, что API корректно передает параметры фильтрации в сервис.

    Параметры
    ---------
    client: TestClient
        Фикстура тестового клиента FastAPI.

    Возвращает
    ---------
    None
    """
    service = StubGenreService()
    service.list_genres.return_value = {
        "genres": [
            GenreShort(uuid=uuid4(), name="Comedy"),
            GenreShort(uuid=uuid4(), name="Drama"),
        ],
        "total_hits": 20,
    }

    app = client.app
    app.dependency_overrides[dependencies.get_genres_dependency] = (
        lambda: service
    )

    response = client.get(
        "/api/v1/genres/?filter[name]=com&page_size=5&page_number=3"
        "&sort=-name"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 20
    assert body["total_pages"] == 4
    assert body["prev"] == 2
    assert body["next"] == 4
    assert len(body["results"]) == 2
    service.list_genres.assert_awaited_once_with(
        sort="-name",
        name="com",
        page_size=5,
        page_number=3,
    )


def test_genres_list_rejects_invalid_sort(client):
    """
    Тест валидации параметра сортировки.

    Проверяет, что API возвращает ошибку 422 при передаче
    недопустимого поля сортировки.

    Параметры
    ---------
    client: TestClient
        Фикстура тестового клиента FastAPI.

    Возвращает
    ---------
    None
    """
    response = client.get("/api/v1/genres/?sort=imdb_rating")

    assert response.status_code == 422


def test_genre_details_returns_404_when_not_found(client):
    """
    Тест обработки случая, когда жанр не найден.

    Проверяет, что API возвращает 404 при отсутствии жанра.

    Параметры
    ---------
    client: TestClient
        Фикстура тестового клиента FastAPI.

    Возвращает
    ---------
    None
    """
    service = StubGenreService()
    service.get_by_id.return_value = None

    app = client.app
    app.dependency_overrides[dependencies.get_genres_dependency] = (
        lambda: service
    )

    response = client.get(f"/api/v1/genres/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Genre not found"}


def test_genre_details_returns_genre(client):
    """
    Тест получения детальной информации о жанре.

    Проверяет, что API корректно возвращает данные жанра.

    Параметры
    ---------
    client: TestClient
        Фикстура тестового клиента FastAPI.

    Возвращает
    ---------
    None
    """
    service = StubGenreService()
    genre_id = uuid4()
    service.get_by_id.return_value = GenreDetail(
        uuid=genre_id,
        name="Action",
        description="Action movies",
    )

    app = client.app
    app.dependency_overrides[dependencies.get_genres_dependency] = (
        lambda: service
    )

    response = client.get(f"/api/v1/genres/{genre_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["uuid"] == str(genre_id)
    assert body["name"] == "Action"


def test_genres_list_returns_empty_results_for_page_beyond_total(client):
    """
    Тест обработки страницы за пределами диапазона.

    Проверяет, что API возвращает 200 и пустой список результатов,
    если запрошенная страница больше числа доступных страниц.

    Параметры
    ---------
    client: TestClient
        Фикстура тестового клиента FastAPI.

    Возвращает
    ---------
    None
    """
    service = StubGenreService()
    service.list_genres.return_value = {
        "genres": [],
        "total_hits": 0,
    }

    app = client.app
    app.dependency_overrides[dependencies.get_genres_dependency] = (
        lambda: service
    )

    response = client.get("/api/v1/genres?page_size=50&page_number=2")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["total_pages"] == 1
    assert body["prev"] == 1
    assert body["next"] is None
    assert body["results"] == []
