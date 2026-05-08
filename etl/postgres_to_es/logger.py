"""Конфигурация логирования для ETL-конвейера."""

import logging
import sys


def setup_logger(name: str = "etl") -> logging.Logger:
    """
    Настраиваем и возвращаем экземпляр логгера.

    Args:
        name: Имя логгера

    Returns:
        Настроенный экземпляр логгера
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Удаляем существующие обработчики, чтобы избежать дубликатов
    logger.handlers = []

    # Создаем консольный обработчик с форматированием
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Создаем форматтер
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    # Добавляем обработчик к логгеру
    logger.addHandler(console_handler)

    return logger


# Глобальный экземпляр логгера
logger = setup_logger()
