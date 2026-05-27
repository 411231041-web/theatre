# Setup / Локальная настройка

Этот документ даёт более детальные шаги для разворачивания проекта локально и с Docker.

1) Использование Docker Compose (рекомендуется)

- Собрать и запустить все сервисы:

```bash
docker compose up -d --build
```

- Остановить и удалить контейнеры:

```bash
docker compose down
```

2) Локальная разработка (по компонентам)

- FastAPI:

  - Установите зависимости: `pip install -r fastapi/requirements.txt`.
  - Запустите: `uvicorn fastapi.src.main:app --reload --port 8001`.
  - Документация OpenAPI доступна по адресу: `http://localhost:8001/api/openapi`.
  - JSON-схема OpenAPI доступна по адресу: `http://localhost:8001/api/openapi.json`.

- Django (админ):

  - Перейдите в папку `django-admin/`.
  - Установите зависимости (если есть `requirements.txt`).
  - Выполните миграции: `python manage.py migrate`.
  - Запустите сервер: `python manage.py runserver`.

- ETL (перенос данных в Elasticsearch):

  - Установите зависимости: `pip install -r etl/requirements.txt`.
  - Проверьте настройки подключения в `etl/config.py`.
  - Запустите нужный модуль (например, для фильмов):

```bash
python -m etl.postgres_to_es.films_main
```

3) Тестирование

- Запуск тестов FastAPI:

```bash
cd fastapi
python -m pytest -q
```

4) Полезные советы

- Внимательно проверяйте переменные окружения и настройки подключения к PostgreSQL/Elasticsearch.
- Если используете Docker, убедитесь, что сервисы БД и ES подняты до запуска ETL или API.
