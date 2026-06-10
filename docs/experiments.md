# Experiments

## Evaluation Contract

- Random train/test splits are prohibited.
- Callers explicitly provide train, validation, and test season identifiers.
- Season groups must be disjoint and chronological.
- Model selection and calibration must not use the final test period.

## Primary Metrics

1. Brier Score
2. Log Loss
3. Calibration quality

ROC-AUC and Accuracy are secondary context. Accuracy is not the optimization
target because the product emits probabilities for simulation.

## Current Results

The baseline evaluation interface and complete offline CLI workflow are
implemented and tested on deterministic multi-season fixtures. Fixture metrics
validate plumbing only and are not reported as model performance. A historical
multi-season comparison has not been completed yet.

Implemented baseline definitions:

| Model | Probability definition |
|---|---|
| Constant home rate | Mean home-win outcome in the supplied training period |
| Season win percentage | `0.5 + (home win pct - away win pct) / 2` |
| Elo | Sequential pre-game Elo probability with home advantage |
| Logistic Regression | Median imputation, standardization, and regularized Logistic Regression |

This document will record each historical configuration, data window, metrics,
and selection decision without replacing earlier results.
