# Руководство для разработчиков django-admin

Этот документ описывает устройство Django-части проекта Theatre, рабочие команды и правила изменения кода.

## 1. Назначение проекта

`django-admin` отвечает за административную часть проекта и HTTP API поверх модели `movies`.

Основные задачи:

- административная панель Django по адресу `/admin/`;
- API проекта по адресу `/api/`;
- хранение и редактирование данных о фильмах, жанрах и персонах;
- работа с PostgreSQL как с основным источником данных.

## 2. Архитектура проекта

Проект использует стандартный Django entrypoint и разбиение настроек на отдельные модули.

Ключевые точки:

- `manage.py` — запуск команд Django;
- `config/settings.py` — сборка настроек через `split-settings`;
- `config/components/` — отдельные блоки конфигурации;
- `config/urls.py` — корневые маршруты и настройка заголовков админки;
- `movies/` — доменная app с моделями, админкой, API и переводами.

## 3. Слои конфигурации

Настройки проекта собираются из нескольких файлов:

- `components/secret_env.py` — переменные окружения для имени проекта, описания, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`;
- `components/base.py` — базовые настройки языка, времени, `BASE_DIR` и `LOCALE_PATHS`;
- `components/logging.py` — логирование SQL-запросов при `SQL_DEBUG`;
- `components/installed_apps.py` — список `INSTALLED_APPS`;
- `components/middleware.py` — middleware, `ROOT_URLCONF`, `WSGI_APPLICATION`;
- `components/templates.py` — настройка шаблонов;
- `components/auth_validators.py` — валидаторы паролей;
- `components/database.py` — подключение к PostgreSQL;
- `components/static_and_paths.py` — static settings.

Файл `.env` читается из корня `django-admin`.

## 4. Доменные сущности

В приложении `movies` используются следующие модели:

- `Genre`;
- `Person`;
- `FilmWork`;
- `GenreFilmWork`;
- `PersonFilmWork`.

Связи и ограничения уже заложены в модели и миграции:

- many-to-many между фильмами и жанрами через `GenreFilmWork`;
- many-to-many между фильмами и персонами через `PersonFilmWork`;
- уникальные ограничения на связующих таблицах;
- индекс по `creation_date` и `rating` для `FilmWork`.

## 5. Админка

Админка настраивается в `movies/admin.py`.

Что важно:

- `Genre` и `Person` имеют поиск по имени;
- `FilmWork` отображает жанры через inline-таблицы;
- список фильмов сортируется и фильтруется через стандартный Django admin;
- для заголовков интерфейса используются `PROJECT_NAME` и `PROJECT_DESCRIPTION`.

## 6. API проекта

Маршрутизация строится так:

- `config/urls.py` подключает `/api/`;
- `movies/api/urls.py` подключает `movies.api.v1`;
- `movies/api/v1/urls.py` определяет версии и конечные маршруты.

Текущие endpoints:

- `GET /api/v1/info/`;
- `GET /api/v1/movies/`;
- `GET /api/v1/movies/<uuid:pk>/`.

Контроллеры реализованы через class-based views и используют агрегации PostgreSQL (`ArrayAgg`) для сборки списков жанров и персон.

## 7. Локальная разработка

Из папки `django-admin`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Далее подготовьте переменные окружения и выполните миграции:

```bash
python manage.py migrate
```

Полезные команды:

```bash
python manage.py createsuperuser
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py compilemessages
python manage.py test
```

Для локального запуска Django-сервера можно использовать:

```bash
python manage.py runserver 0.0.0.0:8000
```

## 8. Запуск через Docker

В корне проекта используется `docker compose`.

Сервис Django собирается из каталога `django-admin`, а стартовый скрипт контейнера выполняет:

- `python manage.py migrate --noinput`;
- `python manage.py compilemessages`;
- `python manage.py collectstatic --noinput`;
- запуск `uwsgi` с конфигурацией из `uwsgi/uwsgi.ini`.

Типовой запуск всего стека:

```bash
docker compose up --build
```

## 9. Переменные окружения

Минимальный набор переменных, которые использует проект:

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

При необходимости можно добавить `SQL_DEBUG` и `SQL_LOG_FILE` для отладки SQL.

## 10. Переводы

Переводы лежат в `movies/locale/en/LC_MESSAGES/django.po` и `movies/locale/ru/LC_MESSAGES/django.po`.

Если вы меняете пользовательские строки в моделях, admin или API, проверьте, что:

- новые `msgid` добавлены в `.po` файлы;
- после этого выполнен `python manage.py compilemessages`;
- строковые ключи остаются согласованными между моделями и переводами.

## 11. Правила изменений

Перед изменением Django-части полезно проверять цепочку целиком:

1. Модели и миграции.
2. Админка и отображение данных.
3. API-маршруты и view-логика.
4. Переводы.
5. Docker entrypoint и compose-конфигурация.

Если меняется схема данных, не забывайте обновить:

- модели;
- миграции;
- admin-конфигурацию;
- API;
- переводы;
- документацию.

## 12. Точки входа для отладки

Если что-то не запускается, начинайте с этих файлов:

- `manage.py`;
- `config/settings.py`;
- `config/urls.py`;
- `movies/models.py`;
- `movies/admin.py`;
- `movies/api/v1/views.py`;
- `entrypoint.sh`;
- `docker-compose.yml`.

## 13. Замечания по эксплуатации

- Админка и API используют один и тот же Django-процесс.
- Контейнер ожидает доступность PostgreSQL до старта приложения.
- При старте контейнера перевод и статика собираются автоматически.
- Для production-окружения следует проверять `ALLOWED_HOSTS`, `SECRET_KEY` и настройки базы данных отдельно.
