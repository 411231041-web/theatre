from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.db.elasticsearch import get_elastic_client
from src.db.redis import get_redis_client
from src.models.film_api import FilmDetail, FilmShort
from src.services.films import FilmService, get_film_service

router = APIRouter(prefix="/films", tags=["films"])


def get_service() -> FilmService:
    """
    Создает и возвращает экземпляр FilmService с зависимостями.

    Returns:
        FilmService: Экземпляр сервиса для работы с фильмами.
    """
    return get_film_service(get_elastic_client(), get_redis_client())


@router.get(
    "/",
    response_model=list[FilmShort],
    summary="Список фильмов",
    description=(
        "Возвращает список фильмов с возможностью сортировки, "
        "пагинации и фильтрации по жанру."
    ),
)
async def films_list(
    service: FilmService = Depends(get_service),
    sort: str = Query(default="-imdb_rating", pattern=r"^-?imdb_rating$"),
    page_size: int = Query(default=50, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
    genre: str | None = Query(default=None),
    filter_genre: str | None = Query(default=None, alias="filter[genre]"),
) -> list[FilmShort]:
    """
    Получить список фильмов с пагинацией и фильтрацией.

    Args:
        service: Зависимость - сервис для работы с фильмами.
        sort: Поле для сортировки (по умолчанию -imdb_rating, убывающий порядок).
        page_size: Количество записей на страницу (от 1 до 100, по умолчанию 50).
        page_number: Номер страницы (от 1, по умолчанию 1).
        genre: Идентификатор жанра для фильтрации.
        filter_genre: Альтернативный параметр фильтрации по жанру (alias: filter[genre]).

    Returns:
        list[FilmShort]: Список кратких данных о фильмах.
    """
    selected_genre = filter_genre or genre

    return await service.list_films(
        page_size=page_size,
        page_number=page_number,
        sort=sort,
        genre=selected_genre,
    )


@router.get(
    "/{film_id}",
    response_model=FilmDetail,
    summary="Детальная информация о фильме",
    description="Возвращает детальную информацию по идентификатору фильма.",
)
async def film_details(
    film_id: UUID,
    service: FilmService = Depends(get_service),
) -> FilmDetail:
    """
    Получить детальную информацию о фильме по его идентификатору.

    Args:
        film_id: Уникальный идентификатор фильма (UUID).
        service: Зависимость - сервис для работы с фильмами.

    Returns:
        FilmDetail: Детальная информация о фильме.

    Raises:
        HTTPException: Если фильм не найден (status_code=404).
    """
    film = await service.get_by_id(film_id)
    if film is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Film not found",
        )

    return film
