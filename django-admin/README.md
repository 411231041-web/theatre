# django-admin

`django-admin` — Django-приложение для администрирования и API проекта
Theatre. Внутри есть административная панель, модуль `movies` и JSON API,
доступный через `movies.api`.

## Возможности

- Админ-панель Django по адресу `/admin/`.
- API проекта по адресу `/api/`.
- Поддержка PostgreSQL.
- Конфигурация через `.env` и разбиение настроек на отдельные компоненты.
- Подготовка статики и переводов при запуске контейнера.

## Структура проекта

- `manage.py` — точка входа для команд Django.
- `config/settings.py` — сборка настроек через `split-settings`.
- `config/components/` — отдельные блоки настроек: база данных, шаблоны,
  middleware, логирование и т.д.
- `config/urls.py` — корневые маршруты проекта.
- `movies/` — основное приложение с моделями и API.

## Требования

- Python 3.10+
- PostgreSQL
- Зависимости из `requirements.txt`

## Переменные окружения

Минимальный набор переменных, которые используются в настройках:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `INTERNAL_IPS`
- `PROJECT_NAME`
- `PROJECT_DESCRIPTION`
- `SQL_ENGINE`
- `SQL_HOST`
- `SQL_PORT`
- `SQL_OPTIONS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

Если проект запускается через Docker Compose, эти значения обычно
передаются через файл `.env` в корне репозитория.

## Локальный запуск

1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. Подготовьте переменные окружения.
4. Выполните миграции:

   ```bash
   python manage.py migrate
   ```

5. Соберите статические файлы и переводы, если нужно:

   ```bash
   python manage.py compilemessages
   python manage.py collectstatic --noinput
   ```

6. Запустите сервер разработки:

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

## Запуск через Docker

В корне репозитория используется `docker-compose.yml`. Django-приложение
собирается из каталога `django-admin`, а полный стек поднимается вместе
с PostgreSQL, Nginx, Elasticsearch, Redis и ETL-сервисами.

Пример запуска:

```bash
docker compose up --build
```

После старта админка будет доступна через Nginx, а сам Django-контейнер
выполнит миграции, `compilemessages` и `collectstatic` автоматически.

## Полезные команды

- `python manage.py createsuperuser`
- `python manage.py makemigrations`
- `python manage.py migrate`
- `python manage.py test`

## Маршруты

- `/admin/` — Django admin
- `/api/` — API приложения `movies`

## Примечание

Стартовый скрипт контейнера выполняет:

- миграции базы данных,
- компиляцию переводов,
- сборку статических файлов,
- запуск `uwsgi`.
