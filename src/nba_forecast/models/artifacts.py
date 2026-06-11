"""Versioned persistence for a fitted probability model bundle."""

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from nba_forecast.models.baselines import PROBABILITY_EPSILON
from nba_forecast.models.calibration import ProbabilityCalibrator


@dataclass(frozen=True)
class ModelBundleMetadata:
    """Auditable metadata stored beside fitted model objects."""

    version: str
    created_at: str
    base_model: str
    calibration_method: str
    feature_columns: tuple[str, ...]
    training_seasons: tuple[str, ...]
    calibration_season: str
    test_season: str
    metrics: dict[str, float]


@dataclass(frozen=True)
class ModelBundle:
    """Frozen base model, calibrator, and metadata."""

    model: Pipeline
    calibrator: ProbabilityCalibrator
    metadata: ModelBundleMetadata

    def predict_probability(self, frame: pd.DataFrame) -> pd.Series:
        """Return calibrated home-win probabilities."""
        values = self.model.predict_proba(
            frame[list(self.metadata.feature_columns)]
        )[:, 1]
        raw = pd.Series(values, index=frame.index).clip(
            PROBABILITY_EPSILON,
            1 - PROBABILITY_EPSILON,
        )
        return self.calibrator.predict(raw)


def save_model_bundle(bundle: ModelBundle, path: Path) -> None:
    """Atomically persist a model bundle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(bundle, temporary_path)
    temporary_path.replace(path)


def load_model_bundle(path: Path) -> ModelBundle:
    """Load a persisted model bundle."""
    bundle = joblib.load(path)
    if not isinstance(bundle, ModelBundle):
        raise TypeError("Artifact does not contain a ModelBundle")
    return bundle
