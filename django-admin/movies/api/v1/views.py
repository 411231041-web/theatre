from typing import Any
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.http import HttpRequest
from django.http import Http404
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.generic.list import BaseListView
from movies.models import FilmWork


def project_info(_request: HttpRequest) -> JsonResponse:
    """
    Возвращает основную информацию о проекте.

    Args:
        _request: Django HTTP запрос.

    Returns:
        JsonResponse: JSON-ответ с названием и описанием проекта.
    """
    return JsonResponse(
        {
            'project_name': _(settings.PROJECT_NAME),
            'project_description': _(settings.PROJECT_DESCRIPTION),
        }
    )


class MoviesApiMixin:
    """
    Базовый миксин для настройки API для работы с фильмами.

    Обеспечивает базовую настройку джанго-сервера для предоставления данных о фильмах в
    формате JSON. Фильмы настроены с агрегированными данными о жанрах, актёрах,
    режиссёрах и сценаристах.

    Attributes:
        model: Джанго-модель для набора данных.
        http_method_names: Разрешённые HTTP-методы (только GET).
    """
    model = FilmWork
    http_method_names: list[str] = ['get']  # Разрешены только GET-запросы

    def get_queryset(self):
        return (
            FilmWork.objects.values(
                'id',
                'title',
                'description',
                'creation_date',
                'rating',
                'type',
            )
            .annotate(
                # Агрегируем жанры в массив
                genres=ArrayAgg('genres__name', distinct=True),
                # Агрегируем актёров в массив, фильтруя по роли "actor"
                actors=ArrayAgg(
                    'personfilmwork__person__full_name',
                    filter=Q(personfilmwork__role='actor'),
                    distinct=True,
                ),
                # Агрегируем режиссёров в массив, фильтруя по роли "director"
                directors=ArrayAgg(
                    'personfilmwork__person__full_name',
                    filter=Q(personfilmwork__role='director'),
                    distinct=True,
                ),
                # Агрегируем сценаристов в массив, фильтруя по роли "writer"
                writers=ArrayAgg(
                    'personfilmwork__person__full_name',
                    filter=Q(personfilmwork__role='writer'),
                    distinct=True,
                ),
            )
        )

    def render_to_response(self, context, **response_kwargs):
        """
        Отключает стандартные шаблоны Django и выводит данные в формате JSON.

        Args:
            context: Контекст данных для вывода.
            **response_kwargs: Дополнительные параметры для JSON-ответа.

        Returns:
            JsonResponse: JSON-ответ с наданными данными.
        """
        return JsonResponse(context)

    def make_array(self, array: dict[str, Any]) -> dict[str, Any]:
        """
        Обрабатывает данные фильма: заменяет None на пустые массивы.

        Обеспечивает, что все поля массивов (генры, актёры, режиссёры,
        сценаристы) всегда возвращаются как непустые контейнеры.

        Args:
            array: Словарь данных фильма.

        Returns:
            dict[str, Any]: Обработанные данные с гарантированными пустыми массивами.
        """
        for key in ('genres', 'actors', 'directors', 'writers'):
            array[key] = array.get(key) or []
        return array


# API для получения списка фильмов
class MoviesListApi(MoviesApiMixin, BaseListView):
    """
    API вью для получения списка фильмов с пагинацией.

    Предоставляет данные о фильмах страница за страницей в формате JSON.

    Attributes:
        paginate_by: Количество фильмов на одной странице.
    """
    paginate_by = 50  # Количество фильмов на одной странице

    def get_context_data(self, *, object_list=None, **kwargs):
        """
        Формирует контекст данных для JSON-ответа со списком фильмов.

        Обрабатывает пагинацию, фильмы и метаданные о странице.

        Returns:
            dict[str, Any]: Контекст с общим количеством, числом страниц, ссылками на следующую и предыдущую страницы и списком результатов.
        """
        queryset = self.get_queryset()
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset, self.paginate_by
        )
        context = {
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'prev': (
                page.previous_page_number() if page.has_previous() else None
            ),
            'next': page.next_page_number() if page.has_next() else None,
            'results': [
                self.make_array(movie) for movie in queryset
            ],
        }
        return context


# API для получения детальной информации о фильме
class MoviesDetailApi(MoviesApiMixin, BaseListView):
    """
    API вью для получения детальной информации о строке выбранного фильма.

    Получает однин фильм по ID и вернул детальные данные в формате JSON.
    Возвращает ошибку 404, если фильм не найден.
    """

    def get_queryset(self):
        """
        Получает основной набор данных и фильтрирует но одному фильму по ID.

        Returns:
            QuerySet: Офильтрованный набор данных для одного фильма.
        """
        return super().get_queryset().filter(id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        """
        Получает и возвращает данные о денном фильме.

        Обрабатывает данные и убедитесь, что данные фильма составляют гарантированные массивы.
        На настоящие станице если фильм не получичся быв вызывается ошибка 404.

        Returns:
            dict[str, Any]: Обработанные данные денного фильма.

        Raises:
            Http404: Ошибка 404, если фильм не найден.
        """
        movie = self.get_queryset().first()
        if movie is None:
            raise Http404  # Если фильм не найден, возвращаем ошибку 404
        return self.make_array(movie)
