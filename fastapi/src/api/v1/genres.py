import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.elasticsearch import get_elastic_client
from db.redis import get_redis_client
from models.genre_api import GenreDetail, GenreShort
from services.genres import GenreService, get_genre_service

router = APIRouter(prefix="/genres", tags=["genres"])


def get_service() -> GenreService:
    """
    Создает и возвращает экземпляр GenreService с зависимостями.

    Returns:
        GenreService: Экземпляр сервиса для работы с жанрами.
    """
    return get_genre_service(get_elastic_client(), get_redis_client())


@router.get(
    "",
    response_model=list[GenreShort],
    summary="Список жанров",
    description="Возвращает список всех жанров с пагинацией.",
)
async def genres_list(
    sort: str = Query(default="name", pattern=r"^-?name$"),
    name: str | None = Query(default=None),
    filter_name: str | None = Query(default=None, alias="filter[name]"),
    page_size: int = Query(default=50, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
    service: GenreService = Depends(get_service),
) -> list[GenreShort]:
    """
    Получить список жанров с пагинацией и фильтрацией.

    Args:
        sort: Поле для сортировки (по умолчанию name, по возрастанию).
        name: Название жанра для поиска (поиск по частичному совпадению).
        filter_name: Альтернативный параметр фильтрации по названию
            (alias: filter[name]).
        page_size: Количество записей на страницу (от 1 до 100,
            по умолчанию 50).
        page_number: Номер страницы (от 1, по умолчанию 1).
        service: Зависимость - сервис для работы с жанрами.

    Returns:
        list[GenreShort]: Список кратких данных о жанрах.
    """
    selected_name = filter_name or name

    result = await service.list_genres(
        sort=sort,
        name=selected_name,
        page_size=page_size,
        page_number=page_number,
    )

    genres = result["genres"]
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

    return genres


@router.get(
    "/{genre_id}",
    response_model=GenreDetail,
    summary="Детальная информация о жанре",
    description="Возвращает детальную информацию по идентификатору жанра.",
)
async def genre_details(
    genre_id: UUID,
    service: GenreService = Depends(get_service),
) -> GenreDetail:
    """
    Получить детальную информацию о жанре по его идентификатору.

    Args:
        genre_id: Уникальный идентификатор жанра (UUID).
        service: Зависимость - сервис для работы с жанрами.

    Returns:
        GenreDetail: Детальная информация о жанре.

    Raises:
        HTTPException: Если жанр не найден (status_code=404).
    """
    genre = await service.get_by_id(genre_id)
    if genre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found",
        )

    return genre
