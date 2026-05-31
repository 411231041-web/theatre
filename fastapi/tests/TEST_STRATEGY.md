# Тестирование переструктурированного сервисного слоя

## Новая структура

После рефакторинга архитектура сервисов разделена на:

- **repositories.py** — доступ к данным (Elasticsearch)
- **mappers.py** — преобразование ES-данных в модели
- **base.py** — базовая логика кэширования и управления зависимостями
- **films.py, genres.py, persons.py** — бизнес-логика каждого домена

## Новые тестовые файлы

### test_repositories.py
Тесты для `ElasticsearchRepository`:
- `test_get_by_id_returns_source` — получение по ID
- `test_get_by_id_returns_none_on_not_found` — обработка 404
- `test_search_returns_hits_and_total` — поиск с пагинацией
- `test_search_with_filters` — фильтрация
- `test_search_respects_source_fields` — выборка полей

### test_mappers.py
Тесты для маппинга данных:

**FilmMapper:**
- `test_map_to_short_basic_fields` — маппинг основных полей
- `test_map_to_detail_with_people` — маппинг с людьми (actors, directors, writers)
- `test_map_to_detail_filters_incomplete_people` — фильтрация неполных данных

**GenreMapper:**
- `test_map_to_short` — маппинг в GenreShort
- `test_map_to_detail` — маппинг в GenreDetail

**PersonMapper:**
- `test_map_to_search_result_no_role_filter` — поиск без фильтра по ролям
- `test_map_to_search_result_with_role_filter` — поиск с фильтром по ролям
- `test_map_to_search_result_actor_role_only` — поиск только актёров

### test_services.py
Тесты для сервисов:

**FilmService:**
- `test_get_by_id_returns_film_from_db` — получение фильма
- `test_list_films_calls_repository_search` — вызов поиска в репозитории
- `test_search_films_with_query` — полнотекстовый поиск
- `test_list_films_builds_correct_filter_query` — построение фильтров

**GenreService:**
- `test_get_by_id_returns_genre_from_db` — получение жанра
- `test_list_genres_calls_repository_search` — поиск жанров
- `test_list_genres_with_name_filter` — фильтрация по названию

## Запуск тестов

```bash
# Все тесты
pytest

# Только репозитории
pytest tests/test_repositories.py -v

# Только маппинг
pytest tests/test_mappers.py -v

# Только сервисы
pytest tests/test_services.py -v

# API-тесты (существующие)
pytest tests/test_films_api.py tests/test_genres_api.py tests/test_persons_api.py -v

# С покрытием
pytest --cov=services --cov=api --cov-report=html
```

## Ключевые изменения в тестировании

### Перед рефакторингом
- Тесты тестировали жесткие зависимости (`AsyncElasticsearch`, `Redis`)
- Сложно мокировать логику, перемешанную с доступом к данным
- Дублирование логики кэширования в каждом сервисе

### После рефакторинга
- Тесты репозитория изолируют доступ к данным
- Тесты маппинга проверяют трансформацию данных отдельно
- Тесты сервисов тестируют бизнес-логику через мок-репозиторий
- Легко добавить новые источники данных (SQL, Redis и т.д.)

## Примеры использования моков

```python
# Мок репозитория
mock_repository = MagicMock()
mock_repository.get_by_id = AsyncMock(return_value=film_data)
mock_repository.search = AsyncMock(return_value=([film_data], 1))

# Создание сервиса с мок-зависимостями
service = FilmService(
    repository=mock_repository,
    redis=mock_redis,
    settings=mock_settings,
)

# Тестирование
result = await service.get_by_id(film_id)
assert result.title == "Test Film"
```

## SOLID принципы в тестах

✅ **SRP** — каждый тест проверяет одну ответственность  
✅ **OCP** — легко добавить тесты для новых репозиториев без изменения старых  
✅ **LSP** — любой репозиторий с интерфейсом `BaseRepository` работает  
✅ **ISP** — тесты не зависят от лишних методов  
✅ **DIP** — тесты работают с абстракциями, а не конкретными реализациями
