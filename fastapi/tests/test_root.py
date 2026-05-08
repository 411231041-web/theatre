def test_root_healthcheck(client):
    """
    Тест проверки работоспособности корневого endpoint.

    Проверяет, что API возвращает статус "ok" при обращении к корню.
    """
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
