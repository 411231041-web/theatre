#!/usr/bin/env bash

set -e

# Переключаемся в рабочую директорию приложения
cd /opt/app || exit 1

# Выполняем миграции и собираем статические файлы
python manage.py migrate --noinput
python manage.py compilemessages
python manage.py collectstatic --noinput

# Запускаем uWSGI с конфигурацией из uwsgi.ini
exec uwsgi --strict --ini uwsgi.ini
