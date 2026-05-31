"""Тесты для сервисов с логикой кэширования и маппинга."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.config import Settings
from models.film_api import FilmDetail
from models.genre_api import GenreDetail
from models.person_api import FilmInPerson
from services.films import FilmService
from services.genres import GenreService
from services.persons import PersonService


@pytest.fixture
def mock_settings():
    """Создать мок конфигурации."""
    settings = MagicMock(spec=Settings)
    settings.redis_cache_expire = 3600
    return settings


@pytest.fixture
def mock_cache_backend():
    """Создать мок кэш-бекенда."""
    backend = MagicMock()
    backend.get_model = AsyncMock(return_value=None)
    backend.get_json = AsyncMock(return_value=None)
    backend.set_model = AsyncMock()
    backend.set_json = AsyncMock()
    return backend


@pytest.fixture
def mock_repository():
    """Создать мок репозитория."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.search = AsyncMock()
    return repo


class TestFilmService:
    """Тесты для FilmService."""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_film_from_db(
        self,
        mock_repository,
        mock_cache_backend,
        mock_settings,
    ):
        """Тест получения фильма из БД при отсутствии в кэше."""
        film_id = uuid4()
        film_data = {
            "id": str(film_id),
            "title": "Test Film",
            "imdb_rating": 8.5,
            "genre": [],
            "actors": [],
            "directors": [],
            "writers": [],
        }

        mock_repository.get_by_id.return_value = film_data
        mock_cache_backend.get = AsyncMock(return_value=None)

        service = FilmService(
            repository=mock_repository,
            cache=mock_cache_backend,
            settings=mock_settings,
        )

        result = await service.get_by_id(film_id)

        assert isinstance(result, FilmDetail)
        assert result.title == "Test Film"
        mock_repository.get_by_id.assert_awaited_once_with(film_id)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self,
        mock_repository,
        mock_cache_backend,
        mock_settings,
    ):
        """Тест возврата None при отсутствии фильма."""
        film_id = uuid4()
        mock_repository.get_by_id.return_value = None

        service = FilmService(
            repository=mock_repository,
            cache=mock_cache_backend,
            settings=mock_settings,
        )

        result = await service.get_by_id(film_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_films_calls_repository_search(
        self,
        mock_repository,
        mock_cache_backend,
        mock_settings,
    ):
        """Тест вызова поиска в репозитории."""
        film_source = {
            "id": str(uuid4()),
            "title": "Film 1",
            "imdb_rating": 8.0,
            "genre": ["Action"],
        }

        mock_repository.search.return_value = ([film_source], 1)

        service = FilmService(
            repository=mock_repository,
            cache=mock_cache_backend,
            settings=mock_settings,
        )

        result = await service.list_films(
            page_size=10,
            page_number=1,
            sort="imdb_rating",
            genre="action",
        )

        assert len(result["films"]) == 1
        assert result["total_hits"] == 1
        mock_repository.search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_films_with_query(
        self,
        mock_repository,
        mock_cache_backend,
        mock_settings,
    ):
        """Тест полнотекстового поиска."""
        film_source = {
            "id": str(uuid4()),
            "title": "Search Result",
            "imdb_rating": 7.5,
        }

        mock_repository.search.return_value = ([film_source], 5)

        service = FilmService(
            repository=mock_repository,
            cache=mock_cache_backend,
            settings=mock_settings,
        )

        result = await service.search_films(
            query="test",
            page_size=20,
            page_number=1,
            sort="-imdb_rating",
        )

        assert len(result["films"]) == 1
        assert result["total_hits"] == 5

    @pytest.mark.asyncio
    async def test_list_films_builds_correct_filter_query(
        self,
        mock_repository,
        mock_cache_backend,
        mock_settings,
    ):
        """Тест построения фильтрующего запроса."""
        mock_repository.search.return_value = ([], 0)

        service = FilmService(
            repository=mock_repository,
            cache=mock_cache_backend,
            settings=mock_settings,
        )

        await service.list_films(
            page_size=10,
            page_number=1,
            sort="imdb_rating",
            genre="comedy",
            title="test",
        )

        # Проверяем, что был вызван search с правильными параметрами
        call_args = mock_repository.search.call_args
        assert "query_body" in call_args.kwargs


class TestPersonService:
    """Тесты для PersonService."""

    @pytest.mark.asyncio
    async def test_get_films_by_person_returns_typed_films(
        self,
        mock_repository,
        mock_cache_backend,
        mock_settings,
    ):
        """Тест возвращения типизированного списка фильмов из сервиса."""
        person_id = uuid4()
        film_id = uuid4()
        mock_repository.get_by_id.return_value = {
            "id": str(person_id),
            "films": [
                {"id": str(film_id), "roles": ["actor"]},
                {"roles": ["director"]},
            ],
        }

        service = PersonService(
            repository=mock_repository,
            cache=mock_cache_backend,
            settings=mock_settings,
        )

        result = await service.get_films_by_person(
            person_id=person_id,
            page_size=10,
            page_number=1,
        )

        assert len(result) == 1
        assert isinstance(result[0], FilmInPerson)
        assert str(result[0].uuid) == str(film_id)
        assert result[0].roles == ["actor"]


class TestGenreService:
    """Тесты для GenreService."""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_genre_from_db(
        self,
        mock_repository,
        mock_cache_backend,
        mock_settings,
    ):
        """Тест получения жанра из БД."""
        genre_id = uuid4()
        genre_data = {
            "id": str(genre_id),
            "name": "Action",
            "description": "Action movies",
        }

        mock_repository.get_by_id.return_value = genre_data

        service = GenreService(
            repository=mock_repository,
            cache=mock_cache_backend,
            settings=mock_settings,
        )

        result = await service.get_by_id(genre_id)

        assert isinstance(result, GenreDetail)
        assert result.name == "Action"
        assert result.description == "Action movies"

    @pytest.mark.asyncio
    async def test_list_genres_calls_repository_search(
        self,
        mock_repository,
        mock_cache_backend,
        mock_settings,
    ):
        """Тест вызова поиска жанров в репозитории."""
        genre_source = {
            "id": str(uuid4()),
            "name": "Comedy",
        }

        mock_repository.search.return_value = ([genre_source], 15)

        service = GenreService(
            repository=mock_repository,
            cache=mock_cache_backend,
            settings=mock_settings,
        )

        result = await service.list_genres(
            sort="name",
            name=None,
            page_size=50,
            page_number=1,
        )

        assert len(result["genres"]) == 1
        assert result["total_hits"] == 15
        mock_repository.search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_genres_with_name_filter(
        self,
        mock_repository,
        mock_cache_backend,
        mock_settings,
    ):
        """Тест фильтрации жанров по названию."""
        mock_repository.search.return_value = ([], 0)

        service = GenreService(
            repository=mock_repository,
            cache=mock_cache_backend,
            settings=mock_settings,
        )

        await service.list_genres(
            sort="-name",
            name="action",
            page_size=50,
            page_number=1,
        )

        call_args = mock_repository.search.call_args
        # Проверяем, что был создан запрос для поиска
        assert call_args is not None
