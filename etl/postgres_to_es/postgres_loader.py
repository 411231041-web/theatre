"""Загрузчик данных из PostgreSQL для ETL-конвейера."""

from typing import List, Dict, Any, Tuple
import psycopg
from .logger import logger
from .backoff import RetryConfig
from . import queries


class PostgresLoader:
    """Загружает данные из базы PostgreSQL."""

    def __init__(self, dsn: str, retry_config: RetryConfig):
        """
        Инициализируем загрузчик PostgreSQL.

        Args:
            dsn: DSN подключения к PostgreSQL
            retry_config: Экземпляр RetryConfig для повторных попыток
        """
        self.dsn = dsn
        self.retry_config = retry_config
        self._conn = None

    def connect(self) -> None:
        """Устанавливаем соединение с PostgreSQL."""
        def _connect():
            self._conn = psycopg.connect(self.dsn)
            logger.info("Connected to PostgreSQL")

        self.retry_config.execute_with_retry(_connect)

    def close(self) -> None:
        """Закрываем соединение с PostgreSQL."""
        if self._conn:
            self._conn.close()
            logger.info("Closed PostgreSQL connection")

    def get_changed_films(
        self,
        cursor_timestamp: str,
        cursor_id: str,
        batch_size: int = 100,
    ) -> List[Tuple[str, str]]:
        """
        Получаем ID фильмов и метки времени, измененные после курсора.

        Args:
            cursor_timestamp: Время курсора в формате ISO
            cursor_id: UUID курсора для разрешения совпадений по времени
            batch_size: Количество ID фильмов для выборки

        Returns:
            Список кортежей (film_id, changed_at_iso)
        """
        def _get_changed_films():
            if not self._conn:
                self.connect()

            cursor = self._conn.cursor()
            cursor.execute(
                queries.CHANGED_FILMS_QUERY,
                {
                    "cursor_timestamp": cursor_timestamp,
                    "cursor_id": cursor_id,
                    "limit": batch_size,
                }
            )
            rows = cursor.fetchall()
            cursor.close()

            return [(str(row[0]), row[1].isoformat()) for row in rows]

        return self.retry_config.execute_with_retry(_get_changed_films)

    def get_films_data(self, film_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Получаем полные данные фильмов для заданных ID.

        Args:
            film_ids: Список UUID фильмов

        Returns:
            Список словарей с данными фильмов
        """
        if not film_ids:
            return []

        def _get_data():
            if not self._conn:
                self.connect()

            cursor = self._conn.cursor()
            cursor.execute(
                queries.FILM_PAYLOAD_QUERY,
                {"film_ids": film_ids}
            )
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            return [dict(zip(columns, row)) for row in rows]

        return self.retry_config.execute_with_retry(_get_data)

    def get_changed_genres(
        self,
        cursor_timestamp: str,
        cursor_id: str,
        batch_size: int = 100,
    ) -> List[Tuple[str, str]]:
        """
        Получаем ID жанров и метки времени, измененные после курсора.

        Args:
            cursor_timestamp: Время курсора в формате ISO
            cursor_id: UUID курсора для разрешения совпадений по времени
            batch_size: Количество ID жанров для выборки

        Returns:
            Список кортежей (genre_id, changed_at_iso)
        """

        def _get_changed_genres():
            if not self._conn:
                self.connect()

            cursor = self._conn.cursor()
            cursor.execute(
                queries.CHANGED_GENRES_QUERY,
                {
                    "cursor_timestamp": cursor_timestamp,
                    "cursor_id": cursor_id,
                    "limit": batch_size,
                }
            )
            rows = cursor.fetchall()
            cursor.close()

            return [(str(row[0]), row[1].isoformat()) for row in rows]

        return self.retry_config.execute_with_retry(_get_changed_genres)

    def get_genres_data(self, genre_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Получаем полные данные жанров для заданных ID.

        Args:
            genre_ids: Список UUID жанров

        Returns:
            Список словарей с данными жанров
        """
        if not genre_ids:
            return []

        def _get_data():
            if not self._conn:
                self.connect()

            cursor = self._conn.cursor()
            cursor.execute(
                queries.GENRE_PAYLOAD_QUERY,
                {"genre_ids": genre_ids}
            )
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            return [dict(zip(columns, row)) for row in rows]

        return self.retry_config.execute_with_retry(_get_data)

    def get_changed_persons(
        self,
        cursor_timestamp: str,
        cursor_id: str,
        batch_size: int = 100,
    ) -> List[Tuple[str, str]]:
        """
        Получаем ID людей и метки времени, измененные после курсора.

        Args:
            cursor_timestamp: Время курсора в формате ISO
            cursor_id: UUID курсора для разрешения совпадений по времени
            batch_size: Количество ID людей для выборки

        Returns:
            Список кортежей (person_id, changed_at_iso)
        """

        def _get_changed_persons():
            if not self._conn:
                self.connect()

            cursor = self._conn.cursor()
            cursor.execute(
                queries.CHANGED_PERSONS_QUERY,
                {
                    "cursor_timestamp": cursor_timestamp,
                    "cursor_id": cursor_id,
                    "limit": batch_size,
                }
            )
            rows = cursor.fetchall()
            cursor.close()

            return [(str(row[0]), row[1].isoformat()) for row in rows]

        return self.retry_config.execute_with_retry(_get_changed_persons)

    def get_persons_data(self, person_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Получаем полные данные людей для заданных ID.

        Args:
            person_ids: Список UUID людей

        Returns:
            Список словарей с данными людей
        """
        if not person_ids:
            return []

        def _get_data():
            if not self._conn:
                self.connect()

            cursor = self._conn.cursor()
            cursor.execute(
                queries.PERSON_PAYLOAD_QUERY,
                {"person_ids": person_ids}
            )
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            return [dict(zip(columns, row)) for row in rows]

        return self.retry_config.execute_with_retry(_get_data)
