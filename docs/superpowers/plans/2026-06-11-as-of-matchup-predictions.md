# As-of Matchup Predictions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one leakage-safe scheduled-matchup feature row as of a declared
date and score it with a frozen model bundle.

**Architecture:** A focused feature module filters completed canonical games to
dates strictly before `as_of_date`, appends one ephemeral scheduled matchup,
and reuses the historical feature builders so training and inference share the
same definitions. A separate application workflow combines the feature row and
frozen bundle, while a CLI command handles file input and JSON output.

**Tech Stack:** Python, pandas, scikit-learn/joblib model bundles, pytest,
argparse

---

### Task 1: Scheduled Matchup Feature Snapshot

**Files:**
- Create: `src/nba_forecast/features/matchup_features.py`
- Create: `tests/features/test_matchup_features.py`
- Modify: `docs/data_dictionary.md`
- Modify: `docs/leakage_prevention.md`

- [x] **Step 1: Write a failing historical-parity test**

Build a scheduled matchup feature row using only games strictly before its
`as_of_date`, then compare all `MODEL_FEATURE_COLUMNS` with the existing
historical pre-game row for that same completed game.

- [x] **Step 2: Run the test and verify it fails because the module is missing**

Run:

```bash
pytest tests/features/test_matchup_features.py -v
```

Expected: collection fails because `matchup_features` does not exist.

- [x] **Step 3: Implement the minimum snapshot builder**

Add `ScheduledMatchup` and `build_scheduled_matchup_features`. Validate dates
and teams, filter history using `game_date < as_of_date`, create one ephemeral
scheduled row, reuse `build_game_features`, and return only the scheduled row.

- [x] **Step 4: Add and pass leakage regression tests**

Prove that changing or adding rows on or after `as_of_date` does not change the
scheduled feature row.

### Task 2: Frozen-Bundle Matchup Prediction Workflow

**Files:**
- Create: `src/nba_forecast/application/matchup_prediction.py`
- Create: `tests/application/test_matchup_prediction.py`
- Modify: `docs/architecture.md`

- [x] **Step 1: Write failing workflow tests**

Test that the workflow returns one home-win probability, model version,
`as_of_date`, and the exact feature row used for prediction.

- [x] **Step 2: Implement the minimum application workflow**

Accept completed games, a `ScheduledMatchup`, `as_of_date`, and a loaded
`ModelBundle`. Build the feature row and score it without training.

- [x] **Step 3: Pass focused workflow tests**

Run:

```bash
pytest tests/application/test_matchup_prediction.py -v
```

### Task 3: Reproducible CLI and Documentation

**Files:**
- Modify: `src/nba_forecast/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`
- Modify: `docs/runbook.md`
- Modify: `docs/architecture.md`

- [x] **Step 1: Write a failing CLI report test**

Test `predict-matchup` against temporary games and bundle files and assert the
JSON report includes matchup identity, cutoff, model version, and probability.

- [x] **Step 2: Implement `predict-matchup`**

Load completed games and the frozen bundle, run the shared application
workflow, and write `artifacts/predictions/matchup_prediction.json`.

- [x] **Step 3: Document the command and current data limitation**

State that the current local processed artifact ends on April 12, 2026 and
must be refreshed with playoff games before making a current Finals claim.

### Task 4: Verification and Publication

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-as-of-matchup-predictions.md`

- [x] **Step 1: Run full verification**

```bash
ruff check .
mypy src
pytest
git diff --check
```

- [x] **Step 2: Audit public claims and generated artifacts**

Confirm no generated model, prediction JSON, or local collaboration
instructions are staged.

- [ ] **Step 3: Commit, push, and open a Draft PR**

Use neutral project-focused Git and PR language.
