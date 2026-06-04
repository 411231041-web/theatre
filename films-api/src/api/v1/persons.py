from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.v1.helpers import paginated_result
from core.dependencies import get_persons_dependency
from models.pagination import PaginatedResponse
from models.person_api import FilmInPerson, PersonDetail, PersonSearchResult
from services.persons import PersonService

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get(
    "/search",
    response_model=PaginatedResponse[PersonSearchResult],
    summary="Поиск персоналий",
    description="Возвращает список персоналий по запросу с пагинацией.",
)
async def persons_search(
    query: str = Query(
        ..., min_length=1, description="Строка поискового запроса",
    ),
    sort: str = Query(default="full_name", pattern=r"^-?full_name$"),
    role: str | None = Query(default=None),
    filter_role: str | None = Query(default=None, alias="filter[role]"),
    page_size: int = Query(default=50, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
    service: PersonService = Depends(get_persons_dependency),
) -> PaginatedResponse[PersonSearchResult]:
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

    return paginated_result(
        persons,
        total_hits,
        page_number,
        page_size,
    )


@router.get(
    "/{person_id}",
    response_model=PersonDetail,
    summary="Детальная информация о персоне",
    description="Возвращает детальную информацию по идентификатору персоны.",
)
async def person_details(
    person_id: UUID,
    service: PersonService = Depends(get_persons_dependency),
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
    response_model=list[FilmInPerson],
    summary="Фильмы по персоне",
    description="Возвращает список фильмов, в которых участвовала персона.",
)
async def person_films(
    person_id: UUID,
    page_size: int = Query(default=50, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
    service: PersonService = Depends(get_persons_dependency),
) -> list[FilmInPerson]:
    """
    Получить список фильмов по идентификатору персоны.

    Args:
        person_id: Уникальный идентификатор персоны (UUID).
        page_size: Количество записей на страницу (от 1 до 100,
            по умолчанию 50).
        page_number: Номер страницы (от 1, по умолчанию 1).
        service: Зависимость - сервис для работы с персонами.

    Returns:
        list[FilmInPerson]: Список фильмов с информацией об участии персоны.

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
