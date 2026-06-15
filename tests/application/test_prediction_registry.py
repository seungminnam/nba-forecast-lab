from datetime import datetime, timezone

import pandas as pd
import pytest

from nba_forecast.application.matchup_prediction import MatchupPredictionOutput
from nba_forecast.application.prediction_registry import (
    empty_prediction_registry,
    prediction_to_record,
    validate_prediction_registry,
)
from nba_forecast.features.matchup_features import ScheduledMatchup


def test_prediction_to_record_is_deterministic_and_unsettled() -> None:
    first = prediction_to_record(_prediction())
    second = prediction_to_record(_prediction())

    assert first == second
    assert first["game_id"] == "scheduled-1"
    assert first["prediction_timestamp"] == pd.Timestamp("2026-10-20T12:00:00Z")
    assert first["features_json"] == '{"elo_diff":12.5,"rest_days_diff":1.0}'
    assert first["final_outcome"] is pd.NA
    assert first["settled_at"] is pd.NaT
    assert first["brier_contribution"] is pd.NA
    assert first["is_correct"] is pd.NA
    assert len(str(first["prediction_id"])) == 64
    assert len(str(first["payload_fingerprint"])) == 64


def test_validate_prediction_registry_accepts_empty_and_valid_tables() -> None:
    empty = empty_prediction_registry()
    populated = pd.DataFrame([prediction_to_record(_prediction())])

    validate_prediction_registry(empty)
    validate_prediction_registry(populated)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda frame: pd.concat([frame, frame], ignore_index=True),
            "duplicate prediction_id",
        ),
        (
            lambda frame: frame.assign(home_win_probability=1.2),
            "probabilities",
        ),
        (
            lambda frame: frame.assign(away_win_probability=0.5),
            "sum to one",
        ),
        (
            lambda frame: frame.assign(
                prediction_timestamp=pd.Timestamp("2026-10-20 12:00:00")
            ),
            "timezone-aware",
        ),
        (
            lambda frame: frame.assign(features_json="{invalid"),
            "features_json",
        ),
        (
            lambda frame: frame.assign(final_outcome=1),
            "settlement fields",
        ),
        (
            lambda frame: frame.assign(
                final_outcome=2,
                settled_at=pd.Timestamp("2026-10-22T12:00:00Z"),
                brier_contribution=0.16,
                is_correct=1,
            ),
            "final_outcome",
        ),
    ],
)
def test_validate_prediction_registry_rejects_invalid_tables(
    mutate: object,
    message: str,
) -> None:
    registry = pd.DataFrame([prediction_to_record(_prediction())])

    with pytest.raises(ValueError, match=message):
        validate_prediction_registry(mutate(registry))  # type: ignore[operator]


def test_validate_prediction_registry_rejects_schema_changes() -> None:
    registry = empty_prediction_registry()

    with pytest.raises(ValueError, match="columns"):
        validate_prediction_registry(registry.drop(columns=["game_id"]))

    with pytest.raises(ValueError, match="columns"):
        validate_prediction_registry(registry.assign(unexpected="value"))


def _prediction() -> MatchupPredictionOutput:
    return MatchupPredictionOutput(
        matchup=ScheduledMatchup(
            game_id="scheduled-1",
            game_date=pd.Timestamp("2026-10-22"),
            season_id="22026",
            season_type="Regular Season",
            season_key="2026-27",
            home_team_id=1,
            away_team_id=2,
            home_team_abbreviation="HOM",
            away_team_abbreviation="AWY",
        ),
        prediction_timestamp=datetime(2026, 10, 20, 12, tzinfo=timezone.utc),
        as_of_date=pd.Timestamp("2026-10-20"),
        model_version="model-a",
        feature_version="features-v1",
        home_win_probability=0.6,
        away_win_probability=0.4,
        feature_row=pd.DataFrame(
            [{"rest_days_diff": 1.0, "elo_diff": 12.5}]
        ),
        feature_columns=("elo_diff", "rest_days_diff"),
    )
