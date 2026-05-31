#!/bin/bash
# Удаляет кэши и временные папки Python в проекте

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Очистка проекта от .pytest_cache и __pycache__..."

# Удаляем .pytest_cache
find "$SCRIPT_DIR" -type d -name ".pytest_cache" -exec rm -rfv {} + 2>/dev/null || true

# Удаляем __pycache__
find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rfv {} + 2>/dev/null || true

echo "✓ Очистка завершена успешно"
