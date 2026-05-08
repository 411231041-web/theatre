FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY etl/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY etl/postgres_to_es ./postgres_to_es

COPY etl/es_films_index_settings.json .
COPY etl/es_genres_index_settings.json .
COPY etl/es_persons_index_settings.json .

RUN touch etl_films_state.json

CMD ["python", "-m", "postgres_to_es.films_main"]
