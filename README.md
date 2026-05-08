# Theatre — project overview

Коротко: это проект для хранения и поиска данных о фильмах, жанрах и персонах.

Компоненты:
- `django-admin/` — административная часть и админ-интерфейс.
- `fastapi/` — публичное HTTP API (ASGI) для поиска и доступа к данным.
- `etl/` — перенос данных из PostgreSQL в Elasticsearch, настройки индексов.
- `docker-compose.yml` — локальная сборка и запуск базовых сервисов.

Быстрый старт (локально с Docker):

1. Запустить контейнеры:

```bash
docker compose up -d --build
```

2. Проверьте логи и доступность сервисов (пример):

```bash
curl -i http://localhost:8001/  # FastAPI (порт зависит от docker-compose)
```

Локальная разработка (без Docker):

1. Создайте виртуальное окружение и установите зависимости для нужного компонента, например для FastAPI:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r fastapi/requirements.txt
```

2. Запуск FastAPI для разработки:

```bash
uvicorn fastapi.src.main:app --reload --port 8001
```

3. Запуск Django (админ):

```bash
python django-admin/manage.py migrate
python django-admin/manage.py runserver
```

ETL (перенос данных в Elasticsearch):

ETL-скрипты находятся в папке `etl/`. Для запуска используйте соответствующие точки входа, например (в виртуальном окружении с зависимостями из `etl/requirements.txt`):

```bash
python -m etl.postgres_to_es.films_main
python -m etl.postgres_to_es.genres_main
python -m etl.postgres_to_es.persons_main
```

Тесты:

- FastAPI: выполнить из папки `fastapi/`:

```bash
python -m pytest -q
```

Конфигурация и среда:

- Общие настройки в `docker-compose.yml` и `nginx.conf`.
- Параметры окружения — смотреть в `django-admin/.env` (если есть) и переменные, которые использует `docker-compose`.

Структура репозитория (кратко):

- `django-admin/` — Django проект (админка, настройки).
- `fastapi/` — код API: `src/` (routes, services, models, tests).
- `etl/` — скрипты загрузки в Elasticsearch.
- `configs/`, `nginx.conf`, `docker-compose.yml` — инфраструктурные файлы.

Контрибьютинг:

- Открывайте pull request'ы в отдельной ветке.
- Пишите короткое описание изменений и добавляйте тесты для логики.

Полезные файлы:
- `docker-compose.yml` — старт окружения.
- `fastapi/pytest.ini` и `fastapi/tests/` — тесты API.

Если нужно, могу расширить документацию отдельными разделами: API reference, примеры запросов, CI/CD, подробный guide по разработке.
