FROM python:3.13-slim

WORKDIR /opt/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV UWSGI_PROCESSES 1
ENV UWSGI_THREADS 16
ENV UWSGI_HARAKIRI 240
ENV DJANGO_SETTINGS_MODULE 'config.settings'

COPY requirements.txt requirements.txt
COPY uwsgi/uwsgi.ini uwsgi.ini
COPY entrypoint.sh entrypoint.sh

RUN  mkdir -p /var/www/static/ \
     && mkdir -p /var/www/media/ \
     && mkdir -p /opt/app/static/ \
     && mkdir -p /opt/app/media/ \
     && apt-get update \
     && apt-get install -y --no-install-recommends gettext \
        build-essential \
        python3-dev \
        libpq-dev \
     && rm -rf /var/lib/apt/lists/* \
     && pip install --upgrade pip \
     && pip install -r requirements.txt

COPY . .

EXPOSE 8000

RUN chmod +x /opt/app/entrypoint.sh || true

ENTRYPOINT ["/opt/app/entrypoint.sh"]
