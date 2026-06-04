# FastAPI сервис (Movies API)

Базовая документация для сервиса FastAPI в проекте theatre.

Документация для разработчиков:
- `DEVELOPER_GUIDE.md`

## Что это

Сервис предоставляет read-only API для данных о:
- фильмах;
- жанрах;
- персонах;
- фильмах, связанных с персоной.

Источник данных:
- Elasticsearch (индексы `movies`, `genres`, `persons`);
- Redis используется как кэш ответов.

## Структура

- `src/main.py` — создание приложения FastAPI и lifecycle (закрытие клиентов Elasticsearch/Redis).
- `src/api/v1/` — HTTP API (`films`, `genres`, `persons`).
- `src/services/` — бизнес-логика, работа с Elasticsearch и кэширование.
- `src/db/` — ленивые singleton-клиенты Elasticsearch и Redis.
- `src/core/config.py` — конфигурация через переменные окружения.
- `tests/` — API-тесты.

## Требования

- Python 3.12+
- Elasticsearch 8+
- Redis 7+

## Переменные окружения

Поддерживаются (см. `src/core/config.py`):

- `ELASTICSEARCH_HOST` (по умолчанию: `localhost`)
- `ELASTICSEARCH_PORT` (по умолчанию: `9200`)
- `ELASTICSEARCH_FILMS_INDEX` (по умолчанию: `movies`)
- `ELASTICSEARCH_GENRES_INDEX` (по умолчанию: `genres`)
- `ELASTICSEARCH_PERSONS_INDEX` (по умолчанию: `persons`)
- `REDIS_HOST` (по умолчанию: `localhost`)
- `REDIS_PORT` (по умолчанию: `6379`)
- `REDIS_DB` (по умолчанию: `0`)
- `REDIS_CACHE_EXPIRE` (по умолчанию: `300`, секунды)

## Запуск через Docker Compose (рекомендуется)

Из корня проекта:

```bash
docker compose up -d --build
```

FastAPI будет доступен по адресу:
- `http://localhost:8001`

Документация OpenAPI:
- `http://localhost:8001/api/v1/openapi`
- `http://localhost:8001/api/v1/openapi.json`

## Локальный запуск FastAPI

Из папки `films-api`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Пример минимального окружения:

```bash
export ELASTICSEARCH_HOST=localhost
export ELASTICSEARCH_PORT=9200
export ELASTICSEARCH_FILMS_INDEX=movies
export ELASTICSEARCH_GENRES_INDEX=genres
export ELASTICSEARCH_PERSONS_INDEX=persons
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
export REDIS_CACHE_EXPIRE=300
```

Запуск приложения:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

## API эндпоинты

Базовый префикс: `/api/v1`

### Root

- `GET /` — health-check, возвращает `{"status": "ok"}`.

### Films

- `GET /api/v1/films` — список фильмов.
  - Query-параметры:
    - `sort`: `imdb_rating` или `-imdb_rating`
    - `title`: поиск по части названия фильма
    - `page_size`: 1..100
    - `page_number`: >= 1
    - `genre` или `filter[genre]`
- `GET /api/v1/films/search` — полнотекстовый поиск фильмов.
  - Query-параметры:
    - `query`: строка поиска, минимум 1 символ
    - `sort`: `imdb_rating` или `-imdb_rating`
    - `page_size`: 1..100
    - `page_number`: >= 1
- `GET /api/v1/films/{film_id}` — детальная информация о фильме.

### Genres

- `GET /api/v1/genres` — список жанров.
  - Query-параметры:
    - `sort`: `name` или `-name`
    - `name` или `filter[name]`
    - `page_size`: 1..100
    - `page_number`: >= 1
- `GET /api/v1/genres/{genre_id}` — детальная информация о жанре.

### Persons

- `GET /api/v1/persons/search` — поиск персоналий.
  - Query-параметры:
    - `query`: строка поиска (минимум 1 символ)
    - `sort`: `full_name` или `-full_name`
    - `role` или `filter[role]`
    - `page_size`: 1..100
    - `page_number`: >= 1
- `GET /api/v1/persons/{person_id}` — детальная информация о персоне.
- `GET /api/v1/persons/{person_id}/film` — фильмы, связанные с персоной.
> У персон нет отдельного роута `/api/v1/persons` для общего списка; поиск осуществляется через `/api/v1/persons/search`.
## Примеры запросов

```bash
curl -i "http://localhost:8001/"
curl -i "http://localhost:8001/api/v1/films?page_size=5&page_number=1"
curl -i -g "http://localhost:8001/api/v1/films/search?query=matrix&page_size=5&page_number=1"
curl -i -g "http://localhost:8001/api/v1/persons/search?query=george&filter[role]=actor&page_size=5&page_number=1"
```

## Тесты

Из папки `films-api`:

```bash
PYTHONPATH=src python -m pytest -q tests
```

Если вы уже активировали виртуальное окружение, можно использовать:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests
```

Покрываются:
- root endpoint;
- API фильмов;
- API жанров;
- API персон.

## Примечания

- Эндпоинты списка доступны по URL без завершающего `/` (`/films`, `/genres`); запросы с завершающим слэшем могут редиректиться.
- Кэш реализован на уровне сервисов через Redis; при ошибках Redis запросы продолжают работать без падения API.
