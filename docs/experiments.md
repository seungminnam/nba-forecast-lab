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

## Training Window and XGBoost Experiment

**Run date:** 2026-06-11

**Fixed feature set:** The existing 19 `MODEL_FEATURE_COLUMNS`. No new feature
groups are introduced in this experiment.

**Selection period:** 2024-25 validation season (`22024`)

**Untouched period:** 2025-26 test season (`22025`). This period is excluded
from training-window and model selection.

### Pre-Experiment Hypothesis

Recent five-season XGBoost is expected to achieve the best validation Brier
Score, but its advantage over Logistic Regression is expected to be small.
The current feature set is compact and contains several correlated summaries
of team strength, including Elo, win percentage, and rolling ratings.
Logistic Regression can already model much of their approximately monotonic
relationship with win probability, while XGBoost may gain from nonlinear
effects and interactions such as rest, back-to-back status, and season
progress.

### Compared Training Windows

| Window | Training seasons relative to validation | Weighting |
|---|---|---|
| Recent 3 | Most recent three completed seasons | Equal |
| Recent 5 | Most recent five completed seasons | Equal |
| Decayed full history | Every completed historical season | `0.8` annual decay, newest training season weighted `1.0` |

Both Logistic Regression and a conservative fixed-configuration XGBoost model
will be evaluated on identical validation rows. The winner is selected by
validation Brier Score, with Log Loss as the tie-breaker. Hyperparameter
tuning and feature expansion are deliberately deferred so this experiment
isolates model class and training-window effects.

### Validation Results

| Model | Training window | Train rows | Brier Score | Log Loss | ROC-AUC | Accuracy |
|---|---|---:|---:|---:|---:|---:|
| Logistic Regression | Recent 5 | 5,829 | **0.208594** | **0.603709** | 0.730156 | 0.678049 |
| Logistic Regression | Decayed full history | 10,749 | 0.208670 | 0.603964 | **0.730329** | **0.680488** |
| Logistic Regression | Recent 3 | 3,690 | 0.208736 | 0.604207 | 0.730118 | 0.678862 |
| XGBoost | Decayed full history | 10,749 | 0.211099 | 0.609608 | 0.723284 | 0.653659 |
| XGBoost | Recent 3 | 3,690 | 0.211292 | 0.610053 | 0.722403 | 0.655285 |
| XGBoost | Recent 5 | 5,829 | 0.211721 | 0.611173 | 0.721448 | 0.672358 |

### Interpretation and Selection

The hypothesis was only partly supported. The recent five-season window
produced the best Brier Score, but Logistic Regression outperformed every
XGBoost window. Recent-five Logistic Regression improved Brier Score by
approximately `1.19%` relative to the best XGBoost configuration and by
approximately `0.28%` relative to the earlier equal-weight full-history
Logistic Regression validation result.

The three Logistic Regression windows are extremely close. This experiment
does not establish that five seasons are universally optimal or that XGBoost
is unsuitable for NBA forecasting. It shows that, for the current compact and
correlated 19-feature set, the added model complexity did not improve
validation probability quality under the fixed conservative configuration.

Recent-five Logistic Regression is selected for the next calibration
experiment because it has the lowest validation Brier Score and Log Loss. The
2025-26 test season remains untouched during this selection. Feature-group
ablation experiments will later test whether efficiency detail, opponent
strength, or head-to-head history creates nonlinear signal that changes the
model comparison.

## Probability Calibration Experiment

**Run date:** 2026-06-11

**Selected base model:** Recent-five Logistic Regression

**Calibration selection season:** 2024-25 (`22024`), split chronologically into
an earlier calibration-fit half and a later calibration-selection half

**Untouched final test:** 2025-26 (`22025`)

### Pre-Experiment Hypothesis

Platt scaling is expected to produce the best selection-half Brier Score, but
the improvement over raw Logistic Regression probabilities is expected to be
small. Logistic Regression probabilities are often reasonably calibrated
already, while Platt scaling can make a low-variance correction for systematic
overconfidence or underconfidence. Isotonic calibration is expected to be less
stable because its flexible step function can fit random patterns in the
approximately half-season calibration sample.

### Corrected Temporal Contract

The earlier Phase 3 plan proposed fitting calibrators on validation predictions
and comparing raw, Platt, and Isotonic results on the final test season. That
would use the test period to choose a calibration method and contaminate the
final estimate. The corrected workflow is:

```text
2019-20 through 2023-24 -> fit selected base model
2024-25 first half      -> fit Platt and Isotonic calibrators
2024-25 second half     -> select Raw, Platt, or Isotonic
2024-25 full season     -> refit only the selected calibrator
2020-21 through 2024-25 -> refit recent-five base model
2025-26                 -> evaluate the frozen bundle exactly once
```

Selection uses Brier Score first and Log Loss as the tie-breaker. Expected
Calibration Error is reported as supporting calibration context. The selected
method may be Raw if neither calibrator improves validation probability
quality.

### Calibration Selection Results

Each validation half contains 615 chronologically ordered games.

| Method | Brier Score | Log Loss | ECE | ROC-AUC | Accuracy |
|---|---:|---:|---:|---:|---:|
| Raw | **0.201537** | **0.588339** | **0.032448** | **0.750629** | **0.689431** |
| Isotonic | 0.204388 | 0.630123 | 0.037552 | 0.744941 | 0.682927 |
| Platt | 0.205197 | 0.598572 | 0.053973 | 0.750629 | 0.686179 |

The hypothesis was not supported. Raw Logistic Regression probabilities
outperformed both calibration methods on the later validation half. Platt
scaling preserved ranking, as expected, but worsened probability quality.
Isotonic calibration changed ranking through tied step outputs and had the
worst Log Loss, consistent with instability from a small calibration sample.

Raw is therefore the selected calibration method. This is an intentional
measured decision, not an omitted calibration step.

### Frozen 2025-26 Final Test Result

After calibration selection, the base model was refit on the recent five
seasons from 2020-21 through 2024-25. Raw was retained as the frozen
calibration method and the 2025-26 test season was evaluated once.

| Method | Brier Score | Log Loss | ECE | ROC-AUC | Accuracy |
|---|---:|---:|---:|---:|---:|
| Raw | **0.207254** | **0.601983** | **0.039914** | **0.732116** | **0.689431** |

This final result is slightly worse than the earlier equal-weight
full-history Logistic Regression baseline test Brier Score of `0.20649`.
That difference is retained rather than using the test result to reverse the
validation-based recent-five selection. Future feature-group experiments must
use new validation or walk-forward evidence rather than repeatedly optimizing
against this final test season.
