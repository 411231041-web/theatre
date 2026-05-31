"""Основная оркестрация ETL-конвейера."""

import time
from .config import get_settings
from .logger import logger
from .state import State
from .backoff import RetryConfig
from .postgres_loader import PostgresLoader
from .transformer import transform_batch
from .es_saver import ElasticsearchSaver
from .films_es_settings import ES_FILMS_INDEX_SETTINGS


class FilmsETLPipeline:
    """Основной ETL-конвейер синхронизации фильмов в Elasticsearch."""

    def __init__(self):
        """Инициализируем ETL-конвейер с настройками и компонентами."""
        self.settings = get_settings()

        # Инициализируем конфигурацию повторных попыток
        self.retry_config = RetryConfig(
            max_retries=self.settings.max_retries,
            initial_delay=self.settings.initial_backoff,
            max_delay=self.settings.max_backoff,
            multiplier=self.settings.backoff_multiplier,
        )

        # Инициализируем компоненты
        self.state = State(self.settings.etl_state_file)
        self.postgres_loader = PostgresLoader(
            self.settings.postgres_dsn, self.retry_config
        )
        self.es_saver = ElasticsearchSaver(
            self.settings.elasticsearch_url,
            self.settings.elasticsearch_films_index,
            self.retry_config,
        )

    def setup(self) -> None:
        """Подготавливаем ETL: подключаемся к сервисам и проверяем индекс."""
        logger.info("Setting up films ETL pipeline...")

        # Подключаемся к PostgreSQL
        self.postgres_loader.connect()

        # Подключаемся к Elasticsearch и проверяем существование индекса
        self.es_saver.connect()
        self.es_saver.ensure_index_exists(ES_FILMS_INDEX_SETTINGS)

        logger.info("Films ETL pipeline setup complete")

    def cleanup(self) -> None:
        """Закрываем все соединения."""
        logger.info("Cleaning up films ETL pipeline...")
        self.postgres_loader.close()
        self.es_saver.close()

    def sync_once(self) -> int:
        """Синхронизируем изменения и возвращаем число обработанных записей."""
        processed_total = 0
        cursor_timestamp = self.state.get_cursor_timestamp()
        cursor_id = self.state.get_cursor_id()

        while True:
            changed_batch = self.postgres_loader.get_changed_films(
                cursor_timestamp=cursor_timestamp,
                cursor_id=cursor_id,
                batch_size=self.settings.batch_size,
            )

            if not changed_batch:
                return processed_total

            film_ids = [film_id for film_id, _ in changed_batch]
            films_data = self.postgres_loader.get_films_data(film_ids)
            documents = transform_batch(films_data)

            if documents:
                written_count = self.es_saver.bulk_write(documents)
                processed_total += written_count

            last_film_id, last_changed_at = changed_batch[-1]
            self.state.set_cursor(last_changed_at, last_film_id)
            cursor_timestamp = last_changed_at
            cursor_id = last_film_id

            logger.info(
                "Processed batch: %s docs. Cursor moved to (%s, %s)",
                len(documents),
                cursor_timestamp,
                cursor_id,
            )

    def run_continuous(self) -> None:
        """Запускаем ETL-конвейер в непрерывном режиме (опрос)."""
        logger.info(
            "Starting continuous ETL mode (polling every %ss)",
            self.settings.poll_interval,
        )

        try:
            while True:
                try:
                    total_synced = self.sync_once()
                    if total_synced:
                        logger.info(
                            "Sync cycle completed, documents indexed: %s",
                            total_synced,
                        )
                    else:
                        logger.debug("No changes detected")

                except Exception as e:
                    logger.error(f"Error in ETL cycle: {e}")

                # Ожидаем перед следующим опросом
                logger.debug(
                    "Waiting %ss for next poll...",
                    self.settings.poll_interval,
                )
                time.sleep(self.settings.poll_interval)

        except KeyboardInterrupt:
            logger.info("ETL pipeline interrupted by user")


def main() -> None:
    logger.info("=" * 50)
    logger.info("Starting Films ETL Pipeline")
    logger.info("=" * 50)

    pipeline = FilmsETLPipeline()

    try:
        pipeline.setup()
        pipeline.run_continuous()
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted")
    except Exception as e:
        logger.error(f"Fatal error in films ETL pipeline: {e}", exc_info=True)
        raise
    finally:
        pipeline.cleanup()
        logger.info("Films ETL Pipeline stopped")


if __name__ == "__main__":
    main()
