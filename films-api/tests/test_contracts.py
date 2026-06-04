from src.main import app


def test_api_routes_response_model_matches_return_annotation():
    """
    Проверяет, что у роутов API `response_model` соответствует
    аннотации `return` у обработчика.
    """
    mismatches = []
    for route in app.routes:
        # Импровизированный фильтр на маршруты v1
        if not getattr(route, "path", "").startswith("/api/v1"):
            continue
        resp = getattr(route, "response_model", None)
        handler = getattr(route, "endpoint", None)
        if resp is None or handler is None:
            continue
        ann = getattr(handler, "__annotations__", {}).get("return")
        if ann is None:
            continue
        # Простая проверка: строковое представление типов должно совпадать
        if str(resp) != str(ann):
            mismatches.append((route.path, route.name, resp, ann))

    assert (
        not mismatches
    ), f"Found response_model/return mismatches: {mismatches}"
