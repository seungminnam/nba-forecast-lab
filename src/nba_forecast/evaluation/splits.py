"""Explicit season-based temporal splits."""

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd


class TemporalSplitError(ValueError):
    """Raised when requested temporal splits are invalid."""


@dataclass(frozen=True)
class TemporalSplit:
    """Train, validation, and test frames in chronological order."""

    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def make_temporal_split(
    features: pd.DataFrame,
    *,
    train_seasons: Sequence[str],
    validation_seasons: Sequence[str],
    test_seasons: Sequence[str],
) -> TemporalSplit:
    """Select disjoint season groups and reject chronological reversals."""
    groups = [
        ("train", tuple(train_seasons)),
        ("validation", tuple(validation_seasons)),
        ("test", tuple(test_seasons)),
    ]
    selected_seasons = [season for _, seasons in groups for season in seasons]
    if len(selected_seasons) != len(set(selected_seasons)):
        raise TemporalSplitError("Season groups overlap")

    available_seasons = set(features["season_id"].astype(str))
    missing = sorted(set(selected_seasons) - available_seasons)
    if missing:
        raise TemporalSplitError(f"Requested seasons are missing: {', '.join(missing)}")

    frames = {
        name: features.loc[features["season_id"].astype(str).isin(seasons)]
        .sort_values(["game_date", "game_id"])
        .reset_index(drop=True)
        for name, seasons in groups
    }
    non_empty_frames = [frames[name] for name, _ in groups if not frames[name].empty]
    for earlier, later in zip(non_empty_frames, non_empty_frames[1:]):
        if pd.to_datetime(earlier["game_date"]).max() >= pd.to_datetime(
            later["game_date"]
        ).min():
            raise TemporalSplitError("Season groups must be chronological")

    return TemporalSplit(
        train=frames["train"],
        validation=frames["validation"],
        test=frames["test"],
    )

