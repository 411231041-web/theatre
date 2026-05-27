# Руководство для разработчиков FastAPI

Этот документ описывает внутреннее устройство сервиса и практики разработки.

## 1. Назначение и границы сервиса

FastAPI-приложение предоставляет read-only API поверх данных в Elasticsearch.
Redis используется как кэш, чтобы снизить нагрузку на Elasticsearch и ускорить ответы.

Сервис не пишет данные в PostgreSQL и Elasticsearch напрямую. Заполнение индексов выполняется ETL-пайплайнами проекта.

## 2. Локальный контур разработки

Из папки `fastapi`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

Полный контур (DB + ETL + Elasticsearch + Redis + FastAPI) поднимается из корня проекта:

```bash
docker compose up -d --build
```

## 3. Архитектура и поток запроса

Слои:
- `src/api/v1/*` — HTTP слой (валидация query/path, статусы, DI).
- `src/services/*` — бизнес-логика, запросы в Elasticsearch, кэширование в Redis.
- `src/db/*` — ленивые singleton-клиенты Elasticsearch/Redis.
- `src/models/*` — Pydantic-модели API-ответов.
- `src/core/config.py` — конфигурация через environment variables.

Дополнительные детали:
- `src/main.py` создает FastAPI-приложение, настраивает `docs_url` и `openapi_url`, `default_response_class=ORJSONResponse`, и закрывает клиентов в `lifespan`.
- `src/db/elasticsearch.py` и `src/db/redis.py` содержат глобальные клиенты, которые инициализируются один раз и закрываются при завершении.
- Конфигурация загружается через `get_settings()` и кэшируется `lru_cache`.

Поток:
1. Роутер принимает запрос и валидирует параметры через FastAPI `Query`.
2. Роутер получает сервис через `Depends(get_service)`.
3. Сервис формирует cache key и сначала читает Redis.
4. При cache miss сервис обращается в Elasticsearch.
5. Ответ маппится в Pydantic-модель и сохраняется в Redis с TTL.
6. Роутер возвращает данные клиенту.

## 4. Конвенции API

- Версия API: префикс `/api/v1`.
- Эндпоинты списка используют базовый путь без завершающего `/`:
  - `/api/v1/films`
  - `/api/v1/genres`
- У персон нет общего list-эндпоинта `/api/v1/persons`; вместо него используется `/api/v1/persons/search`.
- Для фильтрации поддерживаются alias-параметры `filter[...]`:
  - `filter[genre]`, `filter[name]`, `filter[role]`
- Параметры `sort` проверяются через `pattern` на уровне роутов.
- Поиск запросов требует `query` с минимум 1 символом.

## 5. API и правила запросов

### Films
- `GET /api/v1/films`
  - `sort`: `imdb_rating` или `-imdb_rating`
  - `title`: частичное совпадение по названию фильма
  - `genre` или `filter[genre]`
  - `page_size`: 1..100
  - `page_number`: >= 1
- `GET /api/v1/films/search`
  - `query`: строка, минимум 1 символ
  - `sort`: `imdb_rating` или `-imdb_rating`
  - `page_size`: 1..100
  - `page_number`: >= 1
- `GET /api/v1/films/{film_id}` — детальный просмотр.

### Genres
- `GET /api/v1/genres`
  - `sort`: `name` или `-name`
  - `name` или `filter[name]`
  - `page_size`: 1..100
  - `page_number`: >= 1
- `GET /api/v1/genres/{genre_id}` — детальный просмотр.

### Persons
- `GET /api/v1/persons/search`
  - `query`: строка поиска, минимум 1 символ
  - `sort`: `full_name` или `-full_name`
  - `role` или `filter[role]`
  - `page_size`: 1..100
  - `page_number`: >= 1
- `GET /api/v1/persons/{person_id}` — детальная информация о персоне.
- `GET /api/v1/persons/{person_id}/film` — фильмы по персоне, paged list.

## 6. Работа с Elasticsearch

Сервисы работают через `AsyncElasticsearch`.

Особенности:
- `FilmService`:
  - `get_by_id` получает фильм по UUID из индекса `movies`.
  - `list_films` строит запрос `match_phrase` для `title` и `term` для `genre`.
  - `search_films` ищет по `title` и `description` через `multi_match`.
- `GenreService`:
  - `get_by_id` и `list_genres` используют индекс `genres`.
  - фильтрация по `name` выполняется через `match`.
- `PersonService`:
  - `get_by_id` и `get_films_by_person` используют индекс `persons`.
  - `search_persons` ищет по `full_name` и фильтрует по роли через `nested` запрос.

## 7. Кэширование

Хелперы находятся в `src/services/cache.py`.

Основные функции:
- `build_cache_key(namespace, **params)` — SHA-256 ключ на основе параметров.
- `get_cached_model` / `set_cached_model` — кешируют одиночные Pydantic-модели.
- `get_cached_models` / `set_cached_models` — кешируют списки моделей.
- `get_cached_json` / `set_cached_json` — кешируют произвольный JSON.

Важно:
- Кэшируют как тело ответа, так и `total_hits`.
- Ошибки Redis подавляются: при сбое Redis API продолжает отдавать данные из Elasticsearch.

## 8. Конфигурация

Ключевые переменные:
- `ELASTICSEARCH_HOST`, `ELASTICSEARCH_PORT`
- `ELASTICSEARCH_FILMS_INDEX`
- `ELASTICSEARCH_GENRES_INDEX`
- `ELASTICSEARCH_PERSONS_INDEX`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `REDIS_CACHE_EXPIRE`

Дополнительно:
- `Settings` из `src/core/config.py` читает `.env` и игнорирует неизвестные переменные.
- `get_settings()` кэширует экземпляр конфигурации.
- `elasticsearch_url` и `redis_url` строятся автоматически.

## 9. Добавление нового эндпоинта

Рекомендуемая последовательность:
1. Определить Pydantic-модели ответа в `src/models/*_api.py`.
2. Реализовать бизнес-логику в сервисе `src/services/*`:
   - построить cache key;
   - читать из Redis;
   - обращаться в Elasticsearch;
   - маппить данные в модели;
   - сохранять результат в Redis.
3. Добавить роут в `src/api/v1/*`:
   - `response_model`;
   - валидацию query/path;
   - `Depends(get_service)`;
   - возвращать корректные `404`/`422`.
4. Если нужен новый ресурс, подключить роутер в `src/api/v1/router.py`.
5. Добавить тесты в `tests/`.

## 10. Тестирование

Запуск (из папки `fastapi`):

```bash
PYTHONPATH=src python -m pytest -q tests
```

Если вы уже активировали виртуальное окружение, можно использовать:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests
```

В проекте используется:
- `TestClient` для HTTP-слоя;
- `AsyncMock` для сервисов;
- `app.dependency_overrides` для подмены зависимостей.

После теста overrides очищаются в `tests/conftest.py`.

## 11. Диагностика

- `422 Unprocessable Entity`:
  - `sort` обязателен и проверяется шаблоном;
  - `page_size` ограничен 1..100;
  - `page_number` должен быть <= total pages.
- `404` для сущностей:
  - проверьте UUID и наличие документа в Elasticsearch.
- `empty search`:
  - убедитесь, что индекс загружен и данные доступны.
- `медленные ответы`:
  - проверьте Redis и настройки `REDIS_CACHE_EXPIRE`.

## 12. Особенности реализации

- `src/main.py` использует `ORJSONResponse` для быстрого JSON-сериализатора.
- `Docs` доступны по `/api/v1/openapi`.
- `PersonsService.get_films_by_person` возвращает список `dict` с фильмами и ролями,
  а не Pydantic-модель.
- `PersonService.search_persons` возвращает список `PersonSearchResult`,
  фильтруя роли по полю `films.roles`.
