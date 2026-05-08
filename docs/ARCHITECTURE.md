# Архитектура проекта — кратко

Общая схема:

- Источник данных: PostgreSQL (основная БД).
- ETL-процессы читают из PostgreSQL и индексируют данные в Elasticsearch.
- FastAPI предоставляет API поверх Elasticsearch (чтение, поиск, пагинация).
- Django используется для административных задач и управления данными.
- Nginx (конфигурация в `nginx.conf`) выступает как обратный прокси/статические файлы.

Потоки данных:

1. Записи создаются/обновляются в PostgreSQL (например, через Django или миграции).
2. ETL считывает изменения и обновляет индексы в Elasticsearch.
3. FastAPI выполняет поисковые запросы к Elasticsearch и возвращает результаты клиентам.

Коммуникация и зависимости:

- FastAPI → Elasticsearch (read-only для API сервиса).
- ETL → PostgreSQL (read) и → Elasticsearch (write).
- Django → PostgreSQL (read/write).

Где смотреть код:
- API: `fastapi/src/` — маршруты, сервисы, модели.
- ETL: `etl/` — загрузчики, настройки индексов.
- Админ: `django-admin/`.
