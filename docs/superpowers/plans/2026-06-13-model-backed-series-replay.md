# Model-Backed Series Historical Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruct a real playoff series at any declared cutoff and simulate
the remaining games using two frozen model-derived venue probabilities.

**Architecture:** Extend the model-independent simulator to accept an active
observed score, then add a focused replay application that derives that score
from canonical playoff games and reuses scheduled-matchup inference for both
venue directions. Expose the shared workflow through a JSON CLI report and a
separate model-backed Streamlit tab while preserving the Assumption Lab.

**Tech Stack:** Python, pandas, scikit-learn/joblib model bundles, Monte Carlo,
argparse, Streamlit, pytest

---

### Task 1: Remaining-Series Simulation From Observed Score

**Files:**
- Modify: `src/nba_forecast/simulation/series.py`
- Modify: `tests/simulation/test_series.py`
- Modify: `docs/decisions/0002-series-simulation-contract.md`

- [x] Write failing tests for a `1-3` initial score, skipped schedule positions,
  reachable outcome labels, and invalid completed scores.
- [x] Run focused tests and verify failure because initial wins are unsupported.
- [x] Add `initial_team_a_wins` and `initial_team_b_wins` keyword arguments.
- [x] Initialize each Monte Carlo run from the observed score and iterate only
  over remaining home-court schedule positions.
- [x] Reject negative, impossible, completed, or over-seven-game initial
  scores.
- [x] Run focused simulation tests.

### Task 2: Historical Series Reconstruction

**Files:**
- Create: `src/nba_forecast/application/series_replay.py`
- Create: `tests/application/test_series_replay.py`

- [x] Write failing tests that reconstruct `0-0`, mid-series, and completed
  states using only playoff games strictly before `as_of_date`.
- [x] Add immutable replay input and observed-state dataclasses.
- [x] Filter by season key, playoff type, unordered team pair, and cutoff.
- [x] Validate observed home-court order, win counts, completion boundary, and
  maximum seven games.
- [x] Run focused reconstruction tests.

### Task 3: Frozen Model-Backed Replay Workflow

**Files:**
- Modify: `src/nba_forecast/application/series_replay.py`
- Modify: `tests/application/test_series_replay.py`

- [x] Write failing tests proving the workflow scores exactly two venue
  directions at the same cutoff and starts simulation from reconstructed wins.
- [x] Build two scheduled matchups using the declared next-game date and reuse
  `predict_scheduled_matchup`.
- [x] Supply the two frozen venue probabilities to the remaining-series
  simulator.
- [x] Return chart-ready tables and an auditable JSON-serializable report.
- [x] Add a mutation test proving Game 4 and later changes cannot alter a
  pre-Game-4 replay.
- [x] Report completed series without scoring future matchups or simulating.
- [x] Run focused application tests.

### Task 4: Reproducible CLI Report

**Files:**
- Modify: `src/nba_forecast/cli.py`
- Modify: `tests/test_cli.py`

- [x] Write a failing `replay-series` CLI test using offline games and a test
  model bundle.
- [x] Add explicit games, bundle, cutoff, next-game date, season, team,
  simulation, seed, and output arguments.
- [x] Load artifacts, call the shared replay workflow, and write
  `artifacts/reports/model_backed_series_replay.json`.
- [x] Run focused CLI tests.

### Task 5: Two-Mode Streamlit Product Surface

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_streamlit_app.py`

- [x] Write failing AppTest assertions for Model-Backed Historical Replay and
  Assumption Lab tabs.
- [x] Render the replay tab with current Finals defaults, artifact checks,
  observed score, frozen probabilities, assumptions, and remaining outcome
  charts.
- [x] Preserve the existing Assumption Lab controls and validation behavior.
- [x] Ensure missing artifacts show an actionable replay message without
  breaking the Assumption Lab.
- [x] Run Streamlit AppTest.

### Task 6: Documentation and Live Replay Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/data_dictionary.md`
- Modify: `docs/leakage_prevention.md`
- Modify: `docs/model_card.md`
- Modify: `docs/runbook.md`
- Modify: `docs/decisions/0002-series-simulation-contract.md`
- Modify: `docs/superpowers/plans/2026-06-13-model-backed-series-replay.md`

- [x] Document Historical Replay versus Hypothetical Assumption Lab.
- [x] Document frozen venue probability, observed-score, cutoff, and
  no-psychological-adjustment assumptions.
- [x] Run a pre-Game-4 historical replay and verify it excludes Game 4 onward.
- [x] Run a current active-series replay if the refreshed local source remains
  active; otherwise document the observed completed-series status.
- [x] Visually verify the local Streamlit app.
- [x] Run `ruff check .`, `mypy src`, `pytest`, and `git diff --check`.
- [x] Audit generated artifacts and public performance claims.
- [ ] Commit, push, and open a Draft PR.
