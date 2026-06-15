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

## Playoff Generalization Backtest

The frozen model was replayed chronologically across all 85 completed 2025-26
playoff games without changing the model after observing playoff results:

| Brier Score | Log Loss | ECE | ROC-AUC | Accuracy |
|---:|---:|---:|---:|---:|
| **0.221755** | **0.635268** | **0.082080** | **0.672452** | **0.635294** |

This is measured playoff generalization evidence, not a new model-selection
period. Probability quality and calibration were worse than the regular-season
final test. The 2025-26 playoff results must not be used to select a revised
model and then reported again as unbiased evidence.

## Intended Use

- Historical pre-game probability replay
- Upcoming game probability estimates from explicit `as_of_date` snapshots
- Input probabilities for best-of-seven playoff simulation
- Historical playoff-series replay from an explicit cutoff and observed score
- Model-implied no-margin fair-odds display for probability communication
- Educational analysis of leakage-safe sports forecasting

## Limitations

- Trained and selected on regular-season team-level games; the measured
  2025-26 playoff backtest showed worse probability quality and calibration
  than the regular-season final test
- Continuous playoff inference sends season-to-date features such as
  `games_played` beyond their regular-season training range, so probability
  calibration may drift during later playoff rounds
- The verified local processed history ends on June 13, 2026 and includes all
  85 completed 2025-26 playoff games
- The current refresh does not include Play-In tournament games, so a
  Play-In qualifier's first-round state would omit those completed games
- Historical Replay freezes two venue probabilities at the cutoff and does
  not model future box-score-driven feature changes, injuries, momentum, or
  elimination-game psychology
- Model-implied fair odds are only a deterministic transform of model
  probabilities; they are not sportsbook prices, market observations, or
  evidence of betting profitability
- Canonical data currently lacks a stable source `series_id`; replay identifies
  a series from season, playoff type, and the selected team pair
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
