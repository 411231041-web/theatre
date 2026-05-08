"""Управление состоянием ETL-конвейера для отслеживания прогресса."""

import json
from typing import Dict, Any
from pathlib import Path

from .logger import logger


class State:
    """Класс для управления сохранением состояния ETL."""

    def __init__(self, state_file: str):
        """
        Инициализируем менеджер состояния.

        Args:
            state_file: Путь к JSON-файлу для хранения состояния
        """
        self.state_file = Path(state_file)
        self._state: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """
        Загружаем состояние из файла, если он существует.

        Returns:
            Словарь состояния или пустой словарь, если файл отсутствует
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    "Failed to load state file %s: %s. Starting fresh.",
                    self.state_file,
                    e,
                )
                return {}
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получаем значение состояния по ключу.

        Args:
            key: Ключ состояния
            default: Значение по умолчанию, если ключ не найден

        Returns:
            Значение состояния или default
        """
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Установаем значение состояния и сохраняем в файл.

        Args:
            key: Ключ состояния
            value: Сохраняемое значение
        """
        self._state[key] = value
        self._save_state()

    def update(self, data: Dict[str, Any]) -> None:
        """
        Обновляем несколько значений состояния за один вызов.

        Args:
            data: Словарь пар ключ-значение для обновления
        """
        self._state.update(data)
        self._save_state()

    def _save_state(self) -> None:
        """Сохраняем состояние в файл."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.state_file.with_suffix(
                f"{self.state_file.suffix}.tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, default=str)
            temp_file.replace(self.state_file)
        except IOError as e:
            logger.error("Failed to save state file %s: %s",
                         self.state_file, e)

    def get_cursor_timestamp(self) -> str:
        """Получаем текущую метку времени инкрементального курсора."""
        return str(self.get("cursor_timestamp", "1970-01-01T00:00:00"))

    def get_cursor_id(self) -> str:
        """Получаем ID фильма курсора для разрешения совпадений по времени."""
        default_cursor_id = "00000000-0000-0000-0000-000000000000"
        return str(self.get("cursor_id", default_cursor_id))

    def set_cursor(self, cursor_timestamp: str, cursor_id: str) -> None:
        """Обновляем курсор только после успешной массовой записи."""
        self.update(
            {
                "cursor_timestamp": cursor_timestamp,
                "cursor_id": cursor_id,
            }
        )
