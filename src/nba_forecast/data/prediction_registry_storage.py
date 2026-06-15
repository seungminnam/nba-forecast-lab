"""Local Parquet and DuckDB persistence for prediction operating records."""

from pathlib import Path

import duckdb
import pandas as pd

from nba_forecast.application.prediction_registry import (
    empty_prediction_registry,
    validate_prediction_registry,
)

PARQUET_FILENAME = "predictions.parquet"
DATABASE_FILENAME = "prediction_registry.duckdb"


def load_prediction_registry(registry_dir: Path) -> pd.DataFrame:
    """Load and validate a registry, or initialize an absent one."""
    parquet_path = registry_dir / PARQUET_FILENAME
    if not parquet_path.exists():
        return empty_prediction_registry()
    registry = pd.read_parquet(parquet_path)
    validate_prediction_registry(registry)
    return registry


def write_prediction_registry(
    registry: pd.DataFrame,
    registry_dir: Path,
) -> tuple[Path, Path]:
    """Atomically persist validated registry rows and synchronize DuckDB."""
    validate_prediction_registry(registry)
    registry_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = registry_dir / PARQUET_FILENAME
    temporary_path = registry_dir / f"{PARQUET_FILENAME}.tmp"
    registry.to_parquet(temporary_path, index=False)
    temporary_path.replace(parquet_path)

    database_path = registry_dir / DATABASE_FILENAME
    with duckdb.connect(str(database_path)) as connection:
        connection.register("predictions_frame", registry)
        connection.execute(
            "CREATE OR REPLACE TABLE predictions AS SELECT * FROM predictions_frame"
        )
    return parquet_path, database_path
