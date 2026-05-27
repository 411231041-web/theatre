"""Утилиты повторных попыток и backoff для ETL-конвейера."""

import time
import random
from typing import Callable, Any
from .logger import logger


class RetryConfig:
    """Конфигурация логики повторных попыток."""

    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
    ):
        """Инициализируем конфигурацию повторных попыток."""
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier

    def execute_with_retry(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Выполняем функцию с логикой повторных попыток.

        Args:
            func: Функция для выполнения
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции

        Returns:
            Результат функции

        Raises:
            Последнее исключение, если все попытки исчерпаны
        """
        delay = self.initial_delay
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    # Добавляем случайное отклонение: delay * (0.5 до 1.5)
                    actual_delay = delay * (0.5 + random.random())
                    actual_delay = min(actual_delay, self.max_delay)

                    logger.warning(
                        "Attempt "
                        f"{attempt + 1}/{self.max_retries + 1} "
                        f"failed: {e}. "
                        f"Retrying in {actual_delay:.2f}s..."
                    )
                    time.sleep(actual_delay)
                    delay = min(delay * self.multiplier, self.max_delay)
                else:
                    logger.error(
                        f"All {self.max_retries + 1} attempts failed: {e}"
                    )

        raise last_exception
