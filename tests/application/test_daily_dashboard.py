from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from nba_forecast.application.daily_dashboard import (
    DailyForecastReportError,
    daily_report_path,
    find_latest_daily_report,
    load_daily_report,
)


def _write_report(path: Path, *, prediction_date: str, predictions: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "prediction_date": prediction_date,
                "prediction_timestamp": f"{prediction_date}T12:00:00+00:00",
                "schedule_snapshot_at_utc": "2026-06-15T12:00:00+00:00",
                "total_schedule_rows": 3,
                "eligible_game_count": len(predictions),
                "excluded_game_count": 3 - len(predictions),
                "predictions": predictions,
            }
        )
    )


def _prediction(game_id: str = "0022600001") -> dict:
    return {
        "prediction_timestamp": "2026-10-22T12:00:00+00:00",
        "as_of_date": "2026-10-22",
        "matchup": {
            "game_id": game_id,
            "game_date": "2026-10-22",
            "season_id": "22026",
            "season_type": "Regular Season",
            "season_key": "2026-27",
            "home_team_id": 1610612752,
            "away_team_id": 1610612759,
            "home_team_abbreviation": "NYK",
            "away_team_abbreviation": "SAS",
        },
        "model_version": "2026-06-11-recent5-raw",
        "feature_version": "model-features-v1",
        "home_win_probability": 0.584,
        "away_win_probability": 0.416,
        "final_outcome": None,
        "features": {"elo_diff": 3.2},
    }


def test_find_latest_daily_report_chooses_newest_date(tmp_path: Path) -> None:
    _write_report(
        tmp_path / "daily_predictions_2026-10-22.json",
        prediction_date="2026-10-22",
        predictions=[],
    )
    _write_report(
        tmp_path / "daily_predictions_2026-10-24.json",
        prediction_date="2026-10-24",
        predictions=[],
    )
    (tmp_path / "other.json").write_text("{}")

    assert (
        find_latest_daily_report(tmp_path)
        == tmp_path / "daily_predictions_2026-10-24.json"
    )


def test_find_latest_daily_report_returns_none_when_absent(tmp_path: Path) -> None:
    assert find_latest_daily_report(tmp_path) is None


def test_daily_report_path_uses_expected_filename(tmp_path: Path) -> None:
    assert (
        daily_report_path(tmp_path, date(2026, 10, 22))
        == tmp_path / "daily_predictions_2026-10-22.json"
    )


def test_load_daily_report_parses_valid_prediction_report(tmp_path: Path) -> None:
    path = tmp_path / "daily_predictions_2026-10-22.json"
    _write_report(path, prediction_date="2026-10-22", predictions=[_prediction()])

    report = load_daily_report(path)

    assert report.prediction_date == date(2026, 10, 22)
    assert report.eligible_game_count == 1
    assert report.prediction_count == 1
    assert report.games[0].matchup_label == "SAS at NYK"
    assert report.games[0].home_win_probability == 0.584
    assert report.games[0].away_win_probability == 0.416
    assert report.model_versions == ("2026-06-11-recent5-raw",)


def test_load_daily_report_accepts_no_game_report(tmp_path: Path) -> None:
    path = tmp_path / "daily_predictions_2026-10-26.json"
    _write_report(path, prediction_date="2026-10-26", predictions=[])

    report = load_daily_report(path)

    assert report.prediction_date == date(2026, 10, 26)
    assert report.games == ()
    assert report.prediction_count == 0


def test_load_daily_report_rejects_malformed_report(tmp_path: Path) -> None:
    path = tmp_path / "daily_predictions_2026-10-22.json"
    path.write_text(json.dumps({"prediction_date": "2026-10-22"}))

    with pytest.raises(DailyForecastReportError, match="missing"):
        load_daily_report(path)


def test_load_daily_report_rejects_non_complementary_probabilities(
    tmp_path: Path,
) -> None:
    path = tmp_path / "daily_predictions_2026-10-22.json"
    bad = _prediction()
    bad["away_win_probability"] = 0.50
    _write_report(path, prediction_date="2026-10-22", predictions=[bad])

    with pytest.raises(DailyForecastReportError, match="sum to one"):
        load_daily_report(path)
