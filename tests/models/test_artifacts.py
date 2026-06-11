from datetime import datetime, timezone

import pandas as pd

from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS
from nba_forecast.models.artifacts import (
    ModelBundle,
    ModelBundleMetadata,
    load_model_bundle,
    save_model_bundle,
)
from nba_forecast.models.baselines import fit_logistic_regression
from nba_forecast.models.calibration import fit_calibrator


def test_model_bundle_round_trip_preserves_predictions_and_metadata(tmp_path) -> None:
    frame = _model_frame(20)
    model = fit_logistic_regression(frame)
    raw_probabilities = pd.Series(
        model.predict_proba(frame[list(MODEL_FEATURE_COLUMNS)])[:, 1]
    )
    calibrator = fit_calibrator("platt", raw_probabilities, frame["home_win"])
    metadata = ModelBundleMetadata(
        version="2026-06-11-recent5-platt",
        created_at=datetime(2026, 6, 11, tzinfo=timezone.utc).isoformat(),
        base_model="logistic_regression",
        calibration_method="platt",
        feature_columns=MODEL_FEATURE_COLUMNS,
        training_seasons=("22020", "22021", "22022", "22023", "22024"),
        calibration_season="22024",
        test_season="22025",
        metrics={"brier_score": 0.2},
    )
    bundle = ModelBundle(model=model, calibrator=calibrator, metadata=metadata)
    path = tmp_path / "model.joblib"

    save_model_bundle(bundle, path)
    restored = load_model_bundle(path)

    assert restored.metadata == metadata
    assert restored.predict_probability(frame).tolist() == bundle.predict_probability(
        frame
    ).tolist()


def _model_frame(rows: int) -> pd.DataFrame:
    data = {
        feature: [
            ((-1) ** index) * (position + 1) / 10
            for index in range(rows)
        ]
        for position, feature in enumerate(MODEL_FEATURE_COLUMNS)
    }
    data["home_win"] = [index % 2 for index in range(rows)]
    return pd.DataFrame(data)
