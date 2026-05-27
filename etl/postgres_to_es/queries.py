"""SQL-запросы для ETL-конвейера.

Этот модуль содержит все SQL-запросы, используемые для извлечения данных
из PostgreSQL базы данных во время ETL-процесса.

Запросы включают:
- Поиск измененных записей после определенного курсора
- Получение полных данных с агрегированными связанными сущностями
"""

# Запрос для поиска измененных фильмов после последнего курсора
# (время + ID для разрешения совпадений по времени)
# Использует CTE (Common Table Expressions) для объединения изменений из
# film_work, genre_film_work и person_film_work таблиц
CHANGED_FILMS_QUERY = """
    WITH changed_events AS (
        SELECT
            fw.id AS id,
            fw.modified AS changed_at
        FROM content.film_work fw

        UNION ALL

        SELECT
            gfw.film_work_id AS id,
            GREATEST(
                COALESCE(g.modified, '1970-01-01'::timestamp),
                COALESCE(gfw.created, '1970-01-01'::timestamp)
            ) AS changed_at
        FROM content.genre_film_work gfw
        JOIN content.genre g ON g.id = gfw.genre_id

        UNION ALL

        SELECT
            pfw.film_work_id AS id,
            GREATEST(
                COALESCE(p.modified, '1970-01-01'::timestamp),
                COALESCE(pfw.created, '1970-01-01'::timestamp)
            ) AS changed_at
        FROM content.person_film_work pfw
        JOIN content.person p ON p.id = pfw.person_id
    ),
    latest_changes AS (
        SELECT
            id,
            MAX(changed_at) AS changed_at
        FROM changed_events
        GROUP BY id
    )
    SELECT
        id,
        changed_at
    FROM latest_changes
    WHERE
        changed_at > %(cursor_timestamp)s::timestamp
        OR (
            changed_at = %(cursor_timestamp)s::timestamp
            AND id > %(cursor_id)s::uuid
        )
    ORDER BY changed_at, id
    LIMIT %(limit)s
"""

# Запрос для получения полных данных фильма для загрузки
# Включает агрегированные данные о жанрах, режиссерах, актерах и сценаристах
# Использует JSONB_AGG для создания вложенных структур данных
FILM_PAYLOAD_QUERY = """
    SELECT
        fw.id,
        fw.title,
        fw.description,
        fw.rating as imdb_rating,
        COALESCE(genre_data.genres, '[]'::jsonb) AS genres,
        COALESCE(person_data.directors_names, '[]'::jsonb) AS directors_names,
        COALESCE(person_data.actors_names, '[]'::jsonb) AS actors_names,
        COALESCE(person_data.writers_names, '[]'::jsonb) AS writers_names,
        COALESCE(person_data.directors, '[]'::jsonb) AS directors,
        COALESCE(person_data.actors, '[]'::jsonb) AS actors,
        COALESCE(person_data.writers, '[]'::jsonb) AS writers
    FROM content.film_work fw
    LEFT JOIN (
        SELECT
            gfw.film_work_id,
            JSONB_AGG(DISTINCT g.name)
                FILTER (WHERE g.name IS NOT NULL) AS genres
        FROM content.genre_film_work gfw
        JOIN content.genre g ON g.id = gfw.genre_id
        GROUP BY gfw.film_work_id
    ) genre_data ON genre_data.film_work_id = fw.id
    LEFT JOIN (
        SELECT
            pfw.film_work_id,
            JSONB_AGG(DISTINCT p.full_name)
                FILTER (WHERE pfw.role = 'director') AS directors_names,
            JSONB_AGG(DISTINCT p.full_name)
                FILTER (WHERE pfw.role = 'actor') AS actors_names,
            JSONB_AGG(DISTINCT p.full_name)
                FILTER (
                    WHERE pfw.role IN ('writer', 'screenwriter')
                ) AS writers_names,
            JSONB_AGG(
                DISTINCT JSONB_BUILD_OBJECT('id', p.id, 'name', p.full_name)
            )
                FILTER (WHERE pfw.role = 'director') AS directors,
            JSONB_AGG(
                DISTINCT JSONB_BUILD_OBJECT('id', p.id, 'name', p.full_name)
            )
                FILTER (WHERE pfw.role = 'actor') AS actors,
            JSONB_AGG(
                DISTINCT JSONB_BUILD_OBJECT('id', p.id, 'name', p.full_name)
            )
                FILTER (
                    WHERE pfw.role IN ('writer', 'screenwriter')
                ) AS writers
        FROM content.person_film_work pfw
        JOIN content.person p ON p.id = pfw.person_id
        GROUP BY pfw.film_work_id
    ) person_data ON person_data.film_work_id = fw.id
    WHERE fw.id = ANY(%(film_ids)s)
    ORDER BY fw.id
"""


# Запрос для поиска измененных жанров (только привязанных к фильмам)
# Объединяет изменения из genre таблицы и genre_film_work таблицы
CHANGED_GENRES_QUERY = """
    WITH changed_events AS (
        SELECT
            g.id AS id,
            g.modified AS changed_at
        FROM content.genre g
        JOIN content.genre_film_work gfw ON gfw.genre_id = g.id

        UNION ALL

        SELECT
            gfw.genre_id AS id,
            gfw.created AS changed_at
        FROM content.genre_film_work gfw
    ),
    latest_changes AS (
        SELECT
            id,
            MAX(changed_at) AS changed_at
        FROM changed_events
        GROUP BY id
    )
    SELECT
        id,
        changed_at
    FROM latest_changes
    WHERE
        changed_at > %(cursor_timestamp)s::timestamp
        OR (
            changed_at = %(cursor_timestamp)s::timestamp
            AND id > %(cursor_id)s::uuid
        )
    ORDER BY changed_at, id
    LIMIT %(limit)s
"""


# Запрос для поиска измененных людей, которые участвуют в фильмах
# Объединяет изменения из person таблицы и person_film_work таблицы
CHANGED_PERSONS_QUERY = """
    WITH changed_events AS (
        SELECT
            p.id AS id,
            p.modified AS changed_at
        FROM content.person p
        JOIN content.person_film_work pfw ON pfw.person_id = p.id

        UNION ALL

        SELECT
            pfw.person_id AS id,
            pfw.created AS changed_at
        FROM content.person_film_work pfw
    ),
    latest_changes AS (
        SELECT
            id,
            MAX(changed_at) AS changed_at
        FROM changed_events
        GROUP BY id
    )
    SELECT
        id,
        changed_at
    FROM latest_changes
    WHERE
        changed_at > %(cursor_timestamp)s::timestamp
        OR (
            changed_at = %(cursor_timestamp)s::timestamp
            AND id > %(cursor_id)s::uuid
        )
    ORDER BY changed_at, id
    LIMIT %(limit)s
"""


# Запрос для получения полных данных жанров для загрузки
# Возвращает только жанры, привязанные к фильмам
GENRE_PAYLOAD_QUERY = """
    SELECT
        g.id,
        g.name,
        g.description
    FROM content.genre g
    WHERE
        g.id = ANY(%(genre_ids)s)
        AND EXISTS (
            SELECT 1
            FROM content.genre_film_work gfw
            WHERE gfw.genre_id = g.id
        )
    ORDER BY g.id
"""


# Запрос для получения полных данных людей для загрузки
# Возвращает только людей, участвующих в фильмах, с агрегированными данными
# о фильмах
PERSON_PAYLOAD_QUERY = """
    SELECT
        p.id,
        p.full_name,
        COALESCE(film_data.films, '[]'::jsonb) AS films
    FROM content.person p
    LEFT JOIN (
        SELECT
            person_id,
            JSONB_AGG(
                JSONB_BUILD_OBJECT(
                    'id', film_work_id,
                    'roles', TO_JSONB(roles)
                )
                ORDER BY film_work_id
            ) AS films
        FROM (
            SELECT
                person_id,
                film_work_id,
                ARRAY_AGG(DISTINCT role ORDER BY role) AS roles
            FROM content.person_film_work
            GROUP BY person_id, film_work_id
        ) person_films
        GROUP BY person_id
    ) film_data ON film_data.person_id = p.id
    WHERE
        p.id = ANY(%(person_ids)s)
        AND EXISTS (
            SELECT 1
            FROM content.person_film_work pfw
            WHERE pfw.person_id = p.id
        )
    ORDER BY p.id
"""
