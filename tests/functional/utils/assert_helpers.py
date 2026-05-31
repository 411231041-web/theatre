"""Утилитарные вспомогательные функции для функциональных тестов.

Модуль содержит проверки-ассерты для типичных ответов API и
вспомогательные функции для работы с aiohttp-ответами в тестах.
"""

import json
from typing import Any, Tuple


def get_helper_message() -> str:
    """Возвращает тестовое сообщение-шеймер.

    Используется в простых юнит-тестах как заглушка.
    """

    return "helper"


def assert_validation_error_status(
    status: int,
    status_expected: int,
    detail: dict | None = None,
) -> None:
    """Проверяет HTTP-статус ответа и присутствие поля `detail`.

    Параметры
    ---------
    status: int
        Фактический HTTP-статус ответа.
    status_expected: int
        Ожидаемый HTTP-статус.
    detail: dict | None
        Объект детали ошибки (обычно `body['detail'][0]`).

    Возвращает
    ---------
    None

    Исключения
    ----------
    AssertionError
        Выбрасывается, если статус не совпадает или отсутствует `detail`.
    """
    assert status == status_expected, (
        f"Ожидается статус {status_expected}, получен {status}"
    )
    assert detail is not None, "Отсутствует detail в ответе"


def assert_validation_error_type(
    detail: dict,
    type_prefix: str | list[str] | None = None,
) -> None:
    """Проверяет значение поля `type` в объекте детали ошибки.

    Параметры
    ---------
    detail: dict
        Словарь с деталями ошибки (как в ответе FastAPI).
    type_prefix: str | list[str] | None
        Ожидаемый префикс строки в поле `type` или список префиксов.
        Если `None`, проверка пропускается.

    Возвращает
    ---------
    None

    Исключения
    ----------
    AssertionError
        Выбрасывается, если поле `type` не начинается ни с одного из
        ожидаемых префиксов.
    """
    if type_prefix is None:
        return

    error_type = detail.get('type', '')
    prefixes = (
        type_prefix if isinstance(type_prefix, list) else [type_prefix]
    )
    assert any(
        error_type.startswith(p) for p in prefixes
    ), (
        f"Тип ошибки '{error_type}' не начинается с "
        f"{prefixes}"
    )


def assert_validation_error_location(
    detail: dict,
    loc_contains: str | None = None,
) -> None:
    """Проверяет содержимое поля `loc` в объекте детали ошибки.

    Поддерживает точное сравнение при передаче JSON-строки списка
    или проверку вхождения после нормализации пробелов.

    Параметры
    ---------
    detail: dict
        Словарь с деталями ошибки.
    loc_contains: str | None
        Ожидаемая подстрока или JSON-строка списка локации. Если
        `None`, проверка пропускается.

    Возвращает
    ---------
    None

    Исключения
    ----------
    AssertionError
        Выбрасывается, если `loc` не содержит ожидаемую подстроку или
        не равняется ожидаемому списку.
    """
    if loc_contains is None:
        return

    loc = detail.get('loc', [])
    # Если ожидаемая локация задана в виде JSON-списка, распарсим её
    # и сравним списки строго. Иначе — проводим упрощённую проверку
    # по вхождению с нормализацией пробелов.
    if isinstance(loc_contains, str) and loc_contains.startswith("["):
        try:
            expected_loc = json.loads(loc_contains)
        except Exception:
            expected_loc = None

        if expected_loc is not None:
            assert (
                loc == expected_loc
            ), f"Ожидается локация {expected_loc}, получена {loc}"
        else:
            loc_str = json.dumps(loc)
            if loc_contains.replace(" ", "") not in loc_str.replace(
                " ", ""
            ):
                raise AssertionError(
                    f"Строка '{loc_contains}' не найдена в локации: {loc_str}"
                )
    else:
        loc_str = json.dumps(loc)
        if loc_contains.replace(" ", "") not in loc_str.replace(
            " ", ""
        ):
            raise AssertionError(
                f"Строка '{loc_contains}' не найдена в локации: {loc_str}"
            )


def assert_validation_error_context(
    detail: dict,
    ctx_contains: dict | list[dict] | None = None,
) -> None:
    """Проверяет поле `ctx` (контекст) в объекте детали ошибки.

    Поддерживает передачу либо одного словаря с ожидаемыми полями, либо
    списка альтернатив — достаточно, чтобы хотя бы один словарь совпал.

    Параметры
    ---------
    detail: dict
        Словарь с деталями ошибки.
    ctx_contains: dict | list[dict] | None
        Ожидаемый контекст или список возможных контекстов. Если
        `None`, проверка пропускается.

    Возвращает
    ---------
    None

    Исключения
    ----------
    AssertionError
        Выбрасывается, если контекст не содержит ожидаемых полей/значений
        или ни одна из альтернатив не совпадает.
    """
    if ctx_contains is None:
        return

    ctx = detail.get('ctx', {})

    # Если передается список словарей — это альтернативы (OR):
    # достаточно, чтобы хотя бы один словарь полностью совпал.
    if isinstance(ctx_contains, list):
        for expected_ctx in ctx_contains:
            match = True
            for key, expected_value in expected_ctx.items():
                if key not in ctx or ctx.get(key) != expected_value:
                    match = False
                    break
            if match:
                return
        raise AssertionError(
            f"Ни один из ожидаемых контекстов {ctx_contains} "
            f"не найден в: {ctx}"
        )

    # Обычное сравнение для одного словаря.
    if isinstance(ctx_contains, dict):
        for key, expected_value in ctx_contains.items():
            actual_value = ctx.get(key)
            assert key in ctx, (
                f"Ключ '{key}' отсутствует в контексте: {ctx}"
            )
            assert actual_value == expected_value, (
                f"Значение для '{key}': ожидается {expected_value}, "
                f"получено {actual_value}"
            )


def assert_body_length(
    body: list | dict,
    expected_length: int | None,
) -> None:
    """Проверяет длину ответа (для списков или словарей).

    Краткое описание
    -----------------
    Проверяет, что в ответе API количество элементов соответствует
    ожидаемому значению. Для списков проверяется число элементов,
    для пагинированного ответа — длина поля results.

    Параметры
    ---------
    body: list | dict
        Тело ответа API — список объектов или словарь. Если значение
        `expected_length` равно `None`, проверка пропускается.
    expected_length: int | None
        Ожидаемая длина. Если `None`, функция ничего не проверяет.

    Возвращаемое значение
    ---------------------
    None
        Функция использует assert и ничего не возвращает при успехе.

    Исключения
    ----------
    AssertionError
        Выкидывается, если передан неподдерживаемый тип `body` или
        если фактическая длина не совпадает с `expected_length`.
    """
    if expected_length is None:
        return

    if isinstance(body, list):
        actual = len(body)
    elif isinstance(body, dict):
        results = body.get("results")
        if isinstance(results, list):
            actual = len(results)
        else:
            actual = len(body)
    else:
        raise AssertionError(f"Неподдерживаемый тип body: {type(body)}")

    assert actual == expected_length, (
        f"Ожидается длина {expected_length}, получена {actual}"
    )


def assert_body_item(
    body: list | dict,
    expected_item: dict | None,
) -> None:
    """Проверяет наличие и типы полей в элементе(ах) ответа.

    Параметры
    ---------
    body: list | dict
        Тело ответа — список объектов или одиночный словарь.
    expected_item: dict | None
        Ожидаемая структура: ключи и соответствующие типы значений.
        Если `None`, проверка пропускается.

    Возвращает
    ---------
    None

    Исключения
    ----------
    AssertionError
        Выбрасывается, если отсутствует ожидаемое поле или тип значения
        не соответствует ожидаемому типу.
    """
    if expected_item is None:
        return

    if isinstance(body, dict) and isinstance(body.get("results"), list):
        items = body["results"]
    else:
        items = body if isinstance(body, list) else [body]

    for item in items:
        for key, expected_type in expected_item.items():
            assert key in item, (
                f"Поле '{key}' отсутствует в элементе: {item}"
            )
            if (expected_type is not None
                    and not isinstance(item[key], expected_type)):
                raise AssertionError(
                    f"Поле '{key}' ожидалось типа {expected_type}, "
                    f"получено {type(item[key])} в элементе: {item}"
                )


def assert_uuid_equal(actual: str | None, expected: str | None) -> None:
    """Проверяет соответствие UUID при наличии ожидаемого значения.

    Параметры
    ---------
    actual: str | None
        Фактическое значение поля `uuid` из ответа.
    expected: str | None
        Ожидаемое значение. Если `None`, проверка пропускается.

    Возвращает
    ---------
    None

    Исключения
    ----------
    AssertionError
        Выбрасывается, если `expected` задан и `actual` не равен ему.
    """
    if expected is None:
        return
    assert actual == expected, (
        f"UUID ожидался {expected}, получен {actual}"
    )


def assert_field_equal(actual: str | None, expected: str | None) -> None:
    """Проверяет равенство текстового поля при наличии ожидаемого значения.

    Параметры
    ---------
    actual: str | None
        Фактическое значение поля из ответа.
    expected: str | None
        Ожидаемое значение. Если `None`, проверка пропускается.

    Возвращает
    ---------
    None

    Исключения
    ----------
    AssertionError
        Выбрасывается, если `expected` задан и `actual` не равен ему.
    """
    if expected is None:
        return
    assert actual == expected, (
        f"Поле ожидалось '{expected}', получено '{actual}'"
    )


async def get_json(response: Any) -> Tuple[int, dict | list]:
    """Получает статус и JSON-тело из ответа API.

    Упрощает повторяющийся паттерн:
        async with session.get(...) as response:
            body = await response.json()
            status = response.status

    Параметры
    ---------
    response: Any
        Объект ответа от aiohttp или контекстный менеджер запроса.

    Возвращает
    ---------
    tuple[int, dict | list]
        Кортеж `(status_code, тело_ответа)`.
    """
    # Поддерживаем передачу контекстного менеджера от aiohttp,
    # например `session.get(...)`.
    if hasattr(response, "__aenter__"):
        async with response as resp:
            body = await resp.json()
            return resp.status, body

    body = await response.json()
    return response.status, body


def assert_items_have_fields(
    items: list[dict],
    required_fields: list[str],
) -> None:
    """Проверяет, что каждый элемент списка содержит указанные поля.

    Параметры
    ---------
    items: list[dict]
        Список словарей (элементы ответа API).
    required_fields: list[str]
        Список обязательных ключей для каждого элемента.

    Возвращает
    ---------
    None

    Исключения
    ----------
    AssertionError
        Выбрасывается, если хотя бы один элемент не содержит требуемый
        ключ.
    """
    for item in items:
        for field in required_fields:
            assert field in item, (
                f"Поле '{field}' отсутствует в элементе: {item}"
            )
