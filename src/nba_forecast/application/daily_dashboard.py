"""Read-only dashboard helpers for daily prediction artifacts."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

_REPORT_PATTERN = re.compile(r"daily_predictions_(\d{4}-\d{2}-\d{2})\.json$")


class DailyForecastReportError(ValueError):
    """Raised when a daily prediction report cannot be used by the dashboard."""


@dataclass(frozen=True)
class DailyForecastGame:
    game_id: str
    matchup_label: str
    game_date: date
    season_type: str
    model_version: str
    feature_version: str
    home_team_abbreviation: str
    away_team_abbreviation: str
    home_win_probability: float
    away_win_probability: float


@dataclass(frozen=True)
class DailyForecastReport:
    path: Path
    prediction_date: date
    prediction_timestamp: datetime
    schedule_snapshot_at_utc: datetime
    total_schedule_rows: int
    eligible_game_count: int
    excluded_game_count: int
    games: tuple[DailyForecastGame, ...]

    @property
    def prediction_count(self) -> int:
        return len(self.games)

    @property
    def model_versions(self) -> tuple[str, ...]:
        return tuple(sorted({game.model_version for game in self.games}))


def daily_report_path(predictions_dir: Path, prediction_date: date) -> Path:
    return predictions_dir / f"daily_predictions_{prediction_date.isoformat()}.json"


def find_latest_daily_report(predictions_dir: Path) -> Path | None:
    if not predictions_dir.exists():
        return None
    candidates: list[tuple[date, Path]] = []
    for path in predictions_dir.iterdir():
        match = _REPORT_PATTERN.fullmatch(path.name)
        if match is None:
            continue
        candidates.append((date.fromisoformat(match.group(1)), path))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def load_daily_report(path: Path) -> DailyForecastReport:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise DailyForecastReportError(
            f"Could not read daily report: {path}"
        ) from error

    required = (
        "prediction_date",
        "prediction_timestamp",
        "schedule_snapshot_at_utc",
        "total_schedule_rows",
        "eligible_game_count",
        "excluded_game_count",
        "predictions",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise DailyForecastReportError(f"daily report missing fields: {missing}")

    predictions = payload["predictions"]
    if not isinstance(predictions, list):
        raise DailyForecastReportError("daily report predictions must be a list")
    games = tuple(_parse_prediction(prediction) for prediction in predictions)
    return DailyForecastReport(
        path=path,
        prediction_date=date.fromisoformat(str(payload["prediction_date"])),
        prediction_timestamp=_parse_datetime(payload["prediction_timestamp"]),
        schedule_snapshot_at_utc=_parse_datetime(payload["schedule_snapshot_at_utc"]),
        total_schedule_rows=int(payload["total_schedule_rows"]),
        eligible_game_count=int(payload["eligible_game_count"]),
        excluded_game_count=int(payload["excluded_game_count"]),
        games=games,
    )


def _parse_prediction(prediction: Any) -> DailyForecastGame:
    if not isinstance(prediction, dict):
        raise DailyForecastReportError("prediction entries must be objects")
    matchup = prediction.get("matchup")
    if not isinstance(matchup, dict):
        raise DailyForecastReportError("prediction missing matchup object")
    home_probability = float(prediction["home_win_probability"])
    away_probability = float(prediction["away_win_probability"])
    if not math.isclose(home_probability + away_probability, 1.0, abs_tol=1e-9):
        raise DailyForecastReportError("prediction probabilities must sum to one")
    home = str(matchup["home_team_abbreviation"])
    away = str(matchup["away_team_abbreviation"])
    return DailyForecastGame(
        game_id=str(matchup["game_id"]),
        matchup_label=f"{away} at {home}",
        game_date=pd.Timestamp(matchup["game_date"]).date(),
        season_type=str(matchup["season_type"]),
        model_version=str(prediction["model_version"]),
        feature_version=str(prediction["feature_version"]),
        home_team_abbreviation=home,
        away_team_abbreviation=away,
        home_win_probability=home_probability,
        away_win_probability=away_probability,
    )


def _parse_datetime(value: Any) -> datetime:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise DailyForecastReportError("daily report timestamps must be timezone-aware")
    return timestamp.to_pydatetime()
