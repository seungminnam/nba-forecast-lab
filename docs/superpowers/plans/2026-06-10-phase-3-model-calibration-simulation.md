# Phase 3 Model, Calibration, and Simulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce measured multi-season baseline and XGBoost results, select a leakage-safe calibrated probability model, and power a tested best-of-seven series simulator.

**Architecture:** A cache-first history command collects season-level raw extracts and rebuilds one chronological feature table. Training-window experiments compare recent 3-season, recent 5-season, and decayed full-history fits. Calibration is fit only on a validation season, evaluated on the untouched 2025-26 test season, and exposed through a game-probability interface consumed by a model-independent simulator.

**Tech Stack:** Python 3.9+, pandas, scikit-learn, XGBoost, joblib, pytest

---

### Task 1: Historical Backfill Workflow and Measured Baselines

**Files:**
- Modify: `src/nba_forecast/data/source_nba.py`
- Modify: `src/nba_forecast/cli.py`
- Modify: `tests/data/test_source_nba.py`
- Modify: `tests/test_cli.py`
- Modify: `docs/runbook.md`
- Modify: `docs/source_report.md`
- Modify: `docs/experiments.md`

- [x] **Step 1: Write failing multi-season fetch tests**

Assert a cache-first history function requests every supplied season and season
type, reuses existing caches, and returns stable raw paths.

- [x] **Step 2: Implement and expose `fetch-history`**

Expose a command that fetches configured historical seasons and prints source
row counts without combining or mutating raw extracts.

- [x] **Step 3: Fetch and build real historical regular-season data**

Fetch 2015-16 through 2025-26, combine raw files into canonical games, build
features, and evaluate current baselines using:

```text
Train: 2015-16 through 2023-24
Validation: 2024-25
Test: 2025-26
```

- [x] **Step 4: Record measured source coverage and baseline results**

Record commands, row counts, date range, split sizes, and metrics in source and
experiment documentation. Do not commit generated data.

- [x] **Step 5: Verify and commit**

```bash
git commit -m "feat: backfill and evaluate historical nba baselines"
```

### Task 2: Training Windows and XGBoost Evaluation

**Files:**
- Modify: `pyproject.toml`
- Create: `src/nba_forecast/models/xgboost_model.py`
- Create: `src/nba_forecast/evaluation/model_comparison.py`
- Create: `tests/models/test_xgboost_model.py`
- Create: `tests/evaluation/test_model_comparison.py`
- Modify: `docs/experiments.md`

- [x] **Step 1: Add XGBoost dependency and failing tests**

Test bounded probabilities, deterministic fixed-seed fitting, and training
window selection for recent 3 seasons, recent 5 seasons, and decayed full
history.

- [x] **Step 2: Implement XGBoost pipeline**

Use median imputation and a conservative fixed configuration before any tuning.
Support optional sample weights for older-game decay.

- [x] **Step 3: Implement comparable window experiment**

Evaluate Logistic Regression and XGBoost under the three training-window
strategies on identical validation rows.

- [x] **Step 4: Run real history experiment and document selection**

Select the model/window using validation Brier Score and Log Loss. Keep the
2025-26 test season untouched.

- [x] **Step 5: Verify and commit**

```bash
git commit -m "feat: compare xgboost training windows"
```

### Task 3: Probability Calibration and Model Artifact

**Files:**
- Create: `src/nba_forecast/models/calibration.py`
- Create: `src/nba_forecast/models/artifacts.py`
- Create: `tests/models/test_calibration.py`
- Create: `tests/models/test_artifacts.py`
- Create: `docs/model_card.md`
- Modify: `docs/experiments.md`

- [x] **Step 1: Write failing calibration leakage tests**

Chronologically split validation predictions into calibration-fit and
calibration-selection halves. Fit Platt and Isotonic only on the earlier half,
select Raw, Platt, or Isotonic only on the later half, and assert final test
labels never enter fitting or selection.

- [x] **Step 2: Implement calibrators**

Use Logistic Regression for Platt scaling and `IsotonicRegression` for isotonic
calibration. Select raw, Platt, or Isotonic on the later validation half, refit
the selected calibrator on full validation predictions, then evaluate the
frozen bundle once on the final test season.

- [x] **Step 3: Persist versioned model bundle**

Save model, calibrator, feature columns, training seasons, validation season,
test season, creation timestamp, and measured metrics together.

- [x] **Step 4: Write model card and measured final test result**

Document intended use, evaluation design, selected calibration, limitations,
and honest final test metrics.

- [x] **Step 5: Verify and commit**

```bash
git commit -m "feat: calibrate and version selected probability model"
```

### Task 4: Best-of-Seven Series Simulator

**Files:**
- Create: `src/nba_forecast/simulation/__init__.py`
- Create: `src/nba_forecast/simulation/series.py`
- Create: `tests/simulation/test_series.py`
- Modify: `docs/architecture.md`
- Modify: `docs/data_dictionary.md`

- [x] **Step 1: Write failing schedule and stopping tests**

Assert schedule `H, H, A, A, H, A, H`, stop at four wins, deterministic seeded
output, and probability distribution totals.

- [x] **Step 2: Implement simulator**

Consume a callable that returns the designated home team's win probability.
Run at least 10,000 simulations by default and report series winner, win-in-N
distribution, and expected length.

- [x] **Step 3: Verify simulator invariants and commit**

```bash
git commit -m "feat: add best of seven playoff simulator"
```

### Task 5: Model and Simulation CLI Workflows

**Files:**
- Modify: `src/nba_forecast/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`
- Modify: `docs/runbook.md`
- Modify: `docs/experiments.md`
- Modify: `docs/superpowers/plans/2026-06-10-phase-3-model-calibration-simulation.md`

- [x] **Step 1: Write failing CLI tests**

Test commands that run a documented model experiment and a seeded series
simulation against prepared fixture artifacts.

- [x] **Step 2: Implement experiment and simulation commands**

Commands write machine-readable reports and never train during an application
request path.

- [ ] **Step 3: Run full historical workflow**

Run the documented history, feature, evaluation, selection, calibration, and
simulation commands.

- [x] **Step 4: Run complete verification and documentation audit**

```bash
ruff check .
mypy src
pytest
```

- [ ] **Step 5: Mark the plan complete and commit**

```bash
git commit -m "docs: finalize calibrated model and simulator workflow"
```
