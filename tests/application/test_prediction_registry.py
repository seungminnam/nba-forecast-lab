from dataclasses import replace
from datetime import datetime, timezone

import pandas as pd
import pytest

from nba_forecast.application.matchup_prediction import MatchupPredictionOutput
from nba_forecast.application.prediction_registry import (
    IMMUTABLE_REGISTRY_COLUMNS,
    build_prediction_registry_report,
    empty_prediction_registry,
    prediction_to_record,
    register_prediction,
    settle_predictions,
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


def test_register_prediction_is_idempotent_for_the_same_event() -> None:
    first = register_prediction(empty_prediction_registry(), _prediction())
    repeated = register_prediction(first.registry, _prediction())

    assert first.status == "registered"
    assert repeated.status == "already_registered"
    assert repeated.prediction_id == first.prediction_id
    assert len(repeated.registry) == 1


def test_register_prediction_rejects_conflict_for_the_same_identity() -> None:
    registered = register_prediction(empty_prediction_registry(), _prediction())
    changed = replace(
        _prediction(),
        home_win_probability=0.7,
        away_win_probability=0.3,
    )

    with pytest.raises(ValueError, match="conflicting"):
        register_prediction(registered.registry, changed)


def test_register_prediction_preserves_other_times_and_models() -> None:
    registry = register_prediction(
        empty_prediction_registry(),
        _prediction(),
    ).registry
    another_time = replace(
        _prediction(),
        prediction_timestamp=datetime(2026, 10, 20, 13, tzinfo=timezone.utc),
    )
    another_model = replace(_prediction(), model_version="model-b")

    registry = register_prediction(registry, another_time).registry
    registry = register_prediction(registry, another_model).registry

    assert len(registry) == 3
    assert registry["prediction_id"].nunique() == 3


def test_settle_predictions_adds_results_without_changing_prediction_evidence() -> None:
    registry = register_prediction(
        empty_prediction_registry(),
        _prediction(),
    ).registry
    unmatched = replace(
        _prediction(),
        matchup=replace(_prediction().matchup, game_id="scheduled-2"),
    )
    registry = register_prediction(registry, unmatched).registry
    immutable_before = registry.loc[:, list(IMMUTABLE_REGISTRY_COLUMNS)].copy(
        deep=True
    )

    result = settle_predictions(
        registry,
        _completed_games(),
        settled_at=datetime(2026, 10, 22, 23, tzinfo=timezone.utc),
    )

    pd.testing.assert_frame_equal(
        immutable_before,
        result.registry.loc[:, list(IMMUTABLE_REGISTRY_COLUMNS)],
    )
    assert result.settled_count == 1
    assert result.already_settled_count == 0
    assert result.unmatched_count == 1
    settled = result.registry.loc[result.registry["game_id"] == "scheduled-1"].iloc[0]
    assert settled["final_outcome"] == 1
    assert settled["brier_contribution"] == pytest.approx((0.6 - 1) ** 2)
    assert settled["is_correct"] == 1
    assert settled["settled_at"] == pd.Timestamp("2026-10-22T23:00:00Z")
    unmatched_row = result.registry.loc[
        result.registry["game_id"] == "scheduled-2"
    ].iloc[0]
    assert pd.isna(unmatched_row["final_outcome"])


def test_settle_predictions_is_idempotent_for_the_same_outcome() -> None:
    registry = register_prediction(
        empty_prediction_registry(),
        _prediction(),
    ).registry
    first = settle_predictions(
        registry,
        _completed_games(),
        settled_at=datetime(2026, 10, 22, 23, tzinfo=timezone.utc),
    )
    repeated = settle_predictions(
        first.registry,
        _completed_games(),
        settled_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
    )

    pd.testing.assert_frame_equal(repeated.registry, first.registry)
    assert repeated.settled_count == 0
    assert repeated.already_settled_count == 1
    assert repeated.unmatched_count == 0


def test_settle_predictions_rejects_team_and_outcome_conflicts() -> None:
    registry = register_prediction(
        empty_prediction_registry(),
        _prediction(),
    ).registry
    mismatched_teams = _completed_games().assign(home_team_id=99)

    with pytest.raises(ValueError, match="team identity"):
        settle_predictions(registry, mismatched_teams)

    settled = settle_predictions(registry, _completed_games()).registry
    conflicting_outcome = _completed_games().assign(home_win=0)
    with pytest.raises(ValueError, match="conflicting outcome"):
        settle_predictions(settled, conflicting_outcome)


def test_build_prediction_registry_report_separates_counts_and_model_metrics() -> None:
    report = build_prediction_registry_report(_registry_for_report())

    assert report.summary.to_dict("records") == [
        {
            "total_predictions": 3,
            "settled_predictions": 2,
            "unsettled_predictions": 1,
        }
    ]
    assert report.metrics["scope"].tolist() == [
        "all_models",
        "model:model-a",
        "model:model-b",
    ]
    assert report.metrics["predictions"].tolist() == [2, 1, 1]
    assert report.metrics.iloc[0]["brier_score"] == pytest.approx(
        ((0.6 - 1) ** 2 + (0.4 - 0) ** 2) / 2
    )
    assert pd.isna(report.metrics.iloc[1]["roc_auc"])


def test_build_prediction_registry_report_handles_no_settled_predictions() -> None:
    empty_report = build_prediction_registry_report(empty_prediction_registry())
    unsettled = register_prediction(
        empty_prediction_registry(),
        _prediction(),
    ).registry
    unsettled_report = build_prediction_registry_report(unsettled)

    assert empty_report.summary.iloc[0].to_dict() == {
        "total_predictions": 0,
        "settled_predictions": 0,
        "unsettled_predictions": 0,
    }
    assert empty_report.metrics.empty
    assert unsettled_report.metrics.empty
    assert empty_report.metrics.columns.tolist() == [
        "scope",
        "model_version",
        "predictions",
        "brier_score",
        "log_loss",
        "expected_calibration_error",
        "roc_auc",
        "accuracy",
    ]


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


def _completed_games() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": "scheduled-1",
                "game_date": pd.Timestamp("2026-10-22"),
                "season_id": "22026",
                "season_type": "Regular Season",
                "season_key": "2026-27",
                "home_team_id": 1,
                "away_team_id": 2,
                "home_team_abbreviation": "HOM",
                "away_team_abbreviation": "AWY",
                "home_points": 110,
                "away_points": 100,
                "home_fga": 88,
                "away_fga": 90,
                "home_fgm": 42,
                "away_fgm": 39,
                "home_fta": 20,
                "away_fta": 18,
                "home_oreb": 10,
                "away_oreb": 9,
                "home_tov": 12,
                "away_tov": 14,
                "home_win": 1,
            }
        ]
    )


def _registry_for_report() -> pd.DataFrame:
    first = _prediction()
    second = replace(
        _prediction(),
        matchup=replace(_prediction().matchup, game_id="scheduled-2"),
        model_version="model-b",
        home_win_probability=0.4,
        away_win_probability=0.6,
    )
    third = replace(
        _prediction(),
        matchup=replace(_prediction().matchup, game_id="scheduled-3"),
        prediction_timestamp=datetime(2026, 10, 20, 13, tzinfo=timezone.utc),
    )
    registry = empty_prediction_registry()
    for prediction in (first, second, third):
        registry = register_prediction(registry, prediction).registry

    first_game = _completed_games().iloc[0].to_dict()
    second_game = {**first_game, "game_id": "scheduled-2", "home_win": 0}
    return settle_predictions(
        registry,
        pd.DataFrame([first_game, second_game]),
        settled_at=datetime(2026, 10, 22, 23, tzinfo=timezone.utc),
    ).registry
