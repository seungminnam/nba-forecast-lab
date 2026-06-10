import pandas as pd
import pytest

from nba_forecast.evaluation.splits import TemporalSplitError, make_temporal_split


def _features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "game_id": ["a", "b", "c"],
            "game_date": pd.to_datetime(["2023-01-01", "2024-01-01", "2025-01-01"]),
            "season_id": ["22022", "22023", "22024"],
            "home_win": [1, 0, 1],
        }
    )


def test_make_temporal_split_returns_disjoint_ordered_frames() -> None:
    split = make_temporal_split(
        _features(),
        train_seasons=["22022"],
        validation_seasons=["22023"],
        test_seasons=["22024"],
    )

    assert split.train["game_id"].tolist() == ["a"]
    assert split.validation["game_id"].tolist() == ["b"]
    assert split.test["game_id"].tolist() == ["c"]


def test_make_temporal_split_rejects_overlapping_seasons() -> None:
    with pytest.raises(TemporalSplitError, match="overlap"):
        make_temporal_split(
            _features(),
            train_seasons=["22022", "22023"],
            validation_seasons=["22023"],
            test_seasons=["22024"],
        )


def test_make_temporal_split_rejects_temporal_reversal() -> None:
    with pytest.raises(TemporalSplitError, match="chronological"):
        make_temporal_split(
            _features(),
            train_seasons=["22024"],
            validation_seasons=[],
            test_seasons=["22022"],
        )

