# Тесты проекта Theatre

Это документация для тестового проекта `tests/` в репозитории Theatre.
Проект содержит функциональные проверки API FastAPI с использованием Elasticsearch и Redis.

## Что здесь находится

- `functional/` — основная папка с функциональными тестами.
- `functional/src/` — сами тесты для API:
  - `test_films.py`
  - `test_films_search.py`
  - `test_genres.py`
  - `test_persons.py`
- `functional/conftest.py` — общие фикстуры и утилиты для работы с Elasticsearch, Redis и aiohttp.
- `functional/settings.py` — конфигурация окружения тестов через переменные окружения.
- `functional/docker-compose.yml` — файл для запуска окружения с Elasticsearch, Redis, FastAPI и тестов в Docker.
- `functional/docker-compose-dev.yml` — файл для локальной разработки тестов и отладки.
- `functional/Dockerfile.test` — образ для запуска тестов в CI/стабильных окружениях.
- `functional/Dockerfile.test.dev` — образ для разработки и интерактивной отладки тестов.
- `functional/requirements.txt` — зависимости для запуска функциональных тестов.

## Цель

Проверить работу внешнего API FastAPI через HTTP:

- валидация входных параметров запросов;
- работа пагинации;
- полнотекстовый поиск фильмов;
- получение жанров и персон;
- корректная работа кеша Redis;
- интеграция с Elasticsearch.

## Требования

- Python 3.12+
- Docker и Docker Compose для запуска через контейнеры
- Elasticsearch 8.x (для локального запуска без Docker)
- Redis 7.x (для локального запуска без Docker)

## Запуск тестов через Docker

Перейдите в папку `tests/functional`:

```bash
cd tests/functional
```

Запустите весь тестовый стек:

```bash
docker compose up --build
```

или только запуск тестов (контейнеры создаются и запускаются автоматически):

```bash
docker compose up --build test-runner
```

Для запуска тестов с подробным выводом в консоль используйте:

```bash
docker compose run --rm test-runner pytest -v
```

Контейнер `test-runner` зависит от `elasticsearch`, `redis` и `fastapi`.

## Локальный запуск

1. Создайте виртуальное окружение и установите зависимости:

```bash
cd tests/functional
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Настройте переменные окружения.
   В `tests/functional/settings.py` используются следующие переменные:

- `ELASTICSEARCH_HOST`
- `ELASTICSEARCH_PORT`
- `ELASTICSEARCH_FILMS_INDEX`
- `ELASTICSEARCH_GENRES_INDEX`
- `ELASTICSEARCH_PERSONS_INDEX`
- `ES_ID_FIELD`
- `ES_INDEX_MAPPING`
- `REDIS_HOST`
- `REDIS_PORT`
- `SERVICE_URL`

Для запуска можно использовать файл окружения из корня проекта, если он есть:

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

3. Запустите тесты:

```bash
PYTHONPATH=. pytest -q src
```

## Обзор окружения Docker

- `elasticsearch` — Elasticsearch 8.6.2
- `redis` — Redis 7-alpine
- `fastapi` — сервис приложения из `fastapi/`
- `test-runner` — контейнер для запуска pytest

Параметры `docker-compose.yml` подключают `SERVICE_URL=http://fastapi:8000` и монтируют `PYTHONPATH=/app`.

## Как работать с тестами

- Общие фикстуры находятся в `functional/conftest.py`.
- Файлы `testdata/es_mapping.py` описывают маппинги индексов Elasticsearch для тестов.
- Тесты используют `aiohttp.ClientSession` для HTTP-запросов и `AsyncElasticsearch` для подготовки данных.

## Полезные команды

```bash
cd tests/functional
docker compose up --build
```

```bash
cd tests/functional
PYTHONPATH=. pytest -q src
```

```bash
cd tests/functional
pytest -q src/test_films.py
```

## Примечания

- Тесты ориентированы на функциональную проверку API, а не на юнит-тестирование бизнес-логики.
- В `docker-compose.yml` для тестов используется `../../.env` из корня проекта.
- Для корректной работы тестов необходимо, чтобы сервис FastAPI был доступен и отвечал на `SERVICE_URL`.
