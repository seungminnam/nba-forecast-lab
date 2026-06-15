"""Chronological game-probability backtest for one playoff season."""

from dataclasses import dataclass

import pandas as pd

from nba_forecast.application.matchup_prediction import predict_scheduled_matchup
from nba_forecast.data.contracts import expected_season_id
from nba_forecast.evaluation.metrics import probability_metrics
from nba_forecast.features.matchup_features import ScheduledMatchup
from nba_forecast.models.artifacts import ModelBundle

BACKTEST_REQUIRED_COLUMNS = (
    "game_id",
    "game_date",
    "season_id",
    "season_type",
    "season_key",
    "home_team_id",
    "away_team_id",
    "home_team_abbreviation",
    "away_team_abbreviation",
    "home_win",
)


@dataclass(frozen=True)
class PlayoffBacktestInput:
    """Season identity for one chronological playoff evaluation."""

    season_key: str
    season_id: str


@dataclass(frozen=True)
class PlayoffBacktestOutput:
    """Prediction-level evidence and aggregate metrics for one playoff season."""

    inputs: PlayoffBacktestInput
    model_version: str
    feature_version: str
    predictions: pd.DataFrame
    metrics: dict[str, float]

    def metrics_report(self) -> dict[str, object]:
        """Return a JSON-serializable aggregate report."""
        return {
            "season_key": self.inputs.season_key,
            "season_id": self.inputs.season_id,
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "games": len(self.predictions),
            "metrics": self.metrics,
        }


def run_playoff_backtest(
    games: pd.DataFrame,
    inputs: PlayoffBacktestInput,
    bundle: ModelBundle,
) -> PlayoffBacktestOutput:
    """Score every completed playoff game at its date-level pre-game cutoff."""
    playoff_games = _validated_playoff_games(games, inputs)
    predictions = []
    for game in playoff_games.itertuples(index=False):
        matchup = ScheduledMatchup(
            game_id=str(game.game_id),
            game_date=pd.Timestamp(game.game_date),
            season_id=str(game.season_id),
            season_type=str(game.season_type),
            season_key=str(game.season_key),
            home_team_id=int(game.home_team_id),
            away_team_id=int(game.away_team_id),
            home_team_abbreviation=str(game.home_team_abbreviation),
            away_team_abbreviation=str(game.away_team_abbreviation),
        )
        prediction = predict_scheduled_matchup(
            games,
            matchup,
            as_of_date=pd.Timestamp(game.game_date),
            bundle=bundle,
        )
        probability = float(prediction.home_win_probability)
        if not 0.0 <= probability <= 1.0:
            raise ValueError("predicted probability must be between zero and one")
        home_win = int(game.home_win)
        predictions.append(
            {
                "game_id": matchup.game_id,
                "game_date": pd.Timestamp(matchup.game_date),
                "season_id": matchup.season_id,
                "season_key": matchup.season_key,
                "home_team_id": matchup.home_team_id,
                "away_team_id": matchup.away_team_id,
                "home_team_abbreviation": matchup.home_team_abbreviation,
                "away_team_abbreviation": matchup.away_team_abbreviation,
                "model_version": prediction.model_version,
                "feature_version": prediction.feature_version,
                "home_win_probability": probability,
                "away_win_probability": float(prediction.away_win_probability),
                "home_win": home_win,
                "brier_contribution": (probability - home_win) ** 2,
                "predicted_correct": (probability >= 0.5) == bool(home_win),
            }
        )

    prediction_table = pd.DataFrame(predictions)
    metrics = probability_metrics(
        prediction_table["home_win"].tolist(),
        prediction_table["home_win_probability"].tolist(),
    )
    return PlayoffBacktestOutput(
        inputs=inputs,
        model_version=str(prediction_table.iloc[0]["model_version"]),
        feature_version=str(prediction_table.iloc[0]["feature_version"]),
        predictions=prediction_table,
        metrics=metrics,
    )


def _validated_playoff_games(
    games: pd.DataFrame,
    inputs: PlayoffBacktestInput,
) -> pd.DataFrame:
    if games.empty:
        raise ValueError("canonical games must be non-empty")
    missing = sorted(set(BACKTEST_REQUIRED_COLUMNS) - set(games.columns))
    if missing:
        raise ValueError(f"canonical games are missing required columns: {missing}")
    if inputs.season_id != expected_season_id("Playoffs", inputs.season_key):
        raise ValueError("playoff backtest has inconsistent season context")

    frame = games.copy()
    frame["game_date"] = pd.to_datetime(frame["game_date"], errors="raise")
    selected = frame.loc[
        (frame["season_key"].astype(str) == inputs.season_key)
        & (frame["season_id"].astype(str) == inputs.season_id)
        & (frame["season_type"].astype(str) == "Playoffs")
    ].copy()
    if selected.empty:
        raise ValueError("no playoff games found for requested season")
    if selected["game_id"].astype(str).duplicated().any():
        raise ValueError("playoff games contain duplicate game IDs")
    if selected["home_win"].isna().any() or not selected["home_win"].isin([0, 1]).all():
        raise ValueError("playoff games must contain complete outcomes")
    return selected.sort_values(["game_date", "game_id"], ignore_index=True)
