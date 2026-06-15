"""Immutable operating records for forward matchup predictions."""

import hashlib
import json
import math
from typing import Any

import pandas as pd

from nba_forecast.application.matchup_prediction import MatchupPredictionOutput

REGISTRY_COLUMNS = (
    "prediction_id",
    "payload_fingerprint",
    "prediction_timestamp",
    "as_of_date",
    "game_id",
    "game_date",
    "season_id",
    "season_type",
    "season_key",
    "home_team_id",
    "away_team_id",
    "home_team_abbreviation",
    "away_team_abbreviation",
    "model_version",
    "feature_version",
    "home_win_probability",
    "away_win_probability",
    "features_json",
    "final_outcome",
    "settled_at",
    "brier_contribution",
    "is_correct",
)

IMMUTABLE_REGISTRY_COLUMNS = REGISTRY_COLUMNS[:18]
SETTLEMENT_COLUMNS = REGISTRY_COLUMNS[18:]


def empty_prediction_registry() -> pd.DataFrame:
    """Return an empty table with the authoritative registry columns."""
    return pd.DataFrame(columns=REGISTRY_COLUMNS)


def prediction_to_record(output: MatchupPredictionOutput) -> dict[str, object]:
    """Convert one matchup prediction to a deterministic unsettled record."""
    prediction_timestamp = _utc_timestamp(output.prediction_timestamp)
    features = output.feature_row.iloc[0][list(output.feature_columns)]
    features_json = _canonical_json(
        {feature: _json_value(features[feature]) for feature in output.feature_columns}
    )
    immutable_payload: dict[str, object] = {
        "prediction_timestamp": prediction_timestamp.isoformat(),
        "as_of_date": pd.Timestamp(output.as_of_date).date().isoformat(),
        "game_id": output.matchup.game_id,
        "game_date": pd.Timestamp(output.matchup.game_date).date().isoformat(),
        "season_id": output.matchup.season_id,
        "season_type": output.matchup.season_type,
        "season_key": output.matchup.season_key,
        "home_team_id": output.matchup.home_team_id,
        "away_team_id": output.matchup.away_team_id,
        "home_team_abbreviation": output.matchup.home_team_abbreviation,
        "away_team_abbreviation": output.matchup.away_team_abbreviation,
        "model_version": output.model_version,
        "feature_version": output.feature_version,
        "home_win_probability": output.home_win_probability,
        "away_win_probability": output.away_win_probability,
        "features_json": features_json,
    }
    identity = {
        key: immutable_payload[key]
        for key in ("game_id", "model_version", "prediction_timestamp")
    }
    return {
        "prediction_id": _sha256(identity),
        "payload_fingerprint": _sha256(immutable_payload),
        "prediction_timestamp": prediction_timestamp,
        "as_of_date": pd.Timestamp(output.as_of_date).normalize(),
        "game_id": output.matchup.game_id,
        "game_date": pd.Timestamp(output.matchup.game_date).normalize(),
        "season_id": output.matchup.season_id,
        "season_type": output.matchup.season_type,
        "season_key": output.matchup.season_key,
        "home_team_id": output.matchup.home_team_id,
        "away_team_id": output.matchup.away_team_id,
        "home_team_abbreviation": output.matchup.home_team_abbreviation,
        "away_team_abbreviation": output.matchup.away_team_abbreviation,
        "model_version": output.model_version,
        "feature_version": output.feature_version,
        "home_win_probability": output.home_win_probability,
        "away_win_probability": output.away_win_probability,
        "features_json": features_json,
        "final_outcome": pd.NA,
        "settled_at": pd.NaT,
        "brier_contribution": pd.NA,
        "is_correct": pd.NA,
    }


def validate_prediction_registry(registry: pd.DataFrame) -> None:
    """Reject registry tables that violate identity or settlement invariants."""
    if registry.columns.tolist() != list(REGISTRY_COLUMNS):
        raise ValueError("Prediction registry columns do not match the contract")
    if registry.empty:
        return
    if registry["prediction_id"].duplicated().any():
        raise ValueError("Prediction registry contains duplicate prediction_id values")
    if registry.loc[:, list(IMMUTABLE_REGISTRY_COLUMNS)].isna().any().any():
        raise ValueError("Immutable prediction registry fields cannot be null")

    for value in registry["prediction_timestamp"]:
        _utc_timestamp(value)

    home = pd.to_numeric(registry["home_win_probability"], errors="coerce")
    away = pd.to_numeric(registry["away_win_probability"], errors="coerce")
    if home.isna().any() or away.isna().any():
        raise ValueError("Prediction probabilities must be numeric")
    if not home.between(0.0, 1.0).all() or not away.between(0.0, 1.0).all():
        raise ValueError("Prediction probabilities must be between zero and one")
    if not (home + away).map(lambda value: math.isclose(value, 1.0)).all():
        raise ValueError("Home and away probabilities must sum to one")

    for features_json in registry["features_json"]:
        try:
            features = json.loads(features_json)
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("features_json must contain canonical JSON") from error
        if not isinstance(features, dict) or _canonical_json(features) != features_json:
            raise ValueError("features_json must contain canonical JSON")

    settlement_nulls = registry.loc[:, list(SETTLEMENT_COLUMNS)].isna()
    partially_settled = settlement_nulls.any(axis=1) & ~settlement_nulls.all(axis=1)
    if partially_settled.any():
        raise ValueError("settlement fields must be populated together")
    settled = registry.loc[~settlement_nulls.all(axis=1)]
    if settled.empty:
        return
    if not settled["final_outcome"].isin([0, 1]).all():
        raise ValueError("final_outcome must be zero or one")
    if not settled["is_correct"].isin([0, 1]).all():
        raise ValueError("is_correct must be zero or one")
    if not pd.to_numeric(
        settled["brier_contribution"],
        errors="coerce",
    ).between(0.0, 1.0).all():
        raise ValueError("brier_contribution must be between zero and one")
    for value in settled["settled_at"]:
        _utc_timestamp(value)


def _utc_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("Prediction registry timestamps must be timezone-aware")
    return timestamp.tz_convert("UTC")


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value
