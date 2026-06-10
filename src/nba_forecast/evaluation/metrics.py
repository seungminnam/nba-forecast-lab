"""Probability-focused model metrics."""

import math
from collections.abc import Sequence

import pandas as pd


def probability_metrics(
    y_true: Sequence[int],
    probabilities: Sequence[float],
) -> dict[str, float]:
    """Calculate Brier Score, Log Loss, ROC-AUC, and Accuracy."""
    targets = pd.Series(y_true, dtype="float64")
    predicted = pd.Series(probabilities, dtype="float64")
    if len(targets) == 0 or len(targets) != len(predicted):
        raise ValueError("Targets and probabilities must be non-empty and equal length")

    clipped = predicted.clip(1e-15, 1 - 1e-15)
    brier_score = float(((predicted - targets) ** 2).mean())
    log_loss = float(
        -(targets * clipped.map(math.log) + (1 - targets) * (1 - clipped).map(math.log))
        .mean()
    )
    accuracy = float(((predicted >= 0.5).astype(int) == targets).mean())
    roc_auc = _roc_auc(targets, predicted)
    return {
        "brier_score": brier_score,
        "log_loss": log_loss,
        "roc_auc": roc_auc,
        "accuracy": accuracy,
    }


def _roc_auc(targets: pd.Series, predicted: pd.Series) -> float:
    positives = int(targets.sum())
    negatives = len(targets) - positives
    if positives == 0 or negatives == 0:
        return math.nan

    ranks = predicted.rank(method="average")
    positive_rank_sum = float(ranks.loc[targets == 1].sum())
    return (
        positive_rank_sum - positives * (positives + 1) / 2
    ) / (positives * negatives)

