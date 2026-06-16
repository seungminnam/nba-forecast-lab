from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from nba_forecast.application.daily_predictions import (
    run_daily_predictions,
    select_daily_matchups,
)
from nba_forecast.application.matchup_prediction import MatchupPredictionOutput
from nba_forecast.application.prediction_registry import empty_prediction_registry
from nba_forecast.data.schedule_transform import (
    SCHEDULED_MATCHUP_COLUMNS,
    empty_scheduled_matchups,
    schedule_rows_to_matchups,
)
from nba_forecast.features.matchup_features import ScheduledMatchup

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "schedule_league_v2_rows.csv"
SNAPSHOT_AT = datetime(2026, 6, 15, 12, tzinfo=timezone.utc)
PREDICTION_TIMESTAMP = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
PREDICTION_DATE = date(2026, 10, 22)


def _source_schedule() -> pd.DataFrame:
    rows = pd.read_csv(FIXTURE_PATH, dtype={"gameId": "string"})
    return schedule_rows_to_matchups(
        rows,
        season_key="2026-27",
        schedule_snapshot_at_utc=SNAPSHOT_AT,
    )


def _schedule_row(
    game_id: str,
    tipoff_at_utc: str | None,
    *,
    game_status: int = 1,
    is_postponed: bool = False,
    is_conditional: bool = False,
    has_confirmed_matchup: bool = True,
    home_team_id: int | None = 1610612738,
    away_team_id: int | None = 1610612747,
    home_team_abbreviation: str | None = "BOS",
    away_team_abbreviation: str | None = "LAL",
) -> dict[str, object]:
    tipoff = pd.Timestamp(tipoff_at_utc) if tipoff_at_utc is not None else pd.NaT
    if pd.isna(tipoff):
        nba_game_date = pd.Timestamp("2026-10-22")
    else:
        nba_game_date = tipoff.tz_convert("America/New_York").normalize()
        nba_game_date = nba_game_date.tz_localize(None)
    return {
        "game_id": game_id,
        "season_id": "22026",
        "season_type": "Regular Season",
        "season_key": "2026-27",
        "schedule_snapshot_at_utc": pd.Timestamp(SNAPSHOT_AT),
        "nba_game_date": nba_game_date,
        "tipoff_at_utc": tipoff,
        "game_status": game_status,
        "game_status_text": "7:30 pm ET",
        "is_postponed": is_postponed,
        "is_conditional": is_conditional,
        "has_confirmed_matchup": has_confirmed_matchup,
        "home_team_id": home_team_id if home_team_id is not None else pd.NA,
        "away_team_id": away_team_id if away_team_id is not None else pd.NA,
        "home_team_abbreviation": (
            home_team_abbreviation
            if home_team_abbreviation is not None
            else pd.NA
        ),
        "away_team_abbreviation": (
            away_team_abbreviation
            if away_team_abbreviation is not None
            else pd.NA
        ),
    }


def _eligibility_schedule() -> pd.DataFrame:
    rows = [
        _schedule_row("0022600102", "2026-10-22T23:45:00Z"),
        _schedule_row("0022600101", "2026-10-22T23:30:00Z"),
        _schedule_row("0022600103", "2026-10-23T23:30:00Z"),
        _schedule_row("0022600104", "2026-10-22T23:30:00Z", game_status=2),
        _schedule_row("0022600105", "2026-10-22T23:30:00Z", game_status=3),
        _schedule_row("0022600106", "2026-10-22T23:30:00Z", is_postponed=True),
        _schedule_row("0022600107", "2026-10-22T23:30:00Z", is_conditional=True),
        _schedule_row(
            "0022600108",
            "2026-10-22T23:30:00Z",
            has_confirmed_matchup=False,
            home_team_id=None,
            away_team_id=None,
            home_team_abbreviation=None,
            away_team_abbreviation=None,
        ),
        _schedule_row("0022600109", None),
        _schedule_row("0022600110", "2026-10-22T11:00:00Z"),
    ]
    return pd.DataFrame(rows, columns=SCHEDULED_MATCHUP_COLUMNS)


def _prediction_output(
    matchup: ScheduledMatchup,
    prediction_timestamp: datetime,
    as_of_date: Any,
) -> MatchupPredictionOutput:
    feature_columns = ("elo_diff", "home_rest_days")
    feature_row = pd.DataFrame([{"elo_diff": 3.5, "home_rest_days": 2.0}])
    return MatchupPredictionOutput(
        matchup=matchup,
        prediction_timestamp=prediction_timestamp,
        as_of_date=pd.Timestamp(as_of_date),
        model_version="test-model",
        feature_version="test-feature",
        home_win_probability=0.61,
        away_win_probability=0.39,
        feature_row=feature_row,
        feature_columns=feature_columns,
    )


def test_select_daily_matchups_applies_eligibility_rules() -> None:
    eligible = select_daily_matchups(
        _eligibility_schedule(),
        prediction_date=PREDICTION_DATE,
        prediction_timestamp=PREDICTION_TIMESTAMP,
    )

    assert eligible["game_id"].tolist() == ["0022600101", "0022600102"]


def test_select_daily_matchups_rejects_naive_prediction_timestamp() -> None:
    with pytest.raises(ValueError, match="prediction_timestamp"):
        select_daily_matchups(
            _eligibility_schedule(),
            prediction_date=PREDICTION_DATE,
            prediction_timestamp=datetime(2026, 10, 22, 12),
        )


def test_select_daily_matchups_accepts_empty_schedule() -> None:
    eligible = select_daily_matchups(
        empty_scheduled_matchups(),
        prediction_date=PREDICTION_DATE,
        prediction_timestamp=PREDICTION_TIMESTAMP,
    )

    assert eligible.empty
    assert eligible.columns.tolist() == list(SCHEDULED_MATCHUP_COLUMNS)


def test_run_daily_predictions_registers_one_atomic_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[ScheduledMatchup, pd.Timestamp, datetime]] = []

    def scorer(
        completed_games: pd.DataFrame,
        matchup: ScheduledMatchup,
        *,
        as_of_date: Any,
        bundle: object,
        prediction_timestamp: datetime,
    ) -> MatchupPredictionOutput:
        calls.append((matchup, pd.Timestamp(as_of_date), prediction_timestamp))
        return _prediction_output(matchup, prediction_timestamp, as_of_date)

    monkeypatch.setattr(
        "nba_forecast.application.daily_predictions.predict_scheduled_matchup",
        scorer,
    )

    output = run_daily_predictions(
        _eligibility_schedule(),
        pd.DataFrame(),
        empty_prediction_registry(),
        object(),
        prediction_date=PREDICTION_DATE,
        prediction_timestamp=PREDICTION_TIMESTAMP,
    )

    assert output.prediction_date == PREDICTION_DATE
    assert output.prediction_timestamp == PREDICTION_TIMESTAMP
    assert output.schedule_snapshot_at_utc == SNAPSHOT_AT
    assert output.total_schedule_rows == 10
    assert output.eligible_game_count == 2
    assert output.excluded_game_count == 8
    assert [call[0].game_id for call in calls] == ["0022600101", "0022600102"]
    assert all(call[1].date() == PREDICTION_DATE for call in calls)
    assert all(call[2] == PREDICTION_TIMESTAMP for call in calls)
    assert len(output.predictions) == 2
    assert len(output.registry) == 2

    report = output.to_report()
    assert report["schedule_snapshot_at_utc"] == SNAPSHOT_AT.isoformat()
    assert report["eligible_game_count"] == 2
    assert report["excluded_game_count"] == 8
    assert [
        prediction["prediction_timestamp"]
        for prediction in report["predictions"]
    ] == [PREDICTION_TIMESTAMP.isoformat(), PREDICTION_TIMESTAMP.isoformat()]


def test_run_daily_predictions_is_idempotent_for_fixed_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nba_forecast.application.daily_predictions.predict_scheduled_matchup",
        lambda completed_games, matchup, *, as_of_date, bundle, prediction_timestamp: (
            _prediction_output(matchup, prediction_timestamp, as_of_date)
        ),
    )
    first = run_daily_predictions(
        _eligibility_schedule(),
        pd.DataFrame(),
        empty_prediction_registry(),
        object(),
        prediction_date=PREDICTION_DATE,
        prediction_timestamp=PREDICTION_TIMESTAMP,
    )
    second = run_daily_predictions(
        _eligibility_schedule(),
        pd.DataFrame(),
        first.registry,
        object(),
        prediction_date=PREDICTION_DATE,
        prediction_timestamp=PREDICTION_TIMESTAMP,
    )
    third = run_daily_predictions(
        _eligibility_schedule(),
        pd.DataFrame(),
        second.registry,
        object(),
        prediction_date=PREDICTION_DATE,
        prediction_timestamp=datetime(2026, 10, 22, 13, tzinfo=timezone.utc),
    )

    assert len(first.registry) == 2
    assert len(second.registry) == 2
    assert len(third.registry) == 4


def test_run_daily_predictions_handles_no_game_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nba_forecast.application.daily_predictions.predict_scheduled_matchup",
        lambda *args, **kwargs: pytest.fail("no games should be scored"),
    )
    registry = empty_prediction_registry()

    output = run_daily_predictions(
        _eligibility_schedule(),
        pd.DataFrame(),
        registry,
        object(),
        prediction_date=date(2026, 10, 24),
        prediction_timestamp=PREDICTION_TIMESTAMP,
    )

    assert output.eligible_game_count == 0
    assert output.predictions == ()
    pd.testing.assert_frame_equal(output.registry, registry)


def test_run_daily_predictions_rejects_missing_or_mixed_snapshot_context() -> None:
    with pytest.raises(ValueError, match="non-empty schedule"):
        run_daily_predictions(
            empty_scheduled_matchups(),
            pd.DataFrame(),
            empty_prediction_registry(),
            object(),
            prediction_date=PREDICTION_DATE,
            prediction_timestamp=PREDICTION_TIMESTAMP,
        )

    mixed = _eligibility_schedule()
    mixed.loc[0, "schedule_snapshot_at_utc"] = pd.Timestamp(
        "2026-06-15T13:00:00Z"
    )
    with pytest.raises(ValueError, match="exactly one schedule snapshot"):
        run_daily_predictions(
            mixed,
            pd.DataFrame(),
            empty_prediction_registry(),
            object(),
            prediction_date=PREDICTION_DATE,
            prediction_timestamp=PREDICTION_TIMESTAMP,
        )


def test_run_daily_predictions_leaves_input_registry_unchanged_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def scorer(
        completed_games: pd.DataFrame,
        matchup: ScheduledMatchup,
        *,
        as_of_date: Any,
        bundle: object,
        prediction_timestamp: datetime,
    ) -> MatchupPredictionOutput:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("scoring failed")
        return _prediction_output(matchup, prediction_timestamp, as_of_date)

    monkeypatch.setattr(
        "nba_forecast.application.daily_predictions.predict_scheduled_matchup",
        scorer,
    )
    registry = empty_prediction_registry()
    original = registry.copy(deep=True)

    with pytest.raises(RuntimeError, match="scoring failed"):
        run_daily_predictions(
            _eligibility_schedule(),
            pd.DataFrame(),
            registry,
            object(),
            prediction_date=PREDICTION_DATE,
            prediction_timestamp=PREDICTION_TIMESTAMP,
        )

    pd.testing.assert_frame_equal(registry, original)
