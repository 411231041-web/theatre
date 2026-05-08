# ETL Developer Guide

## 1. Цель документа

Этот документ описывает внутреннее устройство ETL-модуля `etl`, правила его расширения и практический workflow для разработчиков.

ETL отвечает за инкрементальную синхронизацию данных из PostgreSQL (`content` schema) в Elasticsearch.

## 2. Границы ETL

В проекте есть 3 независимых ETL-процесса:

- films -> индекс `movies`
- genres -> индекс `genres`
- persons -> индекс `persons`

Каждый процесс использует общий набор инфраструктурных компонентов:

- конфигурация (`config.py`)
- retry/backoff (`backoff.py`)
- чтение из PostgreSQL (`postgres_loader.py`)
- преобразование payload (`transformer.py`)
- запись в Elasticsearch (`es_saver.py`)
- хранение курсора (`state.py`)

## 3. Архитектура по слоям

### 3.1 Orchestration layer

Точки входа:

- `postgres_to_es/films_main.py`
- `postgres_to_es/genres_main.py`
- `postgres_to_es/persons_main.py`

Каждая точка входа реализует единый жизненный цикл:

1. setup:
- создать клиентов PostgreSQL/Elasticsearch
- проверить/создать индекс в Elasticsearch

2. sync loop:
- получить changed IDs после курсора
- получить полный payload по IDs
- преобразовать payload в документы ES
- записать bulk-операцией
- обновить cursor только после успешной записи

3. cleanup:
- закрыть подключения

### 3.2 Data access layer (PostgreSQL)

`postgres_loader.py` инкапсулирует SQL-вызовы и не содержит бизнес-логики преобразования.

Ключевые методы:

- `get_changed_films`
- `get_films_data`
- `get_changed_genres`
- `get_genres_data`
- `get_changed_persons`
- `get_persons_data`

SQL хранится в `queries.py`. Это важно для поддерживаемости: оркестрация не должна содержать raw SQL.

### 3.3 Transformation layer

`transformer.py` приводит данные PostgreSQL к итоговому JSON-формату Elasticsearch.

Принципы:

- нормализация nullable-полей
- приведение типов (`id` -> string, `rating` -> float|None)
- защита от плохих данных (ошибки на уровне записи логируются и не валят весь батч)

### 3.4 Storage layer (Elasticsearch)

`es_saver.py`:

- проверяет существование индекса и создает его при необходимости
- выполняет bulk write
- поднимает исключение, если есть ошибки bulk-операции

Bulk write использует `_op_type=index`, что делает операции идемпотентными по `_id`.

### 3.5 State layer

`state.py` хранит инкрементальный курсор в JSON:

- `cursor_timestamp`
- `cursor_id`

Курсор обновляется только после успешной записи текущего батча в Elasticsearch.
Это ключевая гарантия корректного resume после падения процесса.

## 4. Инкрементальная модель синхронизации

Все changed-запросы используют одинаковый принцип курсора:

- выбрать записи, где `changed_at > cursor_timestamp`
- либо `changed_at = cursor_timestamp AND id > cursor_id`
- сортировка `ORDER BY changed_at, id`

Эта схема нужна для детерминированного обхода и корректной обработки совпадений по времени.

## 5. Конфигурация и окружение

Источник настроек: `pydantic-settings` (`Settings` в `config.py`).

Основные переменные:

- PostgreSQL: `SQL_HOST`, `SQL_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Elasticsearch: `ELASTICSEARCH_HOST`, `ELASTICSEARCH_PORT`, `ELASTICSEARCH_FILMS_INDEX`
- ETL runtime: `ETL_STATE_FILE`, `ETL_BATCH_SIZE`, `ETL_POLL_INTERVAL`
- Retry/backoff: `ETL_MAX_RETRIES`, `ETL_INITIAL_BACKOFF`, `ETL_MAX_BACKOFF`, `ETL_BACKOFF_MULTIPLIER`

В Docker Compose все ETL-сервисы задают `ELASTICSEARCH_FILMS_INDEX`; у каждого
сервиса свой `ETL_STATE_FILE`.

## 6. Локальная разработка

### 6.1 Подготовка окружения

Из каталога `etl`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 6.2 Запуск отдельных пайплайнов

```bash
python -m postgres_to_es.films_main
python -m postgres_to_es.genres_main
python -m postgres_to_es.persons_main
```

### 6.3 Запуск в Docker Compose (из корня проекта)

```bash
docker compose up -d --build theatre-db elasticsearch etl-films etl-genres etl-persons
```

Логи:

```bash
docker compose logs -f etl-films
docker compose logs -f etl-genres
docker compose logs -f etl-persons
```

## 7. Контракты данных

### 7.1 Films (индекс movies)

Ожидаемые поля документа:

- `id`
- `title`
- `description`
- `genres` (list[str])
- `imdb_rating` (float | null)
- `directors_names`, `actors_names`, `writers_names` (list[str])
- `directors`, `actors`, `writers` (list[object{id, name}])

### 7.2 Genres (индекс genres)

- `id`
- `name`
- `description`

### 7.3 Persons (индекс persons)

- `id`
- `full_name`
- `films` (list[object{id, roles}])

Важно: если меняется контракт документа, нужно синхронно обновить:

1. SQL payload-запрос в `queries.py`
2. трансформацию в `transformer.py`
3. индексные настройки в соответствующем `es_*_index_settings.json`
4. потребителей в FastAPI (если поле используется API-слоем)

## 8. Retry и отказоустойчивость

Все операции доступа к PostgreSQL/Elasticsearch выполняются через `RetryConfig.execute_with_retry`.

Особенности текущей реализации:

- экспоненциальный backoff
- jitter (`0.5x .. 1.5x`)
- ограничение максимальной задержки (`max_delay`)
- при исчерпании попыток пробрасывается последнее исключение

Практика: для нестабильной среды увеличивайте `ETL_MAX_RETRIES` и `ETL_MAX_BACKOFF`.

## 9. Логирование и наблюдаемость

`logger.py` пишет в stdout с форматом:

- timestamp
- logger name
- level
- message

Рекомендуемые события для проверки при инцидентах:

- `Connected to PostgreSQL`
- `Connected to Elasticsearch`
- `Processed ... batch`
- `Successfully wrote ... documents`
- retry warning-строки

## 10. Как добавить новый ETL-пайплайн

Пример: нужен новый индекс `collections`.

1. Добавить SQL в `queries.py`:
- changed-query с курсором `(timestamp, id)`
- payload-query по списку IDs

2. Добавить методы чтения в `postgres_loader.py`:
- `get_changed_collections`
- `get_collections_data`

3. Добавить трансформацию в `transformer.py`:
- `transform_collection_to_document`
- `transform_collections_batch`

4. Создать index settings файл в `etl/`:
- `es_collections_index_settings.json`

5. Создать новую точку входа:
- `postgres_to_es/collections_main.py`
- по образцу `genres_main.py` / `persons_main.py`

6. Добавить сервис в `docker-compose.yml`:
- отдельный `ELASTICSEARCH_FILMS_INDEX`
- отдельный `ETL_STATE_FILE`
- `command: ["python", "-m", "postgres_to_es.collections_main"]`

7. Проверить end-to-end:
- старт сервиса
- создание индекса
- появление документов
- корректное обновление state-файла

## 11. Частые проблемы

### 11.1 ETL стартует, но не пишет документы

Проверить:

- правильный индекс (`ELASTICSEARCH_FILMS_INDEX`)
- наличие новых изменений после курсора
- корректность SQL-запросов в `queries.py`
- ошибки bulk в логах

### 11.2 После рестарта дубли/пропуски

Проверить:

- state-файл (`ETL_STATE_FILE`) не общий между разными пайплайнами
- курсор обновляется только после успешной записи (текущий код это соблюдает)
- сортировку в changed-query: только `ORDER BY changed_at, id`

### 11.3 Индекс не соответствует документам

Проверить согласованность:

- `transformer.py`
- `es_*_index_settings.json`
- API-модели и сериализацию на стороне FastAPI

## 12. Правила изменений в ETL

Перед merge убедитесь, что:

- изменены все затронутые слои (SQL -> transform -> index mapping)
- обновлены переменные окружения/compose-конфиг при необходимости
- документация синхронизирована с кодом
- проверен запуск хотя бы одного полного sync-цикла в целевом пайплайне
