"""Проверки корневого эндпоинта FastAPI.

Содержит простой healthcheck, который должен возвращать статус ok.
"""


def test_root_healthcheck(client):
    """Проверяет, что `GET /` возвращает статус `ok`.

    Ожидаемый ответ: 200 и JSON {"status": "ok"}.

    Параметры
    ---------
    client: TestClient
        Фикстура тестового клиента FastAPI.

    Возвращает
    ---------
    None
    """
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
