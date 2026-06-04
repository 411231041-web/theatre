"""
Мапперы для преобразования ES-данных в модели.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic

from models.film_api import (
    FilmDetail,
    FilmShort,
    GenreInFilm,
    PersonInFilm,
)
from models.genre_api import GenreDetail, GenreShort
from models.person_api import (
    FilmInPerson,
    PersonDetail,
    PersonSearchResult,
)

TModel = TypeVar("TModel")


class BaseMapper(ABC, Generic[TModel]):
    """Абстрактный базовый маппер."""

    @abstractmethod
    def to_short(self, source: dict) -> TModel:
        """Преобразовать в краткую модель."""
        pass

    @abstractmethod
    def to_detail(self, source: dict) -> TModel:
        """Преобразовать в детальную модель."""
        pass


class FilmMapper(BaseMapper):
    """Маппер для фильмов."""

    @staticmethod
    def to_short(source: dict) -> FilmShort:
        """Преобразовать ES-документ в FilmShort."""
        return FilmShort(
            uuid=source["id"],
            title=source.get("title", ""),
            imdb_rating=source.get("imdb_rating"),
            description=source.get("description"),
            genres=source.get("genre", []),
        )

    @staticmethod
    def to_detail(source: dict) -> FilmDetail:
        """Преобразовать ES-документ в FilmDetail."""
        genres = [
            GenreInFilm(name=genre_name)
            for genre_name in source.get("genre", [])
            if genre_name
        ]

        def map_people(items: list[dict]) -> list[PersonInFilm]:
            return [
                PersonInFilm(uuid=item["id"], full_name=item["name"])
                for item in items
                if item.get("id") and item.get("name")
            ]

        return FilmDetail(
            uuid=source["id"],
            title=source.get("title", ""),
            imdb_rating=source.get("imdb_rating"),
            description=source.get("description"),
            genre=genres,
            actors=map_people(source.get("actors", [])),
            writers=map_people(source.get("writers", [])),
            directors=map_people(source.get("directors", [])),
        )


class GenreMapper(BaseMapper):
    """Маппер для жанров."""

    @staticmethod
    def to_short(source: dict) -> GenreShort:
        """Преобразовать ES-документ в GenreShort."""
        return GenreShort(
            uuid=source["id"],
            name=source.get("name", ""),
        )

    @staticmethod
    def to_detail(source: dict) -> GenreDetail:
        """Преобразовать ES-документ в GenreDetail."""
        return GenreDetail(
            uuid=source["id"],
            name=source.get("name", ""),
            description=source.get("description"),
        )


class PersonMapper(BaseMapper):
    """Маппер для персон."""

    @staticmethod
    def to_short(source: dict) -> PersonSearchResult:
        """Преобразовать ES-документ в PersonSearchResult."""
        return PersonMapper.to_search_result(source, role=None)

    @staticmethod
    def to_detail(source: dict) -> PersonDetail:
        """Преобразовать ES-документ в PersonDetail."""
        return PersonDetail(
            uuid=source["id"],
            full_name=source.get("full_name", ""),
            films=PersonMapper.to_films(source),
        )

    @staticmethod
    def to_films(
        source: dict,
        role: str | None = None,
    ) -> list[FilmInPerson]:
        """Преобразовать список фильмов персоны в DTO."""
        films: list[FilmInPerson] = []
        for film in source.get("films", []):
            if not film.get("id"):
                continue
            roles = film.get("roles", [])
            if role is None:
                films.append(
                    FilmInPerson(uuid=film["id"], roles=roles),
                )
            elif role in roles:
                films.append(
                    FilmInPerson(uuid=film["id"], roles=[role]),
                )
        return films

    @staticmethod
    def to_search_result(
        source: dict,
        role: str | None = None,
    ) -> PersonSearchResult:
        """Преобразовать ES-документ в PersonSearchResult."""
        return PersonSearchResult(
            uuid=source["id"],
            full_name=source.get("full_name", ""),
            films=PersonMapper.to_films(source, role=role),
        )
