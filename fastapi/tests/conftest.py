from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """
    Фикстура для тестирования FastAPI приложения.

    Создает тестовый клиент для отправки HTTP запросов к приложению.

    Yields:
        TestClient: Тестовый клиент FastAPI.
    """
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
