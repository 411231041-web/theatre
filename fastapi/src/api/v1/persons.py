from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.elasticsearch import get_elastic_client
from db.redis import get_redis_client
from models.person_api import PersonDetail, PersonSearchResult
from services.persons import PersonService, get_person_service

router = APIRouter(prefix="/persons", tags=["persons"])


def get_service() -> PersonService:
    """
    Создает и возвращает экземпляр PersonService с зависимостями.

    Returns:
        PersonService: Экземпляр сервиса для работы с персонами.
    """
    return get_person_service(get_elastic_client(), get_redis_client())


@router.get(
    "/search",
    response_model=list[PersonSearchResult],
    summary="Поиск персоналий",
    description="Возвращает список персоналий по запросу с пагинацией.",
)
async def persons_search(
    query: str = Query(default="", min_length=1),
    sort: str = Query(default="full_name", pattern=r"^-?full_name$"),
    role: str | None = Query(default=None),
    filter_role: str | None = Query(default=None, alias="filter[role]"),
    page_size: int = Query(default=50, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
    service: PersonService = Depends(get_service),
) -> list[PersonSearchResult]:
    """
    Выполнить поиск персон по запросу с фильтрацией по роли.

    Args:
        query: Поисковый запрос (минимальная длина 1 символ).
        sort: Поле для сортировки (по умолчанию full_name, по возрастанию).
        role: Роль для фильтрации (actor, director, writer).
        filter_role: Альтернативный параметр фильтрации по роли
            (alias: filter[role]).
        page_size: Количество записей на страницу (от 1 до 100,
            по умолчанию 50).
        page_number: Номер страницы (от 1, по умолчанию 1).
        service: Зависимость - сервис для работы с персонами.

    Returns:
        list[PersonSearchResult]: Список найденных персон с краткой
            информацией о фильмах.
    """
    selected_role = filter_role or role

    result = await service.search_persons(
        query=query,
        sort=sort,
        role=selected_role,
        page_size=page_size,
        page_number=page_number,
    )

    persons = result["persons"]
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

    return persons


@router.get(
    "/{person_id}",
    response_model=PersonDetail,
    summary="Детальная информация о персоне",
    description="Возвращает детальную информацию по идентификатору персоны.",
)
async def person_details(
    person_id: UUID,
    service: PersonService = Depends(get_service),
) -> PersonDetail:
    """
    Получить детальную информацию о персоне по её идентификатору.

    Args:
        person_id: Уникальный идентификатор персоны (UUID).
        service: Зависимость - сервис для работы с персонами.

    Returns:
        PersonDetail: Детальная информация о персоне с фильмами.

    Raises:
        HTTPException: Если персона не найдена (status_code=404).
    """
    person = await service.get_by_id(person_id)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    return person


@router.get(
    "/{person_id}/film",
    response_model=list[dict],
    summary="Фильмы по персоне",
    description="Возвращает список фильмов, в которых участвовала персона.",
)
async def person_films(
    person_id: UUID,
    page_size: int = Query(default=50, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
    service: PersonService = Depends(get_service),
) -> list[dict]:
    """
    Получить список фильмов по идентификатору персоны.

    Args:
        person_id: Уникальный идентификатор персоны (UUID).
        page_size: Количество записей на страницу (от 1 до 100,
            по умолчанию 50).
        page_number: Номер страницы (от 1, по умолчанию 1).
        service: Зависимость - сервис для работы с персонами.

    Returns:
        list[dict]: Список фильмов с информацией об участии персоны.

    Raises:
        HTTPException: Если персона не найдена или не участвовала в фильмах
            (status_code=404).
    """
    films = await service.get_films_by_person(
        person_id=person_id,
        page_size=page_size,
        page_number=page_number,
    )
    if not films:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found or has no films",
        )

    return films
