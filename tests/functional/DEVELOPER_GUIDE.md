# Руководство для разработчиков тестов

Этот документ описывает внутреннее устройство функциональных тестов, правила расширения и практический workflow для разработчиков.

## 1. Назначение и границы

Функциональные тесты проверяют работу HTTP API FastAPI через внешние вызовы:

- валидация входных параметров запросов;
- работа пагинации;
- полнотекстовый поиск фильмов;
- получение жанров и персон;
- корректная работа кеша Redis;
- интеграция с Elasticsearch.

Тесты не проверяют внутреннюю логику сервисов — они делают HTTP-запросы к работающему FastAPI-сервису и проверяют ответы.

## 2. Архитектура тестов

### 2.1 Слои тестов

- `conftest.py` — общие фикстуры и утилиты для Elasticsearch, Redis и aiohttp.
- `settings.py` — конфигурация окружения через переменные окружения.
- `src/test_*.py` — сами тесты для каждого API-роута.
- `testdata/es_mapping.py` — маппинги индексов Elasticsearch для тестов.
- `utils/test_data.py` — вспомогательные утилиты для генерации тестовых данных.

### 2.2 Фикстуры

Ключевые фикстуры:

- `event_loop` — отдельный цикл событий для сессии pytest.
- `es_client` — клиент AsyncElasticsearch для работы с Elasticsearch.
- `es_write_data` — функция для записи данных в Elasticsearch.
- `es_film_data`, `es_genre_data`, `es_person_data` — фабрики тестовых данных.
- `redis_client` — клиент Redis для проверки кеша.
- `http_session` — aiohttp.ClientSession для HTTP-запросов.

### 2.3 Утилиты

Утилиты вынесены в отдельный файл `utils/test_data.py`:

- `_generate_random_text(prefix, length)` — генерирует случайный текст с префиксом.
- `_prepare_bulk_actions(documents, index)` — формирует bulk-документы для Elasticsearch.
- `build_film_bulk_data(count, query_prefix)` — генерирует тестовые данные фильмов.
- `build_genre_bulk_data(count, query_prefix)` — генерирует тестовые данные жанров.
- `build_person_bulk_data(count, query_prefix)` — генерирует тестовые данные персон.
- `fetch_all_pages(session, url, params, page_size)` — загружает все страницы пагинации.
- `build_film_bulk_data(count, query_prefix)` — генерирует тестовые данные фильмов.
- `build_genre_bulk_data(count, query_prefix)` — генерирует тестовые данные жанров.
- `build_person_bulk_data(count, query_prefix)` — генерирует тестовые данные персон.
- `fetch_all_pages(session, url, params, page_size)` — загружает все страницы пагинации.

## 3. Локальный контур разработки

Из папки `tests/functional`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Подготовьте переменные окружения:

```bash
export SERVICE_URL=http://localhost:8000
export ELASTICSEARCH_HOST=localhost
export ELASTICSEARCH_PORT=9200
export ELASTICSEARCH_FILMS_INDEX=movies
export ELASTICSEARCH_GENRES_INDEX=genres
export ELASTICSEARCH_PERSONS_INDEX=persons
export ES_ID_FIELD=id
export ES_INDEX_MAPPING=/path/to/es_mapping.py
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

Запустите тесты:

```bash
PYTHONPATH=. pytest -q src
```

Для запуска конкретного файла:

```bash
PYTHONPATH=. pytest -q src/test_films.py
```

## 4. Запуск через Docker Compose

### 4.1 Стабильное окружение (CI)

Из корня проекта:

```bash
docker compose -f tests/functional/docker-compose.yml build --no-cache
docker compose -f tests/functional/docker-compose.yml run --rm test-runner pytest -v
```

Контейнеры:
- `elasticsearch` — Elasticsearch 8.6.2
- `redis` — Redis 7-alpine
- `fastapi` — сервис из `fastapi/`
- `test-runner` — контейнер для запуска pytest

### 4.2 Разработка и отладка

Из папки `tests/functional`:

```bash
docker compose -f docker-compose-dev.yml build --no-cache
docker compose -f docker-compose-dev.yml run --rm test-runner pytest -v
```

Отличия `docker-compose-dev.yml`:
- монтирует исходный код (`.` → `/app`);
- позволяет редактировать тесты локально без пересборки контейнера;
- удобен для интерактивной отладки.

### 4.3 Запуск с выводом в консоль

Для просмотра подробного вывода результатов тестирования:

```bash
docker compose -f tests/functional/docker-compose.yml run --rm test-runner pytest -v
```

## 5. Конфигурация

Ключевые переменные окружения (см. `settings.py`):

- `SERVICE_URL` — URL FastAPI-сервиса (по умолчанию: `http://localhost:8000`)
- `ELASTICSEARCH_HOST` — хост Elasticsearch (по умолчанию: `localhost`)
- `ELASTICSEARCH_PORT` — порт Elasticsearch (по умолчанию: `9200`)
- `ELASTICSEARCH_FILMS_INDEX` — индекс фильмов (по умолчанию: `movies`)
- `ELASTICSEARCH_GENRES_INDEX` — индекс жанров (по умолчанию: `genres`)
- `ELASTICSEARCH_PERSONS_INDEX` — индекс персон (по умолчанию: `persons`)
- `ES_ID_FIELD` — поле ID в Elasticsearch (по умолчанию: `id`)
- `ES_INDEX_MAPPING` — путь к файлу маппинга (по умолчанию: `/app/testdata/es_mapping.py`)
- `REDIS_HOST` — хост Redis (по умолчанию: `localhost`)
- `REDIS_PORT` — порт Redis (по умолчанию: `6379`)

## 6. Добавление нового теста

Рекомендуемая последовательность:

1. Определите, какой эндпоинт тестируете (`test_films.py`, `test_genres.py`, `test_persons.py`, `test_films_search.py`).
2. Используйте существующие фикстуры (`es_client`, `http_session`, `redis_client`).
3. Подготовьте данные через `es_write_data` с нужным маппингом.
4. Сделайте HTTP-запрос через `http_session`.
5. Проверьте статус, тело ответа и побочные эффекты (кеш в Redis).
6. Добавьте тест в соответствующий файл.
### 6.1 Добавление новых утилит

Если нужно добавить новую утилиту для генерации тестовых данных:

1. Добавьте функцию в `utils/test_data.py`.
2. Экспортируйте её в `utils/__init__.py`.
3. Импортируйте в `conftest.py`, если она нужна в фикстурах.
### Пример теста

```python
@pytest.mark.asyncio
async def test_example_endpoint(es_test_data, http_session):
    """Проверяет базовый сценарий."""
    session = http_session
    async with session.get(
        test_settings.service_url + "/api/v1/endpoint",
        params={"param": "value"}
    ) as response:
        body = await response.json()
        status = response.status

    assert status == 200
    assert "field" in body
```

## 7. Правила и конвенции

- Используйте `pytest.mark.asyncio` для асинхронных тестов.
- Используйте `http_session` для всех HTTP-запросов.
- Используйте `es_write_data` для подготовки данных в Elasticsearch.
- Проверяйте статус ответа и тело ответа.
- Проверяйте кеширование через `redis_client`.
- Используйте `build_film_bulk_data`, `build_genre_bulk_data`, `build_person_bulk_data` для генерации тестовых данных.
- Импортируйте утилиты из `utils/test_data.py` или `utils/__init__.py`.

## 8. Диагностика

- `ContentTypeError: Attempt to decode JSON with unexpected mimetype: text/plain` — FastAPI вернул ошибку (500), а не JSON. Проверьте логи FastAPI.
- `Connection refused` — Elasticsearch или Redis недоступны. Проверьте статус контейнеров.
- `IndexNotFoundError` — индекс не создан. Убедитесь, что `es_write_data` вызван с правильным маппингом.
- `Redis connection error` — Redis недоступен. Проверьте статус контейнера и переменные окружения.

## 9. Особенности реализации

- Тесты используют `aiohttp.ClientSession` для HTTP-запросов.
- Elasticsearch-клиент использует `AsyncElasticsearch`.
- Redis-клиент использует `redis.asyncio.Redis`.
- Тестовые данные генерируются с помощью `random` и `uuid` в модуле `utils/test_data.py`.
- Каждый тест очищает Redis перед запуском (`redis_client` с `scope="function"`).

## 10. Запуск тестов

### Запуск всех тестов

```bash
PYTHONPATH=. pytest -q src
```

### Запуск конкретного файла

```bash
PYTHONPATH=. pytest -q src/test_films.py
```

### Запуск конкретного теста

```bash
PYTHONPATH=. pytest -q src/test_films.py::test_films_validation_sort
```

### Запуск с подробным выводом

```bash
PYTHONPATH=. pytest -v src
```

## 11. Точки входа для отладки

Если что-то не работает, проверьте:

- `conftest.py` — фикстуры и утилиты;
- `settings.py` — переменные окружения;
- `testdata/es_mapping.py` — маппинги индексов;- `utils/test_data.py` — утилиты для генерации тестовых данных;- логи FastAPI-сервиса;
- логи Elasticsearch и Redis.
