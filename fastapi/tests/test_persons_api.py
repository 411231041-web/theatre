from unittest.mock import AsyncMock
from uuid import uuid4

from src.api.v1 import persons as persons_api
from src.models.person_api import PersonDetail, PersonSearchResult


class StubPersonService:
    """
    Заглушка для PersonService в тестах.

    Позволяет мокать методы сервиса для тестирования API.
    """

    def __init__(self):
        self.search_persons = AsyncMock()
        self.get_by_id = AsyncMock()
        self.get_films_by_person = AsyncMock()


def test_persons_search_returns_data_and_forwards_filters(client):
    """
    Тест поиска персон с фильтрацией.

    Проверяет, что API корректно передает параметры фильтрации в сервис.
    """
    service = StubPersonService()
    service.search_persons.return_value = [
        PersonSearchResult(uuid=uuid4(), full_name="George", films=[]),
    ]

    app = client.app
    app.dependency_overrides[persons_api.get_service] = lambda: service

    response = client.get(
        "/api/v1/persons/search"
        "?query=geo&filter[role]=actor"
        "&page_size=5&page_number=2"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    service.search_persons.assert_awaited_once_with(
        query="geo",
        sort="full_name",
        role="actor",
        page_size=5,
        page_number=2,
    )


def test_persons_search_rejects_empty_query(client):
    """
    Тест валидации поискового запроса.

    Проверяет, что API возвращает ошибку 422 при передаче пустого запроса.
    """
    response = client.get("/api/v1/persons/search?query=")

    assert response.status_code == 422


def test_person_details_returns_404_when_not_found(client):
    """
    Тест обработки случая, когда персона не найдена.

    Проверяет, что API возвращает 404 при отсутствии персоны.
    """
    service = StubPersonService()
    service.get_by_id.return_value = None

    app = client.app
    app.dependency_overrides[persons_api.get_service] = lambda: service

    response = client.get(f"/api/v1/persons/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Person not found"}


def test_person_details_returns_person(client):
    """
    Тест получения детальной информации о персоне.

    Проверяет, что API корректно возвращает данные персоны.
    """
    service = StubPersonService()
    person_id = uuid4()
    service.get_by_id.return_value = PersonDetail(
        uuid=person_id,
        full_name="George Name",
        films=[{"uuid": uuid4(), "roles": ["actor"]}],
    )

    app = client.app
    app.dependency_overrides[persons_api.get_service] = lambda: service

    response = client.get(f"/api/v1/persons/{person_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["uuid"] == str(person_id)
    assert body["full_name"] == "George Name"


def test_person_films_returns_404_when_no_films(client):
    """
    Тест обработки случая, когда у персоны нет фильмов.

    Проверяет, что API возвращает 404 при отсутствии фильмов у персоны.
    """
    service = StubPersonService()
    service.get_films_by_person.return_value = []

    app = client.app
    app.dependency_overrides[persons_api.get_service] = lambda: service

    response = client.get(f"/api/v1/persons/{uuid4()}/film")

    assert response.status_code == 404
    assert response.json() == {"detail": "Person not found or has no films"}


def test_person_films_returns_data(client):
    """
    Тест получения фильмов персоны.

    Проверяет, что API корректно возвращает список фильмов персоны.
    """
    service = StubPersonService()
    person_id = uuid4()
    service.get_films_by_person.return_value = [
        {"id": str(uuid4()), "roles": ["writer"]},
    ]

    app = client.app
    app.dependency_overrides[persons_api.get_service] = lambda: service

    response = client.get(
        f"/api/v1/persons/{person_id}/film?page_size=3&page_number=4"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    service.get_films_by_person.assert_awaited_once_with(
        person_id=person_id,
        page_size=3,
        page_number=4,
    )
