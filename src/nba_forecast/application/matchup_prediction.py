"""Application workflow for one frozen-model scheduled matchup prediction."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from nba_forecast.features.game_features import MODEL_FEATURE_VERSION
from nba_forecast.features.matchup_features import (
    ScheduledMatchup,
    build_scheduled_matchup_features,
)
from nba_forecast.models.artifacts import ModelBundle


@dataclass(frozen=True)
class MatchupPredictionOutput:
    """Auditable prediction and the exact feature row used to produce it."""

    matchup: ScheduledMatchup
    prediction_timestamp: datetime
    as_of_date: pd.Timestamp
    model_version: str
    feature_version: str
    home_win_probability: float
    away_win_probability: float
    feature_row: pd.DataFrame
    feature_columns: tuple[str, ...]
    final_outcome: Optional[int] = None

    def to_report(self) -> dict[str, object]:
        """Return a JSON-serializable prediction report."""
        features = self.feature_row.iloc[0][list(self.feature_columns)]
        return {
            "prediction_timestamp": self.prediction_timestamp.isoformat(),
            "as_of_date": self.as_of_date.date().isoformat(),
            "matchup": {
                "game_id": self.matchup.game_id,
                "game_date": pd.Timestamp(self.matchup.game_date).date().isoformat(),
                "season_id": self.matchup.season_id,
                "home_team_id": self.matchup.home_team_id,
                "away_team_id": self.matchup.away_team_id,
                "home_team_abbreviation": self.matchup.home_team_abbreviation,
                "away_team_abbreviation": self.matchup.away_team_abbreviation,
            },
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "home_win_probability": self.home_win_probability,
            "away_win_probability": self.away_win_probability,
            "final_outcome": self.final_outcome,
            "features": {
                feature: _json_value(features[feature])
                for feature in self.feature_columns
            },
        }


def predict_scheduled_matchup(
    completed_games: pd.DataFrame,
    matchup: ScheduledMatchup,
    *,
    as_of_date: pd.Timestamp,
    bundle: ModelBundle,
    prediction_timestamp: Optional[datetime] = None,
) -> MatchupPredictionOutput:
    """Build one as-of feature row and score it with a frozen model bundle."""
    cutoff = pd.Timestamp(as_of_date).normalize()
    timestamp = prediction_timestamp or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("prediction_timestamp must include a timezone")
    timestamp = timestamp.astimezone(timezone.utc)
    feature_row = build_scheduled_matchup_features(
        completed_games,
        matchup,
        as_of_date=cutoff,
    )
    home_probability = float(bundle.predict_probability(feature_row).iloc[0])
    return MatchupPredictionOutput(
        matchup=matchup,
        prediction_timestamp=timestamp,
        as_of_date=cutoff,
        model_version=bundle.metadata.version,
        feature_version=MODEL_FEATURE_VERSION,
        home_win_probability=home_probability,
        away_win_probability=1.0 - home_probability,
        feature_row=feature_row,
        feature_columns=bundle.metadata.feature_columns,
    )


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value
