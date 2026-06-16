"""Application workflow for once-daily scheduled game predictions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

import pandas as pd

from nba_forecast.application.matchup_prediction import (
    MatchupPredictionOutput,
    predict_scheduled_matchup,
)
from nba_forecast.application.prediction_registry import (
    register_prediction,
    validate_prediction_registry,
)
from nba_forecast.data.schedule_transform import validate_scheduled_matchups
from nba_forecast.features.matchup_features import ScheduledMatchup
from nba_forecast.models.artifacts import ModelBundle


@dataclass(frozen=True)
class DailyPredictionsOutput:
    """Auditable result for one atomic daily prediction batch."""

    prediction_date: date
    prediction_timestamp: datetime
    schedule_snapshot_at_utc: datetime
    total_schedule_rows: int
    eligible_game_count: int
    excluded_game_count: int
    predictions: tuple[MatchupPredictionOutput, ...]
    registry: pd.DataFrame

    def prediction_reports(self) -> list[dict[str, object]]:
        """Return each prediction report in deterministic batch order."""
        return [prediction.to_report() for prediction in self.predictions]

    def to_report(self) -> dict[str, object]:
        """Return a JSON-serializable daily batch report."""
        return {
            "prediction_date": self.prediction_date.isoformat(),
            "prediction_timestamp": self.prediction_timestamp.isoformat(),
            "schedule_snapshot_at_utc": self.schedule_snapshot_at_utc.isoformat(),
            "total_schedule_rows": self.total_schedule_rows,
            "eligible_game_count": self.eligible_game_count,
            "excluded_game_count": self.excluded_game_count,
            "predictions": self.prediction_reports(),
        }


def select_daily_matchups(
    schedule: pd.DataFrame,
    *,
    prediction_date: date,
    prediction_timestamp: datetime,
) -> pd.DataFrame:
    """Return schedule rows eligible for one daily pre-tipoff prediction batch."""
    validate_scheduled_matchups(schedule)
    timestamp = _utc_datetime(prediction_timestamp, "prediction_timestamp")
    if schedule.empty:
        return schedule.copy()

    tipoffs = pd.to_datetime(schedule["tipoff_at_utc"], utc=True, errors="coerce")
    game_dates = pd.to_datetime(schedule["nba_game_date"], errors="raise").dt.date
    eligible = schedule.loc[
        (game_dates == prediction_date)
        & (schedule["game_status"].astype(int) == 1)
        & (~schedule["is_postponed"].astype(bool))
        & (~schedule["is_conditional"].astype(bool))
        & (schedule["has_confirmed_matchup"].astype(bool))
        & tipoffs.notna()
        & (tipoffs > pd.Timestamp(timestamp))
    ].copy()
    eligible["_sort_tipoff_at_utc"] = tipoffs.loc[eligible.index]
    eligible = eligible.sort_values(
        ["_sort_tipoff_at_utc", "game_id"],
        ignore_index=True,
    ).drop(columns=["_sort_tipoff_at_utc"])
    return eligible


def run_daily_predictions(
    schedule: pd.DataFrame,
    completed_games: pd.DataFrame,
    registry: pd.DataFrame,
    bundle: ModelBundle,
    *,
    prediction_date: date,
    prediction_timestamp: datetime,
) -> DailyPredictionsOutput:
    """Score and register every eligible scheduled game for one NBA date."""
    validate_scheduled_matchups(schedule)
    validate_prediction_registry(registry)
    timestamp = _utc_datetime(prediction_timestamp, "prediction_timestamp")
    schedule_snapshot_at_utc = _single_schedule_snapshot_at(schedule)
    eligible = select_daily_matchups(
        schedule,
        prediction_date=prediction_date,
        prediction_timestamp=timestamp,
    )

    candidate_registry = registry.copy(deep=True)
    predictions: list[MatchupPredictionOutput] = []
    for _, row in eligible.iterrows():
        prediction = predict_scheduled_matchup(
            completed_games,
            _row_to_scheduled_matchup(row),
            as_of_date=pd.Timestamp(prediction_date),
            bundle=bundle,
            prediction_timestamp=timestamp,
        )
        candidate_registry = register_prediction(
            candidate_registry,
            prediction,
        ).registry
        predictions.append(prediction)

    return DailyPredictionsOutput(
        prediction_date=prediction_date,
        prediction_timestamp=timestamp,
        schedule_snapshot_at_utc=schedule_snapshot_at_utc,
        total_schedule_rows=len(schedule),
        eligible_game_count=len(eligible),
        excluded_game_count=len(schedule) - len(eligible),
        predictions=tuple(predictions),
        registry=candidate_registry,
    )


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return value.astimezone(timezone.utc)


def _single_schedule_snapshot_at(schedule: pd.DataFrame) -> datetime:
    if schedule.empty:
        raise ValueError("daily predictions require a non-empty schedule")
    snapshots = pd.to_datetime(
        schedule["schedule_snapshot_at_utc"],
        utc=True,
        errors="raise",
    ).drop_duplicates()
    if len(snapshots) != 1:
        raise ValueError("daily predictions require exactly one schedule snapshot")
    return pd.Timestamp(snapshots.iloc[0]).to_pydatetime()


def _row_to_scheduled_matchup(row: pd.Series) -> ScheduledMatchup:
    return ScheduledMatchup(
        game_id=str(row["game_id"]),
        game_date=pd.Timestamp(row["nba_game_date"]).normalize(),
        season_id=str(row["season_id"]),
        season_type=str(row["season_type"]),
        season_key=str(row["season_key"]),
        home_team_id=int(row["home_team_id"]),
        away_team_id=int(row["away_team_id"]),
        home_team_abbreviation=str(row["home_team_abbreviation"]),
        away_team_abbreviation=str(row["away_team_abbreviation"]),
    )
