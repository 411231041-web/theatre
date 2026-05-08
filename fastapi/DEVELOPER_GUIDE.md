# Руководство для разработчиков FastAPI

Этот документ описывает внутреннее устройство сервиса и базовые практики для разработки.

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
- `src/api/v1/*` — HTTP слой (валидация query/path, коды ответов, DI).
- `src/services/*` — бизнес-логика, запросы в Elasticsearch, кэширование в Redis.
- `src/db/*` — ленивые singleton-клиенты Elasticsearch/Redis.
- `src/models/*` — Pydantic-модели API-ответов.
- `src/core/config.py` — конфигурация через environment variables.

Поток:
1. Роутер принимает запрос и валидирует параметры через FastAPI `Query`.
2. Роутер получает сервис через `Depends(get_service)`.
3. Сервис формирует cache key и сначала читает Redis.
4. При cache miss сервис обращается в Elasticsearch.
5. Ответ маппится в Pydantic-модель и кладется в Redis с TTL.
6. Роутер возвращает модель в JSON.

## 4. Конвенции API в проекте

- Версия API: префикс `/api/v1`.
- List-эндпоинты в проекте используют завершающий `/`:
  - `/api/v1/films/`
  - `/api/v1/genres/`
- Для фильтрации поддерживаются alias-параметры в стиле `filter[...]`:
  - `filter[genre]`, `filter[name]`, `filter[role]`
- Валидация сортировки задается regex-ограничениями (`pattern=...`) на уровне роутов.

## 5. Конфигурация

Ключевые переменные:
- `ELASTICSEARCH_HOST`, `ELASTICSEARCH_PORT`
- `ELASTICSEARCH_INDEX`
- `ELASTICSEARCH_GENRES_INDEX`
- `ELASTICSEARCH_PERSONS_INDEX`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `REDIS_CACHE_EXPIRE`

Значения по умолчанию определены в `src/core/config.py`.

## 6. Работа с Elasticsearch

Сервисы работают через `AsyncElasticsearch`:
- `get` для детального запроса по id;
- `search` для списков/поиска.

Текущие особенности запросов:
- Фильмы: сортировка по `imdb_rating`, фильтр по жанру через `term` на поле `genres`.
- Жанры: сортировка по `name.raw`, текстовый фильтр `match` по `name`.
- Персоны: `multi_match` по `full_name`, фильтр по роли через `nested` в `films.roles`, сортировка по `full_name.raw`.

## 7. Кэширование

Кэш-хелперы: `src/services/cache.py`.

Что важно:
- Ключ строится как SHA-256 от сериализованных параметров (`build_cache_key`).
- Для моделей используются:
  - `get_cached_model`/`set_cached_model`
  - `get_cached_models`/`set_cached_models`
- Для произвольного JSON (например, список фильмов персоны) используются:
  - `get_cached_json`/`set_cached_json`
- Ошибки Redis подавляются (fail-open): API продолжает работать без падения.

## 8. Добавление нового эндпоинта

Рекомендуемая последовательность:

1. Определить контракт ответа в `src/models/*_api.py`.
2. Добавить метод в соответствующий сервис (`src/services/*`):
   - cache key;
   - чтение из Redis;
   - запрос в Elasticsearch;
   - маппинг в модель;
   - запись в кэш.
3. Добавить роут в `src/api/v1/*`:
   - `response_model`;
   - валидация query/path;
   - `Depends(get_service)`;
   - корректные HTTP-ошибки (`404`, `422`).
4. Если это новый набор ресурсов, подключить роутер в `src/api/v1/router.py`.
5. Добавить тесты в `tests/`.

## 9. Тестирование

Запуск:

```bash
python -m pytest -q
```

Принцип тестов в проекте:
- HTTP-слой тестируется через `TestClient`.
- Сервисы мокируются через `AsyncMock`.
- Подмена зависимостей делается через `app.dependency_overrides`.

Пример паттерна:
- подменить `get_service` в конкретном роут-модуле;
- отправить HTTP-запрос;
- проверить status code, тело и вызов методов мока.

После теста overrides очищаются в фикстуре (`tests/conftest.py`).

## 10. Частые проблемы и диагностика

- `422 Unprocessable Entity`:
  - проверить `sort` и ограничения `pattern`;
  - проверить `page_size`/`page_number`.
- Пустой ответ при поиске:
  - убедиться, что ETL загрузил данные в нужный индекс.
- Медленные ответы:
  - проверить доступность Redis и значение `REDIS_CACHE_EXPIRE`.
- `404` на entity-by-id:
  - проверить наличие документа в Elasticsearch и корректность UUID.

## 11. Минимальные правила для изменений

- Сохранять разделение по слоям: роуты тонкие, логика в сервисах.
- Не дублировать код кэширования, использовать хелперы из `cache.py`.
- Для новых query-параметров сразу добавлять в cache key.
- Для изменений API обязательно добавлять/обновлять тесты.
