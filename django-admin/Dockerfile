FROM python:3.13-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UWSGI_PROCESSES=1
ENV UWSGI_THREADS=16
ENV UWSGI_HARAKIRI=240
ENV DJANGO_SETTINGS_MODULE='config.settings'

COPY requirements.txt requirements.txt
COPY uwsgi/uwsgi.ini uwsgi.ini
COPY entrypoint.sh entrypoint.sh

RUN mkdir -p /var/www/static/ \
    && mkdir -p /var/www/media/ \
    && mkdir -p /app/static/ \
    && mkdir -p /app/media/ \
    && apk update \
    && apk add --no-cache \
        gettext \
        build-base \
        python3-dev \
        libpq-dev \
        postgresql-dev \
        linux-headers \
        musl-dev \
    && rm -rf /var/cache/apk/* \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

EXPOSE 8000

RUN chmod +x /app/entrypoint.sh || true

ENTRYPOINT ["/app/entrypoint.sh"]
