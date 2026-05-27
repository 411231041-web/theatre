from django.contrib import admin

from .models import FilmWork, Genre, GenreFilmWork, Person, PersonFilmWork


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    """
    Админ-класс для управления жанрами.

    Обеспечивает возможность креативности, редактирования, удаления и
    поиска жанров в админ-панели Django.
    """

    search_fields = ("name",)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """
    Админ-класс для управления участниками кинопроизведения
    (актёры, режиссёры, сценаристы).

    Обеспечивает возможность креативности, редактирования, удаления и
    поиска участников в админ-панели Django.
    """

    search_fields = ("full_name",)


class GenreFilmWorkInline(admin.TabularInline):
    """
    Встроенный админ-класс для эдитирования связей между фильмами и жанрами.

    Позволяет добавлять и удалять жанры из формы редактирования фильма.
    Оснащен автозаполнением для строкол на основе поля жанра.
    """

    model = GenreFilmWork
    autocomplete_fields = ("genre",)


class PersonFilmWorkInline(admin.TabularInline):
    """
    Встроенный админ-класс для эдитирования связей между фильмами
    и участниками.

    Позволяет добавлять и удалять актёров, режиссёров и сценаристов
    непосредственно из формы редактирования фильма.
    Оснащен выбором роли и автозаполнением для участника.
    """

    model = PersonFilmWork
    autocomplete_fields = ("person",)


@admin.register(FilmWork)
class FilmWorkAdmin(admin.ModelAdmin):
    """
    Админ-класс для управления кинопроизведениями в Django админ-панели.

    Обеспечивает ваюрди, редактирование, делетирование,
    табулярное эдитирование связей с жанрами и участниками,
    а также фильтрацию и поиск.

    Attributes:
        inlines: Встроенные формы для эдитирования связей.
        list_display: Поля для отображения в списке.
        list_filter: Наименования полей для фильтрации.
        search_fields: Наименования полей для поиска.
    """

    inlines = (GenreFilmWorkInline, PersonFilmWorkInline)
    list_display = ("title", "type", "creation_date", "rating", "get_genres")
    list_filter = ("type", "genres")
    search_fields = ("title", "description", "id")

    def get_queryset(self, request):
        """
        Оптимизирует основном график запроса для получения набора данных.

        Презагружает связанные жанры для уменьшения количества запросов
        к базе данных.

        Args:
            request: Django HTTP запрос.

        Returns:
            QuerySet: Оптимизированный набор данных с презагруженными жанрами.
        """
        queryset = super().get_queryset(request).prefetch_related("genres")
        return queryset

    def get_genres(self, obj):
        """
        Ретурнирует строковое представление всех жанров кинопроизведения.

        Названия жанров отображаются в листвие моделей
        админ-панели через тот же метод.

        Args:
            obj: Объект модели FilmWork.

        Returns:
            str: Строка названий жанров, разделенных запятыми.
        """
        return ",".join([genre.name for genre in obj.genres.all()])
