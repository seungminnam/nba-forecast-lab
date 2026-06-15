"""Immutable operating records for forward matchup predictions."""

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from nba_forecast.application.matchup_prediction import MatchupPredictionOutput
from nba_forecast.data.validate import validate_games

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


@dataclass(frozen=True)
class RegistrationResult:
    """Result of attempting to append one immutable prediction event."""

    registry: pd.DataFrame
    status: str
    prediction_id: str


@dataclass(frozen=True)
class SettlementResult:
    """Registry plus counts describing one result-settlement pass."""

    registry: pd.DataFrame
    settled_count: int
    already_settled_count: int
    unmatched_count: int


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


def register_prediction(
    registry: pd.DataFrame,
    prediction: MatchupPredictionOutput,
) -> RegistrationResult:
    """Append one prediction event without overwriting existing evidence."""
    validate_prediction_registry(registry)
    record = prediction_to_record(prediction)
    prediction_id = str(record["prediction_id"])
    existing = registry.loc[registry["prediction_id"] == prediction_id]
    if not existing.empty:
        if existing.iloc[0]["payload_fingerprint"] != record["payload_fingerprint"]:
            raise ValueError(
                "Prediction identity already exists with a conflicting payload"
            )
        return RegistrationResult(
            registry=registry,
            status="already_registered",
            prediction_id=prediction_id,
        )

    record_frame = pd.DataFrame([record], columns=REGISTRY_COLUMNS)
    appended = (
        record_frame
        if registry.empty
        else pd.concat([registry, record_frame], ignore_index=True)
    ).sort_values(
        ["prediction_timestamp", "game_id", "prediction_id"],
        ignore_index=True,
    )
    validate_prediction_registry(appended)
    return RegistrationResult(
        registry=appended,
        status="registered",
        prediction_id=prediction_id,
    )


def settle_predictions(
    registry: pd.DataFrame,
    completed_games: pd.DataFrame,
    *,
    settled_at: Any = None,
) -> SettlementResult:
    """Attach canonical completed-game outcomes without changing predictions."""
    validate_prediction_registry(registry)
    validate_games(completed_games)
    settlement_timestamp = _utc_timestamp(
        settled_at or datetime.now(timezone.utc)
    )
    games_by_id = completed_games.set_index("game_id", drop=False)
    settled_registry = registry.copy(deep=True)
    settled_registry["settled_at"] = pd.to_datetime(
        settled_registry["settled_at"],
        utc=True,
    )
    settled_count = 0
    already_settled_count = 0
    unmatched_count = 0

    for index, prediction in settled_registry.iterrows():
        game_id = prediction["game_id"]
        if game_id not in games_by_id.index:
            unmatched_count += 1
            continue
        game = games_by_id.loc[game_id]
        _validate_matching_game_identity(prediction, game)
        outcome = int(game["home_win"])
        if not pd.isna(prediction["final_outcome"]):
            if int(prediction["final_outcome"]) != outcome:
                raise ValueError(
                    f"Prediction {prediction['prediction_id']} "
                    "has a conflicting outcome"
                )
            already_settled_count += 1
            continue

        probability = float(prediction["home_win_probability"])
        settled_registry.at[index, "final_outcome"] = outcome
        settled_registry.at[index, "settled_at"] = settlement_timestamp
        settled_registry.at[index, "brier_contribution"] = (
            probability - outcome
        ) ** 2
        settled_registry.at[index, "is_correct"] = int(
            (probability >= 0.5) == bool(outcome)
        )
        settled_count += 1

    validate_prediction_registry(settled_registry)
    return SettlementResult(
        registry=settled_registry,
        settled_count=settled_count,
        already_settled_count=already_settled_count,
        unmatched_count=unmatched_count,
    )


def _validate_matching_game_identity(
    prediction: pd.Series,
    game: pd.Series,
) -> None:
    fields = (
        "home_team_id",
        "away_team_id",
        "home_team_abbreviation",
        "away_team_abbreviation",
    )
    if any(prediction[field] != game[field] for field in fields):
        raise ValueError(
            f"Prediction {prediction['prediction_id']} has a team identity mismatch"
        )


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
