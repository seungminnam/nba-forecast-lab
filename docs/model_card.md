# Model Card

## Model Summary

**Version:** `2026-06-11-recent5-raw`

**Purpose:** Estimate an NBA home team's pre-game win probability using only
information available before tip-off.

**Base model:** Regularized Logistic Regression with median imputation and
standardization

**Calibration method:** Raw probabilities retained after Raw, Platt, and
Isotonic comparison

**Feature set:** The 19 authoritative pre-game features in
`MODEL_FEATURE_COLUMNS`

## Training and Selection

- Base-model and training-window selection period: 2024-25 validation season
- Selected training window: recent five seasons
- Calibration fit: first chronological half of 2024-25, 615 games
- Calibration selection: second chronological half of 2024-25, 615 games
- Final base-model training: 2020-21 through 2024-25, 6,000 games
- Final untouched test: 2025-26 regular season, 1,230 games

Raw probabilities had the best calibration-selection Brier Score and Log Loss.
Neither Platt nor Isotonic calibration was retained. The final bundle still
stores the identity calibrator explicitly so downstream consumers use one
consistent probability interface.

## Final Test Metrics

| Brier Score | Log Loss | ECE | ROC-AUC | Accuracy |
|---:|---:|---:|---:|---:|
| **0.207254** | **0.601983** | **0.039914** | **0.732116** | **0.689431** |

The 2025-26 test season was evaluated once after model-window and calibration
selection. Its result was not used to revise those decisions.
ECE is the weighted average absolute gap between predicted probability and
observed win rate across ten probability bins.

## Intended Use

- Historical pre-game probability replay
- Upcoming game probability estimates from explicit `as_of_date` snapshots
- Input probabilities for best-of-seven playoff simulation
- Educational analysis of leakage-safe sports forecasting

## Limitations

- Uses regular-season team-level history only
- The current local processed history ends on April 12, 2026 and must include
  current playoff games before producing a current Finals estimate
- Does not currently include injuries, player availability, travel, roster
  continuity, head-to-head matchup history, or playoff-specific effects
- Current rolling features contain correlated summaries of team strength
- Calibration selection used only half of one season and may be sensitive to
  temporal drift
- The 2024-25 validation season informed both model-window selection and
  calibration selection, increasing validation-overfitting risk even though
  the final test season remained untouched
- The final test result should not be repeatedly used for feature or model
  selection
- Does not provide betting advice or profitability claims

## Reproducibility and Artifact

Generated bundles are stored under `artifacts/models/` and excluded from Git.
The bundle contains the fitted base model, selected calibrator, authoritative
feature list, training seasons, calibration and test seasons, creation time,
and measured final metrics.

See `docs/experiments.md` for hypotheses and complete comparisons, and
`docs/runbook.md` for operational commands.
