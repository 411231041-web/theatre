FROM python:3.13-alpine

WORKDIR /app

RUN apk update \
    && apk add --no-cache \
        build-base \
        python3-dev \
        libpq-dev \
    && rm -rf /var/cache/apk/*

COPY etl/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY etl/postgres_to_es ./postgres_to_es

COPY etl/es_films_index_settings.json .
COPY etl/es_genres_index_settings.json .
COPY etl/es_persons_index_settings.json .

CMD ["python", "-m", "postgres_to_es.films_main"]
