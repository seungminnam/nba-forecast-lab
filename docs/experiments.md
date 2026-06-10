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

## Historical Baseline Experiment

**Run date:** 2026-06-10

**Data:** 13,209 regular-season games, 2015-16 through 2025-26

**Train:** 2015-16 through 2023-24, 10,749 games

**Validation:** 2024-25, 1,230 games

**Final baseline refit:** 2015-16 through 2024-25, 11,979 games

**Untouched test:** 2025-26, 1,230 games

### Validation Results

| Model | Brier Score | Log Loss | ROC-AUC | Accuracy |
|---|---:|---:|---:|---:|
| Constant home rate | 0.24865 | 0.69046 | 0.50000 | 0.54390 |
| Season win percentage | 0.22483 | 0.67707 | 0.69283 | 0.64065 |
| Elo | 0.21983 | 0.62953 | 0.71426 | 0.63984 |
| Logistic Regression | **0.20918** | **0.60514** | **0.72943** | **0.67642** |

### Untouched 2025-26 Test Results

| Model | Brier Score | Log Loss | ROC-AUC | Accuracy |
|---|---:|---:|---:|---:|
| Constant home rate | 0.24715 | 0.68745 | 0.50000 | 0.55447 |
| Season win percentage | 0.22179 | 0.69051 | 0.71839 | 0.66992 |
| Elo | 0.21360 | 0.61797 | 0.72531 | 0.66585 |
| Logistic Regression | **0.20649** | **0.60051** | **0.73357** | **0.68293** |

The current Logistic Regression baseline reduced Brier Score by **3.33%** and
Log Loss by **2.83%** relative to Elo on the untouched 2025-26 regular season.
These are measured baseline results, not the final selected or calibrated model.

The baseline evaluation interface and complete offline CLI workflow are also
tested on deterministic multi-season fixtures. Fixture metrics validate
plumbing only and are not reported as model performance.

Implemented baseline definitions:

| Model | Probability definition |
|---|---|
| Constant home rate | Mean home-win outcome in the supplied training period |
| Season win percentage | `0.5 + (home win pct - away win pct) / 2` |
| Elo | Sequential pre-game Elo probability with home advantage |
| Logistic Regression | Median imputation, standardization, and regularized binary Logistic Regression using the `liblinear` solver |

This document will record each historical configuration, data window, metrics,
and selection decision without replacing earlier results.
