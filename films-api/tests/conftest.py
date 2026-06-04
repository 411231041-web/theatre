"""Фикстуры для тестов FastAPI.

Содержит фикстуру `client` для создания `TestClient` приложения и
очистки переопределений зависимостей после тестов.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from src.main import app

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Фикстура, создающая `TestClient` для приложения.

    Возвращает:
        TestClient: тестовый клиент FastAPI для выполнения запросов.
    """
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
