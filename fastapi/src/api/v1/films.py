import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.elasticsearch import get_elastic_client
from db.redis import get_redis_client
from models.film_api import FilmDetail, FilmShort
from services.films import FilmService, get_film_service

router = APIRouter(prefix="/films", tags=["films"])


def get_service() -> FilmService:
    """
    Создает и возвращает экземпляр FilmService с зависимостями.

    Returns:
        FilmService: Экземпляр сервиса для работы с фильмами.
    """
    return get_film_service(get_elastic_client(), get_redis_client())


@router.get(
    "",
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
    title: str | None = Query(default=None),
    page_size: int = Query(default=50, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
    genre: str | None = Query(default=None),
    filter_genre: str | None = Query(default=None, alias="filter[genre]"),
) -> list[FilmShort]:
    """
    Получить список фильмов с пагинацией и фильтрацией.

    Args:
        service: Зависимость - сервис для работы с фильмами.
        sort: Поле для сортировки (по умолчанию -imdb_rating).
            Убывающий порядок.
        title: Название фильма для поиска (поиск по частичному совпадению).
        page_size: Количество записей на страницу (от 1 до 100,
            по умолчанию 50).
        page_number: Номер страницы (от 1, по умолчанию 1).
        genre: Идентификатор жанра для фильтрации.
        filter_genre: Альтернативный параметр фильтрации по жанру
            (alias: filter[genre]).

    Returns:
        list[FilmShort]: Список кратких данных о фильмах.
    """
    selected_genre = filter_genre or genre

    result = await service.list_films(
        page_size=page_size,
        page_number=page_number,
        sort=sort,
        genre=selected_genre,
        title=title
    )

    films = result["films"]
    total_hits = result["total_hits"]
    total_pages = max(1, math.ceil(total_hits / page_size))
    if page_number > total_pages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "type": "less_than_equal",
                    "loc": ["query", "page_number"],
                    "msg": (
                        f"Input should be less than or equal to "
                        f"{total_pages}"
                    ),
                    "input": str(page_number),
                    "ctx": {"le": total_pages},
                }
            ],
        )

    return films


@router.get(
    "/search",
    response_model=list[FilmShort],
    summary="Поиск кинопроизведений",
    description="Полнотекстовый поиск по кинопроведениям",
    response_description="Название и рейтинг фильма",
    tags=["Полнотекстовый поиск"],
)
async def film_search(
    query: str = Query(
        ...,
        min_length=1,
        description="Строка поискового запроса",
    ),
    service: FilmService = Depends(get_service),
    sort: str = Query(default="-imdb_rating", pattern=r"^-?imdb_rating$"),
    page_size: int = Query(default=50, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
) -> list[FilmShort]:
    """
    Полнотекстовый поиск по кинопроизведениям.

    Возвращает список фильмов, соответствующих поисковому запросу.
    Для каждого фильма указывается название и рейтинг.
    """
    result = await service.search_films(
        query=query,
        page_size=page_size,
        page_number=page_number,
        sort=sort,
    )

    films = result["films"]
    total_hits = result["total_hits"]
    total_pages = max(1, math.ceil(total_hits / page_size))
    if page_number > total_pages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "type": "less_than_equal",
                    "loc": ["query", "page_number"],
                    "msg": (
                        f"Input should be less than or equal to "
                        f"{total_pages}"
                    ),
                    "input": str(page_number),
                    "ctx": {"le": total_pages},
                }
            ],
        )

    return films


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
