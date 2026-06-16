"""Transform NBA schedule snapshots into canonical scheduled matchups."""

from __future__ import annotations

from datetime import timezone
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from nba_forecast.data.contracts import expected_season_id

SCHEDULE_SOURCE_COLUMNS = (
    "gameId",
    "gameStatus",
    "gameStatusText",
    "gameDateTimeUTC",
    "gameDateEst",
    "ifNecessary",
    "postponedStatus",
    "homeTeam_teamId",
    "homeTeam_teamTricode",
    "awayTeam_teamId",
    "awayTeam_teamTricode",
)

SCHEDULED_MATCHUP_COLUMNS = (
    "game_id",
    "season_id",
    "season_type",
    "season_key",
    "schedule_snapshot_at_utc",
    "nba_game_date",
    "tipoff_at_utc",
    "game_status",
    "game_status_text",
    "is_postponed",
    "is_conditional",
    "has_confirmed_matchup",
    "home_team_id",
    "away_team_id",
    "home_team_abbreviation",
    "away_team_abbreviation",
)

_GAME_ID_PREFIX_TO_SEASON_TYPE = {
    "002": "Regular Season",
    "004": "Playoffs",
}
_NBA_TIMEZONE = ZoneInfo("America/New_York")


def empty_scheduled_matchups() -> pd.DataFrame:
    """Return an empty table with the canonical scheduled-matchup columns."""
    return pd.DataFrame(columns=SCHEDULED_MATCHUP_COLUMNS)


def schedule_rows_to_matchups(
    rows: pd.DataFrame,
    *,
    season_key: str,
    schedule_snapshot_at_utc: Any,
) -> pd.DataFrame:
    """Normalize source-shaped schedule rows into scheduled matchup rows."""
    _require_source_columns(rows)
    snapshot_at = _require_utc_timestamp(
        schedule_snapshot_at_utc,
        field_name="schedule_snapshot_at_utc",
    )
    canonical_rows: list[dict[str, Any]] = []

    for _, row in rows.iterrows():
        game_id = _clean_text(row["gameId"])
        prefix = game_id[:3]
        season_type = _GAME_ID_PREFIX_TO_SEASON_TYPE.get(prefix)
        if season_type is None:
            continue

        tipoff_at = _optional_utc_timestamp(row["gameDateTimeUTC"])
        home_team_id = _optional_positive_integer(row["homeTeam_teamId"])
        away_team_id = _optional_positive_integer(row["awayTeam_teamId"])
        home_abbreviation = _optional_text(row["homeTeam_teamTricode"])
        away_abbreviation = _optional_text(row["awayTeam_teamTricode"])
        has_confirmed_matchup = all(
            not _is_missing(value)
            for value in (
                home_team_id,
                away_team_id,
                home_abbreviation,
                away_abbreviation,
            )
        )

        canonical_rows.append(
            {
                "game_id": game_id,
                "season_id": expected_season_id(season_type, season_key),
                "season_type": season_type,
                "season_key": season_key,
                "schedule_snapshot_at_utc": snapshot_at,
                "nba_game_date": _nba_game_date(tipoff_at, row["gameDateEst"]),
                "tipoff_at_utc": tipoff_at,
                "game_status": _integer_status(row["gameStatus"]),
                "game_status_text": _clean_text(row["gameStatusText"]),
                "is_postponed": _truthy_nonzero(row["postponedStatus"]),
                "is_conditional": _truthy_nonzero(row["ifNecessary"]),
                "has_confirmed_matchup": has_confirmed_matchup,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_team_abbreviation": home_abbreviation,
                "away_team_abbreviation": away_abbreviation,
            }
        )

    schedule = _coerce_schedule_dtypes(
        pd.DataFrame(canonical_rows, columns=SCHEDULED_MATCHUP_COLUMNS)
    )
    validate_scheduled_matchups(schedule)
    return schedule


def validate_scheduled_matchups(schedule: pd.DataFrame) -> None:
    """Validate the canonical scheduled-matchup contract."""
    if tuple(schedule.columns) != SCHEDULED_MATCHUP_COLUMNS:
        raise ValueError("Schedule must contain exactly the scheduled matchup columns")
    if schedule.empty:
        return

    _validate_game_ids(schedule)
    _validate_season_context(schedule)
    _validate_snapshot_timestamps(schedule)
    _validate_game_statuses(schedule)
    _validate_dates(schedule)
    _validate_boolean_columns(schedule)
    _validate_team_identities(schedule)


def _require_source_columns(rows: pd.DataFrame) -> None:
    missing = sorted(set(SCHEDULE_SOURCE_COLUMNS) - set(rows.columns))
    if missing:
        missing_columns = ", ".join(missing)
        raise ValueError(f"Missing required schedule source columns: {missing_columns}")


def _validate_game_ids(schedule: pd.DataFrame) -> None:
    game_ids = schedule["game_id"].astype("string")
    if game_ids.isna().any() or game_ids.str.strip().eq("").any():
        raise ValueError("Schedule game_id values cannot be blank")
    if game_ids.duplicated().any():
        raise ValueError("Schedule game_id values must be unique")


def _validate_season_context(schedule: pd.DataFrame) -> None:
    for index, row in schedule.iterrows():
        season_type = str(row["season_type"])
        season_key = str(row["season_key"])
        try:
            expected_id = expected_season_id(season_type, season_key)
        except ValueError as error:
            raise ValueError(
                f"Invalid season_type or season_key at row {index}"
            ) from error
        if str(row["season_id"]) != expected_id:
            raise ValueError(
                f"Invalid season_id at row {index}: expected {expected_id}"
            )


def _validate_snapshot_timestamps(schedule: pd.DataFrame) -> None:
    for index, value in schedule["schedule_snapshot_at_utc"].items():
        try:
            _require_utc_timestamp(value, field_name="schedule_snapshot_at_utc")
        except ValueError as error:
            raise ValueError(
                f"Invalid schedule_snapshot_at_utc at row {index}"
            ) from error


def _validate_game_statuses(schedule: pd.DataFrame) -> None:
    for index, value in schedule["game_status"].items():
        try:
            status = _integer_status(value)
        except ValueError as error:
            raise ValueError(f"Invalid game_status at row {index}") from error
        if status < 0:
            raise ValueError(f"Invalid game_status at row {index}: negative")


def _validate_dates(schedule: pd.DataFrame) -> None:
    for index, row in schedule.iterrows():
        try:
            nba_game_date = pd.Timestamp(row["nba_game_date"]).normalize()
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid nba_game_date at row {index}") from error
        if pd.isna(nba_game_date):
            raise ValueError(f"Invalid nba_game_date at row {index}")

        if pd.isna(row["tipoff_at_utc"]):
            continue
        try:
            tipoff_at = _require_utc_timestamp(
                row["tipoff_at_utc"],
                field_name="tipoff_at_utc",
            )
        except ValueError as error:
            raise ValueError(f"Invalid tipoff_at_utc at row {index}") from error
        local_date = tipoff_at.tz_convert(_NBA_TIMEZONE).date()
        if nba_game_date.date() != local_date:
            raise ValueError(
                f"tipoff_at_utc and nba_game_date disagree in New York at row {index}"
            )


def _validate_boolean_columns(schedule: pd.DataFrame) -> None:
    for column in ("is_postponed", "is_conditional", "has_confirmed_matchup"):
        for index, value in schedule[column].items():
            if not isinstance(value, (bool, np.bool_)):
                raise ValueError(f"{column} must contain bool values at row {index}")


def _validate_team_identities(schedule: pd.DataFrame) -> None:
    for index, row in schedule.iterrows():
        values = (
            row["home_team_id"],
            row["away_team_id"],
            row["home_team_abbreviation"],
            row["away_team_abbreviation"],
        )
        present = [not _is_missing(value) for value in values]
        confirmed = bool(row["has_confirmed_matchup"])
        if not any(present):
            if confirmed:
                raise ValueError(
                    f"Unknown matchup cannot be confirmed at row {index}"
                )
            continue
        if not all(present):
            raise ValueError(
                f"Team identities are partially populated at row {index}"
            )
        if not confirmed:
            raise ValueError(
                "Confirmed team identities require has_confirmed_matchup "
                f"at row {index}"
            )
        home_team_id = _positive_integer(row["home_team_id"], "home_team_id")
        away_team_id = _positive_integer(row["away_team_id"], "away_team_id")
        if home_team_id == away_team_id:
            raise ValueError(f"Confirmed teams cannot be identical at row {index}")
        if _clean_text(row["home_team_abbreviation"]) == _clean_text(
            row["away_team_abbreviation"]
        ):
            raise ValueError(f"Confirmed teams cannot be identical at row {index}")


def _nba_game_date(tipoff_at: pd.Timestamp | None, source_date: Any) -> pd.Timestamp:
    if tipoff_at is not None and not pd.isna(tipoff_at):
        return tipoff_at.tz_convert(_NBA_TIMEZONE).normalize().tz_localize(None)
    parsed = pd.to_datetime(source_date, errors="raise")
    return pd.Timestamp(parsed).normalize()


def _coerce_schedule_dtypes(schedule: pd.DataFrame) -> pd.DataFrame:
    coerced = schedule.copy()
    string_columns = (
        "game_id",
        "season_id",
        "season_type",
        "season_key",
        "game_status_text",
        "home_team_abbreviation",
        "away_team_abbreviation",
    )
    for column in string_columns:
        coerced[column] = coerced[column].astype("string")
    coerced["schedule_snapshot_at_utc"] = pd.to_datetime(
        coerced["schedule_snapshot_at_utc"],
        utc=True,
    )
    coerced["nba_game_date"] = pd.to_datetime(
        coerced["nba_game_date"],
        errors="raise",
    ).dt.normalize()
    coerced["tipoff_at_utc"] = pd.to_datetime(
        coerced["tipoff_at_utc"],
        utc=True,
        errors="coerce",
    )
    coerced["game_status"] = coerced["game_status"].astype("Int64")
    for column in ("is_postponed", "is_conditional", "has_confirmed_matchup"):
        coerced[column] = coerced[column].astype(bool)
    for column in ("home_team_id", "away_team_id"):
        coerced[column] = coerced[column].astype("Int64")
    return coerced


def _require_utc_timestamp(value: Any, *, field_name: str) -> pd.Timestamp:
    if pd.isna(value):
        raise ValueError(f"{field_name} cannot be null")
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    utc_timestamp = timestamp.tz_convert(timezone.utc)
    if utc_timestamp.tzinfo != timezone.utc:
        raise ValueError(f"{field_name} must be UTC")
    return utc_timestamp


def _optional_utc_timestamp(value: Any) -> pd.Timestamp | None:
    if _is_missing(value):
        return None
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).tz_convert(timezone.utc)


def _integer_status(value: Any) -> int:
    if _is_missing(value):
        raise ValueError("game_status cannot be null")
    number = pd.to_numeric(value, errors="raise")
    if float(number) % 1 != 0:
        raise ValueError("game_status must be an integer")
    status = int(number)
    if status < 0:
        raise ValueError("game_status cannot be negative")
    return status


def _positive_integer(value: Any, field_name: str) -> int:
    if _is_missing(value):
        raise ValueError(f"{field_name} cannot be null")
    number = pd.to_numeric(value, errors="raise")
    if float(number) % 1 != 0:
        raise ValueError(f"{field_name} must be an integer")
    integer = int(number)
    if integer <= 0:
        raise ValueError(f"{field_name} must be positive")
    return integer


def _optional_positive_integer(value: Any) -> Any:
    if _is_missing(value):
        return pd.NA
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return value
    if float(number) % 1 != 0:
        return value
    if int(number) <= 0:
        return pd.NA
    try:
        integer = _positive_integer(value, "team_id")
    except (TypeError, ValueError):
        return value
    return integer


def _optional_text(value: Any) -> Any:
    if _is_missing(value):
        return pd.NA
    text = str(value).strip()
    if not text:
        return pd.NA
    return text


def _clean_text(value: Any) -> str:
    if _is_missing(value):
        return ""
    return str(value).strip()


def _truthy_nonzero(value: Any) -> bool:
    if _is_missing(value):
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"", "0", "false", "f", "no", "n", "none", "nan"}:
        return False
    try:
        return float(text) != 0
    except ValueError:
        return True


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
