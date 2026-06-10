"""Repository-level configuration defaults."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

HISTORICAL_SEASONS = tuple(f"{year}-{str(year + 1)[-2:]}" for year in range(2015, 2026))
SEASON_TYPES = ("Regular Season", "Playoffs")

