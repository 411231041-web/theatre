from __future__ import annotations

import uuid
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedMixin(models.Model):
    """
    Абстрактный миксин для отслеживания времени создания и изменения объектов.

    Автоматически устанавливает временные метки при создании и обновлении записей
    в базе данных.

    Attributes:
        created: Дата и время создания записи (устанавливается автоматически).
        modified: Дата и время последнего изменения записи (обновляется автоматически).
    """
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    """
    Абстрактный миксин для использования UUID в качестве первичного ключа.

    Генерирует и устанавливает уникальный UUID для каждого нового объекта.

    Attributes:
        id: Уникальный идентификатор UUID, используемый как первичный ключ.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Genre(UUIDMixin, TimeStampedMixin):
    """
    Модель жанра фильма.

    Хранит информацию о жанре (кинематографический жанр, например, драма, комедия и т.д.)
    и связана с фильмами через ManyToMany отношение.

    Attributes:
        id: Уникальный идентификатор жанра (UUID).
        name: Название жанра.
        description: Описание жанра (опционально).
        created: Дата создания записи.
        modified: Дата последнего изменения.
    """
    name = models.CharField(_('genre'), max_length=255)
    description = models.TextField(_('description'), blank=True)

    def __str__(self):
        """Возвращает строковое представление жанра (его название)."""
        return self.name

    class Meta:
        db_table = 'content"."genre'
        verbose_name = _('genre')
        verbose_name_plural = _('genres')
        ordering = ('name',)


class Person(UUIDMixin, TimeStampedMixin):
    """
    Модель личности (актёра, режиссёра, сценариста и т.д.).

    Хранит информацию о людях, участвующих в создании фильмов (актёры, режиссёры,
    сценаристы) и связана с фильмами через ManyToMany отношение.

    Attributes:
        id: Уникальный идентификатор личности (UUID).
        full_name: Полное имя человека.
        created: Дата создания записи.
        modified: Дата последнего изменения.
    """
    full_name = models.CharField(_('name'), max_length=255)

    def __str__(self):
        """Возвращает строковое представление личности (её полное имя)."""
        return self.full_name

    class Meta:
        db_table = 'content"."person'
        verbose_name = _('person')
        verbose_name_plural = _('persons')


class FilmTypes(models.TextChoices):
    """
    Варианты типов кинопроизведения.

    Attributes:
        MOVIE: Полнометражный фильм.
        TV_SHOW: Телевизионная передача или сериал.
    """
    MOVIE = 'movie', _('movie')
    TV_SHOW = 'tv show', _('tv show')


class FilmWork(UUIDMixin, TimeStampedMixin):
    """
    Модель кинопроизведения (фильма или телешоу).

    Основная модель, которая хранит информацию о фильмах. Связана с жанрами
    и личностями (актёры, режиссёры, сценаристы) через ManyToMany отношения.

    Attributes:
        id: Уникальный идентификатор фильма (UUID).
        title: Название фильма.
        description: Подробное описание фильма.
        creation_date: Дата создания/выпуска фильма.
        rating: Рейтинг фильма (от 1.0 до 10.0).
        type: Тип кинопроизведения (фильм или телешоу).
        genres: ManyToMany отношение к жанрам.
        persons: ManyToMany отношение к участникам (через PersonFilmWork).
        created: Дата создания записи.
        modified: Дата последнего изменения.
    """
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    creation_date = models.DateField(_('creation date'), blank=True)
    rating = models.FloatField(
        _('rating'),
        blank=True,
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(10.0),
        ],
    )
    type = models.CharField(
        _('type'),
        max_length=7,
        choices=FilmTypes.choices,
        default=FilmTypes.MOVIE,
    )
    genres = models.ManyToManyField(
        Genre,
        through='GenreFilmWork',
        verbose_name=_('genres'),
    )
    persons = models.ManyToManyField(Person, through='PersonFilmWork')

    def __str__(self):
        """Возвращает строковое представление фильма (его название)."""
        return self.title

    class Meta:
        db_table = 'content"."film_work'
        verbose_name = _('film')
        verbose_name_plural = _('films')
        ordering = ['-creation_date']
        indexes = [
            models.Index(
                fields=['creation_date', 'rating'],
                name='film_work_creation_rating_idx',
            ),
        ]


class GenreFilmWork(UUIDMixin):
    """
    Модель связи между фильмом и жанром (through-модель).

    Промежуточная таблица для реализации ManyToMany отношения между фильмами
    и жанрами с дополнительной информацией о дате создания связи.

    Attributes:
        id: Уникальный идентификатор связи (UUID).
        genre: Внешний ключ на жанр.
        film_work: Внешний ключ на фильм.
        created: Дата создания связи.
    """
    genre = models.ForeignKey(
        'Genre',
        on_delete=models.CASCADE,
        verbose_name=_('genre'),
    )
    film_work = models.ForeignKey(FilmWork, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Возвращает строковое представление связи (название жанра)."""
        return self.genre.name

    class Meta:
        db_table = 'content"."genre_film_work'
        verbose_name = _('genre')
        verbose_name_plural = _('film genres')
        constraints = [
            models.UniqueConstraint(
                fields=['film_work', 'genre'],
                name='film_work_genre_idx',
            ),
        ]


class Roles(models.TextChoices):
    """
    Варианты ролей, которые может играть участник фильма.

    Attributes:
        ACTOR: Актёр в фильме.
        DIRECTOR: Режиссёр фильма.
        WRITER: Сценарист фильма.
    """
    ACTOR = 'actor', _('actor')
    DIRECTOR = 'director', _('director')
    WRITER = 'writer', _('writer')


class PersonFilmWork(UUIDMixin):
    """
    Модель связи между фильмом и участником с указанием роли (through-модель).

    Промежуточная таблица для реализации ManyToMany отношения между фильмами
    и участниками (актёры, режиссёры, сценаристы) с информацией о роли участника
    и дате создания связи.

    Attributes:
        id: Уникальный идентификатор связи (UUID).
        person: Внешний ключ на участника (актёра, режиссёра, сценариста).
        film_work: Внешний ключ на фильм.
        role: Роль участника в фильме (актёр, режиссёр, сценарист).
        created: Дата создания связи.
    """
    person = models.ForeignKey(
        'Person',
        on_delete=models.CASCADE,
        verbose_name=_('person'),
    )
    film_work = models.ForeignKey(FilmWork, on_delete=models.CASCADE)
    role = models.CharField(
        _('role'),
        max_length=10,
        choices=Roles.choices,
        default=Roles.ACTOR,
    )
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Возвращает строковое представление связи (полное имя участника)."""
        return self.person.full_name

    class Meta:
        db_table = 'content"."person_film_work'
        verbose_name = _('person')
        verbose_name_plural = _('film persons')
        constraints = [
            models.UniqueConstraint(
                fields=['film_work', 'person', 'role'],
                name='film_work_person_role_idx',
            ),
        ]
