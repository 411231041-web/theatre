"""Тесты для маппинга данных из Elasticsearch в модели."""

from models.film_api import FilmDetail, FilmShort
from models.genre_api import GenreDetail, GenreShort
from models.person_api import PersonDetail, PersonSearchResult
from services.mappers import FilmMapper, GenreMapper, PersonMapper


class TestFilmMapper:
    """Тесты для маппинга фильмов."""

    def test_map_to_short_basic_fields(self):
        """Тест маппинга основных полей в FilmShort."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Test Film",
            "imdb_rating": 8.5,
            "description": "Test description",
            "genre": ["Action", "Drama"],
        }

        result = FilmMapper.to_short(source)

        assert isinstance(result, FilmShort)
        assert str(result.uuid) == source["id"]
        assert result.title == "Test Film"
        assert result.imdb_rating == 8.5
        assert result.genres == ["Action", "Drama"]

    def test_map_to_short_with_missing_fields(self):
        """Тест маппинга с отсутствующими полями."""
        source = {"id": "123e4567-e89b-12d3-a456-426614174000"}

        result = FilmMapper.to_short(source)

        assert result.title == ""
        assert result.imdb_rating is None
        assert result.genres == []

    def test_map_to_detail_with_people(self):
        """Тест маппинга в FilmDetail с людьми."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Film Title",
            "imdb_rating": 7.5,
            "genre": ["Comedy", "Thriller"],
            "actors": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "Actor One",
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174002",
                    "name": "Actor Two",
                },
            ],
            "directors": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174003",
                    "name": "Director",
                }
            ],
            "writers": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174004",
                    "name": "Writer",
                }
            ],
        }

        result = FilmMapper.to_detail(source)

        assert isinstance(result, FilmDetail)
        assert result.title == "Film Title"
        assert len(result.actors) == 2
        assert result.actors[0].full_name == "Actor One"
        assert len(result.directors) == 1
        assert result.directors[0].full_name == "Director"

    def test_map_to_detail_filters_incomplete_people(self):
        """Тест фильтрации людей без ID или имени."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Film",
            "actors": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "Valid",
                },
                {"name": "No ID"},
                {"id": "123e4567-e89b-12d3-a456-426614174002"},
                {},
            ],
            "directors": [],
            "writers": [],
        }

        result = FilmMapper.to_detail(source)

        assert len(result.actors) == 1
        assert result.actors[0].full_name == "Valid"


class TestGenreMapper:
    """Тесты для маппинга жанров."""

    def test_map_to_short(self):
        """Тест маппинга в GenreShort."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174010",
            "name": "Action",
        }

        result = GenreMapper.to_short(source)

        assert isinstance(result, GenreShort)
        assert str(result.uuid) == "123e4567-e89b-12d3-a456-426614174010"
        assert result.name == "Action"

    def test_map_to_detail(self):
        """Тест маппинга в GenreDetail."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174011",
            "name": "Comedy",
            "description": "Funny movies",
        }

        result = GenreMapper.to_detail(source)

        assert isinstance(result, GenreDetail)
        assert result.name == "Comedy"
        assert result.description == "Funny movies"

    def test_map_to_detail_with_missing_description(self):
        """Тест маппинга без описания."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174012",
            "name": "Drama",
        }

        result = GenreMapper.to_detail(source)

        assert result.description is None


class TestPersonMapper:
    """Тесты для маппинга персон."""

    def test_map_to_short(self):
        """Тест маппинга в PersonSearchResult (to_short)."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "full_name": "John Doe",
            "films": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "roles": ["actor"],
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174002",
                    "roles": ["director", "writer"],
                },
            ],
        }

        result = PersonMapper.to_short(source)

        assert isinstance(result, PersonSearchResult)
        assert result.full_name == "John Doe"
        assert len(result.films) == 2

    def test_map_to_detail(self):
        """Тест маппинга в PersonDetail (to_detail)."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174001",
            "full_name": "Jane Smith",
            "films": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174002",
                    "roles": ["writer"],
                },
            ],
        }

        result = PersonMapper.to_detail(source)

        assert isinstance(result, PersonDetail)
        assert result.full_name == "Jane Smith"
        assert len(result.films) == 1
        assert result.films[0].roles == ["writer"]

    def test_map_to_search_result_no_role_filter(self):
        """Тест маппинга в PersonSearchResult без фильтрации по ролям."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174002",
            "full_name": "Tom Hardy",
            "films": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174003",
                    "roles": ["actor"],
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174004",
                    "roles": ["director"],
                },
            ],
        }

        result = PersonMapper.to_search_result(source, role=None)

        assert isinstance(result, PersonSearchResult)
        assert len(result.films) == 2

    def test_map_to_search_result_with_role_filter(self):
        """Тест маппинга в PersonSearchResult с фильтрацией по ролям."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174003",
            "full_name": "Tom Hardy",
            "films": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174004",
                    "roles": ["actor"],
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174005",
                    "roles": ["director", "writer"],
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174006",
                    "roles": ["writer"],
                },
            ],
        }

        result = PersonMapper.to_search_result(source, role="writer")

        assert len(result.films) == 2
        assert all(f.roles == ["writer"] for f in result.films)

    def test_map_to_search_result_filters_incomplete_films(self):
        """Тест фильтрации фильмов без ID."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174004",
            "full_name": "John",
            "films": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174005",
                    "roles": ["actor"],
                },
                {"roles": ["director"]},
                {},
            ],
        }

        result = PersonMapper.to_search_result(source, role=None)

        assert len(result.films) == 1
        assert str(result.films[0].uuid) == (
            "123e4567-e89b-12d3-a456-426614174005"
        )

    def test_map_to_search_result_actor_role_only(self):
        """Тест поиска только актёрских ролей."""
        source = {
            "id": "123e4567-e89b-12d3-a456-426614174006",
            "full_name": "Brad Pitt",
            "films": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174007",
                    "roles": ["actor"],
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174008",
                    "roles": ["director"],
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174009",
                    "roles": ["actor", "writer"],
                },
            ],
        }

        result = PersonMapper.to_search_result(source, role="actor")

        assert len(result.films) == 2
        assert all("actor" in f.roles for f in result.films)
