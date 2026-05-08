"""Настройки и маппинги индекса Elasticsearch."""

import json
from pathlib import Path


# Файл настроек лежит в корне папки etl.
# Путь считаем относительно текущего модуля.
_ES_INDEX_SETTINGS_PATH = (
    Path(__file__).resolve().parents[1] / "es_films_index_settings.json"
)

# Загружаем настройки индекса из JSON.
with _ES_INDEX_SETTINGS_PATH.open(encoding="utf-8") as settings_file:
    ES_FILMS_INDEX_SETTINGS = json.load(settings_file)
