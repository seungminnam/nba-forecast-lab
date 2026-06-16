from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from nba_forecast.data.schedule_transform import (
    SCHEDULED_MATCHUP_COLUMNS,
    empty_scheduled_matchups,
    schedule_rows_to_matchups,
    validate_scheduled_matchups,
)

FIXTURE_PATH = Path("tests/fixtures/schedule_league_v2_rows.csv")
SNAPSHOT_AT = datetime(2026, 6, 15, 12, tzinfo=timezone.utc)


def _source_rows() -> pd.DataFrame:
    return pd.read_csv(FIXTURE_PATH, dtype={"gameId": "string"})


def _schedule() -> pd.DataFrame:
    return schedule_rows_to_matchups(
        _source_rows(),
        season_key="2026-27",
        schedule_snapshot_at_utc=SNAPSHOT_AT,
    )


def _bool_value(value: object) -> bool:
    return bool(value)


def test_schedule_rows_to_matchups_normalizes_supported_games() -> None:
    schedule = _schedule()

    assert schedule.columns.tolist() == list(SCHEDULED_MATCHUP_COLUMNS)
    assert schedule["game_id"].tolist() == [
        "0022600001",
        "0042600001",
        "0042600002",
        "0022600002",
    ]
    assert schedule["season_type"].tolist() == [
        "Regular Season",
        "Playoffs",
        "Playoffs",
        "Regular Season",
    ]
    assert schedule["season_id"].tolist() == [
        "22026",
        "42026",
        "42026",
        "22026",
    ]
    assert schedule["season_key"].eq("2026-27").all()
    assert schedule["schedule_snapshot_at_utc"].eq(pd.Timestamp(SNAPSHOT_AT)).all()

    playoff = schedule.loc[schedule["game_id"] == "0042600001"].iloc[0]
    assert playoff["tipoff_at_utc"] == pd.Timestamp("2027-04-18T00:30:00Z")
    assert playoff["nba_game_date"] == pd.Timestamp("2027-04-17")

    conditional = schedule.loc[schedule["game_id"] == "0042600002"].iloc[0]
    assert pd.isna(conditional["tipoff_at_utc"])
    assert _bool_value(conditional["is_conditional"]) is True
    assert _bool_value(conditional["has_confirmed_matchup"]) is False
    assert pd.isna(conditional["home_team_id"])
    assert pd.isna(conditional["away_team_id"])

    postponed = schedule.loc[schedule["game_id"] == "0022600002"].iloc[0]
    assert _bool_value(postponed["is_postponed"]) is True
    assert postponed["game_status"] == 3


def test_empty_and_valid_schedules_pass_validation() -> None:
    validate_scheduled_matchups(empty_scheduled_matchups())
    validate_scheduled_matchups(_schedule())


def test_transform_rejects_naive_snapshot_timestamp() -> None:
    with pytest.raises(ValueError, match="schedule_snapshot_at_utc"):
        schedule_rows_to_matchups(
            _source_rows(),
            season_key="2026-27",
            schedule_snapshot_at_utc=datetime(2026, 6, 15, 12),
        )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda schedule: schedule.drop(columns=["game_id"]),
            "exactly the scheduled matchup columns",
        ),
        (
            lambda schedule: schedule.assign(extra_column=1),
            "exactly the scheduled matchup columns",
        ),
        (
            lambda schedule: schedule.assign(game_id=["0022600001"] * len(schedule)),
            "unique",
        ),
        (
            lambda schedule: schedule.assign(
                game_id=[""] + schedule["game_id"].iloc[1:].tolist()
            ),
            "blank",
        ),
        (
            lambda schedule: schedule.assign(season_id="99999"),
            "season_id",
        ),
        (
            lambda schedule: schedule.assign(season_type="Preseason"),
            "season_type",
        ),
        (
            lambda schedule: schedule.assign(game_status=pd.NA),
            "game_status",
        ),
        (
            lambda schedule: schedule.assign(game_status=1.5),
            "game_status",
        ),
        (
            lambda schedule: schedule.assign(game_status=-1),
            "game_status",
        ),
        (
            lambda schedule: schedule.assign(tipoff_at_utc="2027-04-18 00:30:00"),
            "tipoff_at_utc",
        ),
        (
            lambda schedule: schedule.assign(nba_game_date="not-a-date"),
            "nba_game_date",
        ),
        (
            lambda schedule: schedule.assign(nba_game_date=pd.Timestamp("2027-04-18")),
            "New York",
        ),
        (
            lambda schedule: schedule.assign(home_team_id=pd.NA),
            "partially populated",
        ),
        (
            lambda schedule: schedule.assign(away_team_id=schedule["home_team_id"]),
            "identical",
        ),
        (
            lambda schedule: schedule.assign(
                schedule_snapshot_at_utc="2026-06-15 12:00:00"
            ),
            "schedule_snapshot_at_utc",
        ),
    ],
)
def test_validate_scheduled_matchups_rejects_invalid_contract(
    mutate: object,
    match: str,
) -> None:
    schedule = _schedule()

    with pytest.raises(ValueError, match=match):
        validate_scheduled_matchups(mutate(schedule))


def test_validate_scheduled_matchups_allows_unknown_nonnegative_status() -> None:
    schedule = _schedule().assign(game_status=7)

    validate_scheduled_matchups(schedule)
