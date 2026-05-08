# ETL: PostgreSQL -> Elasticsearch

## Документация

- Базовая документация: этот файл
- Документация для разработчиков: `DEVELOPER_GUIDE.md`

## Назначение

ETL-модуль синхронизирует данные из PostgreSQL в Elasticsearch в инкрементальном режиме.
В проекте есть три отдельных процесса:

- films: индекс `movies` (запуск через `postgres_to_es.films_main`)
- genres: индекс `genres` (запуск через `postgres_to_es.genres_main`)
- persons: индекс `persons` (запуск через `postgres_to_es.persons_main`)

Каждый процесс:

- читает изменения из PostgreSQL порциями
- преобразует записи в JSON-документы Elasticsearch
- выполняет bulk-запись в Elasticsearch
- сохраняет курсор (время + id) в state-файл

## Структура

- `Dockerfile` - контейнер ETL
- `requirements.txt` - зависимости ETL
- `es_films_index_settings.json` - настройки индекса films
- `es_genres_index_settings.json` - настройки индекса genres
- `es_persons_index_settings.json` - настройки индекса persons
- `postgres_to_es/` - исходный код ETL

Ключевые модули в `postgres_to_es/`:

- `films_main.py` - ETL-пайплайн films
- `genres_main.py` - ETL-пайплайн genres
- `persons_main.py` - ETL-пайплайн persons
- `postgres_loader.py` - чтение из PostgreSQL
- `transformer.py` - преобразование данных в ES-документы
- `es_saver.py` - создание индексов и bulk-запись
- `state.py` - хранение курсора инкрементальной синхронизации
- `config.py` - настройки из переменных окружения
- `queries.py` - SQL-запросы

## Конфигурация

Настройки читаются из переменных окружения (через `pydantic-settings`) и, при наличии, из файла `.env`.

Обязательные/часто используемые параметры:

- `SQL_HOST` (по умолчанию `localhost`)
- `SQL_PORT` (по умолчанию `5432`)
- `POSTGRES_DB` (по умолчанию `movies_database`)
- `POSTGRES_USER` (по умолчанию `postgres`)
- `POSTGRES_PASSWORD` (по умолчанию `postgres`)
- `ELASTICSEARCH_HOST` (по умолчанию `localhost`)
- `ELASTICSEARCH_PORT` (по умолчанию `9200`)
- `ELASTICSEARCH_FILMS_INDEX` (по умолчанию `movies`)
- `ETL_STATE_FILE` (по умолчанию `etl_films_state.json`)
- `ETL_BATCH_SIZE` (по умолчанию `100`)
- `ETL_POLL_INTERVAL` (по умолчанию `10` секунд)

Параметры retry/backoff:

- `ETL_MAX_RETRIES` (по умолчанию `5`)
- `ETL_INITIAL_BACKOFF` (по умолчанию `1.0`)
- `ETL_MAX_BACKOFF` (по умолчанию `60.0`)
- `ETL_BACKOFF_MULTIPLIER` (по умолчанию `2.0`)

## Запуск через Docker Compose

Из корня проекта:

```bash
docker compose up -d --build theatre-db elasticsearch etl-films etl-genres etl-persons
```

Что важно:

- `etl-films` пишет в индекс `movies`
- `etl-genres` пишет в индекс `genres`
- `etl-persons` пишет в индекс `persons`
- состояние хранится в volume `etl-state`

Полный запуск всех сервисов:

```bash
docker compose up -d --build
```

Проверка логов ETL:

```bash
docker compose logs -f etl-films
docker compose logs -f etl-genres
docker compose logs -f etl-persons
```

## Локальный запуск (без Docker для ETL)

Из папки `etl`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Запуск процессов:

```bash
python -m postgres_to_es.films_main
python -m postgres_to_es.genres_main
python -m postgres_to_es.persons_main
```

Перед локальным запуском убедитесь, что PostgreSQL и Elasticsearch доступны по адресам из переменных окружения.

## Как работает инкрементальная синхронизация

- ETL хранит курсор в JSON-файле состояния (`ETL_STATE_FILE`)
- курсор состоит из `cursor_timestamp` и `cursor_id`
- выборка изменений идет по принципу "после курсора"
- курсор обновляется только после успешной записи batch в Elasticsearch

Это позволяет безопасно продолжать синхронизацию после перезапуска.

## Диагностика

Если данных в Elasticsearch нет:

- проверьте доступность PostgreSQL и Elasticsearch
- проверьте корректность `ELASTICSEARCH_FILMS_INDEX` и SQL/ES хостов
- проверьте логи сервисов ETL
- проверьте, что state-файл не поврежден

Если нужно пересобрать индекс с нуля:

- остановите ETL-сервис
- удалите соответствующий state-файл
- удалите индекс в Elasticsearch
- запустите ETL снова
