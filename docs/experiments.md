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

## Season-Agnostic Playoff Backtest

**Pre-registered:** 2026-06-15

**First evaluation season:** 2025-26 playoffs

**Future operational target:** 2026-27 playoffs and later seasons

### Pre-Experiment Hypothesis

The frozen regular-season-selected model is expected to remain directionally
useful during the playoffs, but its Brier Score and calibration are expected
to worsen relative to the untouched 2025-26 regular-season test. Playoff teams
are stronger and more closely matched, rotations change, and the current
feature set does not model injuries, player availability, or playoff-specific
rotation changes.

The model is expected to provide more stable series probabilities than
single-game winner picks because a best-of-seven simulation aggregates
multiple uncertain game probabilities. This is a hypothesis, not a measured
result.

### Temporal and Reuse Contract

The backtest will accept a `season_key` rather than hard-coded 2026 teams or
dates. For each completed playoff game, it will:

1. generate the forecast using only games with `game_date < as_of_date`;
2. persist the forecast before reading the game result;
3. join the result after prediction creation;
4. evaluate game probabilities separately from series probabilities.

The 2025-26 playoffs are the first measured replay. Results may motivate future
features, but the same 2025-26 playoff results cannot then be reused as an
unbiased evaluation of those changes. Later model changes require
walk-forward evidence on later seasons.

### Planned Metrics and Slices

Primary game-level metrics:

- Brier Score
- Log Loss
- Expected Calibration Error

Secondary metrics:

- ROC-AUC
- Accuracy

Planned slices:

- playoff round;
- home and away;
- probability bucket;
- elimination and non-elimination games;
- series game number.

Series-level evaluation will report the probability assigned to the eventual
winner before each game, winner accuracy at declared cutoffs, and predicted
versus observed final length. During future playoffs, the same workflow will
write immutable pre-game prediction records and attach outcomes only after
games finish.

### 2025-26 Measured Results

**Run date:** 2026-06-15

**Games:** 85 completed playoff games from April 18 through June 13, 2026

**Frozen model:** `2026-06-11-recent5-raw`

| Brier Score | Log Loss | ECE | ROC-AUC | Accuracy |
|---:|---:|---:|---:|---:|
| **0.221755** | **0.635268** | **0.082080** | **0.672452** | **0.635294** |

For context, the same frozen model's untouched 2025-26 regular-season test
produced a Brier Score of `0.207254`, Log Loss of `0.601983`, ECE of
`0.039914`, ROC-AUC of `0.732116`, and Accuracy of `0.689431`.

The playoff Brier Score was approximately `7.0%` worse and Log Loss was
approximately `5.5%` worse. ECE increased by approximately `0.0422`, while
ROC-AUC and Accuracy declined by approximately `0.0597` and `0.0541`
respectively.

### Interpretation

The pre-experiment hypothesis was supported. The frozen model retained some
ranking and classification signal, but its probabilities generalized less
reliably to the playoff population. The average predicted home-win probability
was `55.32%`, closely matching the observed playoff home-win rate of `55.29%`,
but the higher ECE shows that agreement in the overall mean did not translate
to reliable calibration across probability buckets.

The result does not establish why performance worsened. Plausible explanations
include stronger and more closely matched teams, playoff rotation changes,
injuries, and the current absence of player availability features. Those are
future hypotheses, not conclusions from this backtest.

The 2025-26 playoff backtest is now evaluation evidence and must not be used to
select a revised model and then reported again as an unbiased result. Future
changes require validation on earlier playoff seasons or forward evaluation
on 2026-27 and later playoffs.
