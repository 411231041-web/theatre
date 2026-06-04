#!/usr/bin/env sh

set -e

# Переключаемся в рабочую директорию приложения
cd /app || exit 1

# Выполняем миграции и собираем статические файлы
python manage.py migrate --noinput
python manage.py compilemessages
python manage.py collectstatic --noinput

# Запускаем uWSGI с конфигурацией из uwsgi.ini
exec uwsgi --strict --ini uwsgi.ini
