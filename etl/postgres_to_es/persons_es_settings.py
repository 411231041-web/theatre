"""Настройки и маппинги индекса persons в Elasticsearch."""

import json
from pathlib import Path


_ES_PERSONS_INDEX_SETTINGS_PATH = (
    Path(__file__).resolve().parents[1] / "es_persons_index_settings.json"
)

with _ES_PERSONS_INDEX_SETTINGS_PATH.open(encoding="utf-8") as settings_file:
    ES_PERSONS_INDEX_SETTINGS = json.load(settings_file)
