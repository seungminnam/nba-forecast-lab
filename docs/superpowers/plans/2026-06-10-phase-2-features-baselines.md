# Phase 2 Leakage-Safe Features and Baselines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Completed and verified on 2026-06-10

**Goal:** Build point-in-time NBA team features, Elo and Logistic Regression baselines, and honest season-based evaluation from validated canonical games.

**Architecture:** Canonical games retain the traditional box-score inputs needed to estimate possessions and ratings. A team-state builder explodes games into team-perspective rows, shifts all outcomes before rolling, updates Elo only after each game, and then assembles one home-minus-away model row per game. Evaluation uses explicit season ordering and stores comparable probability metrics.

**Tech Stack:** Python 3.9+, pandas, NumPy, scikit-learn, pytest, Ruff, mypy

---

### Task 1: Extend Canonical Games with Rating Inputs

**Files:**
- Modify: `tests/fixtures/team_game_rows.csv`
- Modify: `src/nba_forecast/data/contracts.py`
- Modify: `src/nba_forecast/data/transform.py`
- Modify: `tests/data/test_transform.py`
- Modify: `docs/data_dictionary.md`

- [x] **Step 1: Add failing canonical-stat tests**

Add traditional box-score columns `FGA`, `FGM`, `FTA`, `OREB`, and `TOV` to
the fixture. Assert canonical games include home and away versions of each
field.

- [x] **Step 2: Verify focused test failure**

Run `pytest tests/data/test_transform.py -v`.

- [x] **Step 3: Extend contracts and transformation**

Map required source box-score fields into stable home and away canonical
columns. The transformation remains one row per completed game.

- [x] **Step 4: Verify and document**

Run `pytest tests/data/test_transform.py tests/data/test_validate.py -v`,
`ruff check .`, and `mypy src`. Update the data dictionary.

- [x] **Step 5: Commit**

```bash
git commit -m "feat: retain rating inputs in canonical games"
```

### Task 2: Leakage-Safe Team State Features

**Files:**
- Create: `src/nba_forecast/features/__init__.py`
- Create: `src/nba_forecast/features/team_state.py`
- Create: `tests/features/test_team_state.py`
- Create: `docs/leakage_prevention.md`
- Modify: `docs/data_dictionary.md`

- [x] **Step 1: Write failing feature and leakage tests**

Tests assert:

- Each game produces one team-state row per team.
- Current-game outcomes do not affect current-game pre-game features.
- Changing a game's outcome changes only later feature rows.
- Rest days and back-to-back flags use previous game dates.
- Rolling values require at least one prior game and use windows 5, 10, 20.

- [x] **Step 2: Verify focused test failure**

Run `pytest tests/features/test_team_state.py -v`.

- [x] **Step 3: Implement team-state builder**

Estimate possessions with:

```text
FGA + 0.44 * FTA - OREB + TOV
```

Calculate completed-game offensive, defensive, and net ratings, then produce
shifted expanding and rolling pre-game state per team and season.

- [x] **Step 4: Verify mutation-based leakage protection**

Run `pytest tests/features/test_team_state.py -v`, `ruff check .`, and
`mypy src`.

- [x] **Step 5: Document leakage rules and commit**

```bash
git commit -m "feat: build leakage-safe rolling team state"
```

### Task 3: Pre-Game Elo and Game Feature Rows

**Files:**
- Create: `src/nba_forecast/features/elo.py`
- Create: `src/nba_forecast/features/game_features.py`
- Create: `tests/features/test_elo.py`
- Create: `tests/features/test_game_features.py`
- Modify: `docs/data_dictionary.md`
- Modify: `docs/leakage_prevention.md`

- [x] **Step 1: Write failing Elo tests**

Assert both teams start at the configured rating, the current game exposes
pre-game ratings, and ratings update only after the result.

- [x] **Step 2: Implement sequential Elo**

Use a configurable base rating, K-factor, home advantage, and offseason
mean-reversion. Return a pre-game rating and probability for every game.

- [x] **Step 3: Write failing game-feature tests**

Assert one model row per game with home-minus-away differences, separate home
and away back-to-back indicators, and no label columns among model features.

- [x] **Step 4: Implement game-feature assembly**

Join home and away team-state rows and Elo rows by game identifier and emit
stable model feature columns plus the `home_win` target.

- [x] **Step 5: Verify, document, and commit**

Run all feature tests, `ruff check .`, and `mypy src`.

```bash
git commit -m "feat: assemble pregame elo and model features"
```

### Task 4: Season-Based Splits and Probability Metrics

**Files:**
- Create: `src/nba_forecast/evaluation/__init__.py`
- Create: `src/nba_forecast/evaluation/splits.py`
- Create: `src/nba_forecast/evaluation/metrics.py`
- Create: `tests/evaluation/test_splits.py`
- Create: `tests/evaluation/test_metrics.py`
- Create: `docs/experiments.md`

- [x] **Step 1: Write failing split and metric tests**

Assert train seasons precede validation/test seasons, splits never overlap, and
known probability examples produce expected Brier Score and Log Loss.

- [x] **Step 2: Implement explicit season splits**

Provide a function that selects ordered train, validation, and test frames from
caller-supplied season identifiers and rejects temporal reversals.

- [x] **Step 3: Implement probability metrics**

Return Brier Score, Log Loss, ROC-AUC when both classes exist, and Accuracy at a
0.5 threshold.

- [x] **Step 4: Verify, document, and commit**

```bash
git commit -m "feat: add temporal splits and probability metrics"
```

### Task 5: Baseline Model Evaluation

**Files:**
- Modify: `pyproject.toml`
- Create: `src/nba_forecast/models/__init__.py`
- Create: `src/nba_forecast/models/baselines.py`
- Create: `src/nba_forecast/evaluation/baselines.py`
- Create: `tests/models/test_baselines.py`
- Create: `tests/evaluation/test_baseline_evaluation.py`
- Modify: `docs/experiments.md`

- [x] **Step 1: Add scikit-learn dependency and failing baseline tests**

Test constant home-rate, season-win-percentage, Elo probability, and
regularized Logistic Regression predictors.

- [x] **Step 2: Implement baseline predictors**

All predictors expose home-win probabilities clipped away from exact 0 and 1.
Logistic Regression is trained only on caller-supplied training rows.

- [x] **Step 3: Implement comparable evaluation table**

Evaluate every baseline using the same test rows and metrics, returning one row
per model.

- [x] **Step 4: Verify, document, and commit**

Run model/evaluation tests, full quality checks, and record only measured
fixture-level behavior in experiment docs.

```bash
git commit -m "feat: compare nba probability baselines"
```

### Task 6: Feature and Baseline CLI Workflow

**Files:**
- Modify: `src/nba_forecast/cli.py`
- Modify: `tests/test_cli.py`
- Create: `tests/fixtures/multi_season_team_game_rows.csv`
- Modify: `README.md`
- Modify: `docs/runbook.md`
- Modify: `docs/architecture.md`

- [x] **Step 1: Write failing CLI workflow test**

Build processed games from the fixture, generate `features/games.parquet`, and
write `artifacts/reports/baseline_metrics.csv` using explicit train and test
seasons.

- [x] **Step 2: Implement feature and baseline commands**

Expose:

```bash
nba-forecast build-features --games-parquet PATH --output-dir PATH
nba-forecast evaluate-baselines --features-parquet PATH --train-seasons ... --test-season ...
```

- [x] **Step 3: Run offline end-to-end workflow**

Run the documented commands against a deterministic multi-season fixture.

- [x] **Step 4: Run complete verification**

Run:

```bash
ruff check .
mypy src
pytest
```

- [x] **Step 5: Audit documentation and commit**

```bash
git commit -m "feat: add feature and baseline evaluation workflow"
```
