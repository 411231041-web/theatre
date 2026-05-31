"""Оркестрация ETL-конвейера для индекса persons."""

import time

from .backoff import RetryConfig
from .config import get_settings
from .es_saver import ElasticsearchSaver
from .logger import logger
from .persons_es_settings import ES_PERSONS_INDEX_SETTINGS
from .postgres_loader import PostgresLoader
from .state import State
from .transformer import transform_persons_batch


class PersonsETLPipeline:
    """Инкрементальный ETL-конвейер синхронизации людей в Elasticsearch."""

    def __init__(self):
        """Инициализируем ETL-конвейер с настройками и компонентами."""
        self.settings = get_settings()

        self.retry_config = RetryConfig(
            max_retries=self.settings.max_retries,
            initial_delay=self.settings.initial_backoff,
            max_delay=self.settings.max_backoff,
            multiplier=self.settings.backoff_multiplier,
        )

        self.state = State(self.settings.etl_state_file)
        self.postgres_loader = PostgresLoader(
            self.settings.postgres_dsn,
            self.retry_config,
        )
        self.es_saver = ElasticsearchSaver(
            self.settings.elasticsearch_url,
            self.settings.elasticsearch_persons_index,
            self.retry_config,
        )

    def setup(self) -> None:
        """Подготавливаем ETL: подключаемся к сервисам и проверяем индекс."""
        logger.info("Setting up persons ETL pipeline...")
        self.postgres_loader.connect()
        self.es_saver.connect()
        self.es_saver.ensure_index_exists(ES_PERSONS_INDEX_SETTINGS)
        logger.info("Persons ETL pipeline setup complete")

    def cleanup(self) -> None:
        """Закрываем все соединения."""
        logger.info("Cleaning up persons ETL pipeline...")
        self.postgres_loader.close()
        self.es_saver.close()

    def sync_once(self) -> int:
        """Синхронизируем изменения и возвращаем число обработанных записей."""
        processed_total = 0
        cursor_timestamp = self.state.get_cursor_timestamp()
        cursor_id = self.state.get_cursor_id()

        while True:
            changed_batch = self.postgres_loader.get_changed_persons(
                cursor_timestamp=cursor_timestamp,
                cursor_id=cursor_id,
                batch_size=self.settings.batch_size,
            )

            if not changed_batch:
                return processed_total

            person_ids = [person_id for person_id, _ in changed_batch]
            persons_data = self.postgres_loader.get_persons_data(person_ids)
            documents = transform_persons_batch(persons_data)

            if documents:
                written_count = self.es_saver.bulk_write(documents)
                processed_total += written_count

            last_person_id, last_changed_at = changed_batch[-1]
            self.state.set_cursor(last_changed_at, last_person_id)
            cursor_timestamp = last_changed_at
            cursor_id = last_person_id

            logger.info(
                "Processed persons batch: %s docs. Cursor moved to (%s, %s)",
                len(documents),
                cursor_timestamp,
                cursor_id,
            )

    def run_continuous(self) -> None:
        """Запускаем ETL-конвейер в непрерывном режиме (опрос)."""
        logger.info(
            "Starting continuous persons ETL mode (polling every %ss)",
            self.settings.poll_interval,
        )

        try:
            while True:
                try:
                    total_synced = self.sync_once()
                    if total_synced:
                        logger.info(
                            (
                                "Persons sync cycle completed, "
                                "documents indexed: %s"
                            ),
                            total_synced,
                        )
                    else:
                        logger.debug("No persons changes detected")
                except Exception as e:
                    logger.error("Error in persons ETL cycle: %s", e)

                logger.debug(
                    "Waiting %ss for next persons poll...",
                    self.settings.poll_interval,
                )
                time.sleep(self.settings.poll_interval)

        except KeyboardInterrupt:
            logger.info("Persons ETL pipeline interrupted by user")


def main() -> None:
    logger.info("=" * 50)
    logger.info("Starting Persons ETL Pipeline")
    logger.info("=" * 50)

    pipeline = PersonsETLPipeline()

    try:
        pipeline.setup()
        pipeline.run_continuous()
    except KeyboardInterrupt:
        logger.info("Persons pipeline interrupted")
    except Exception as e:
        logger.error(
            "Fatal error in persons ETL pipeline: %s",
            e,
            exc_info=True,
        )
        raise
    finally:
        pipeline.cleanup()
        logger.info("Persons ETL Pipeline stopped")


if __name__ == "__main__":
    main()
