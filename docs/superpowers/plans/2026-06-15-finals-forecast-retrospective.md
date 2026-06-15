# Finals Forecast Retrospective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Present the frozen pre-Game-5 forecast beside the verified Knicks
championship outcome without contaminating the forecast snapshot.

**Architecture:** Add a small application-layer retrospective builder that
validates an explicit outcome record against the existing
`SeriesReplayOutput`. The Streamlit hero consumes that builder while
Historical Replay remains unchanged. Document the result and pre-register the
season-agnostic playoff backtest as the next milestone.

**Tech Stack:** Python dataclasses, pandas, Streamlit, pytest AppTest

---

### Task 1: Forecast Retrospective Contract

**Files:**
- Create: `src/nba_forecast/application/forecast_retrospective.py`
- Create: `tests/application/test_forecast_retrospective.py`

- [x] Write failing tests for the verified Game 5 retrospective, Brier Score,
  and invalid team/date/final-score inputs.
- [x] Run:
  `.venv/bin/pytest -q tests/application/test_forecast_retrospective.py`
  and verify failure because the module does not exist.
- [x] Add immutable `ForecastOutcome` and `ForecastRetrospective` dataclasses.
- [x] Add `build_forecast_retrospective` with explicit validation and
  game-level Brier calculation.
- [x] Run the focused application tests and verify they pass.

### Task 2: Retrospective Dashboard

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_streamlit_app.py`

- [x] Replace hero AppTest expectations with forecast/outcome/interpretation
  assertions while preserving the snapshot-missing fallback test.
- [x] Run the focused dashboard tests and verify they fail for the existing
  featured-forecast hero.
- [x] Add the verified Game 5 outcome constant and build the retrospective
  only when the frozen replay is available.
- [x] Render forecast, actual result, series result, and single-game Brier
  interpretation without changing Historical Replay defaults.
- [x] Run the focused dashboard tests and verify they pass.

### Task 3: Documentation and Future Playoff Contract

**Files:**
- Modify: `README.md`
- Modify: `docs/experiments.md`
- Modify: `docs/runbook.md`
- Modify: `docs/superpowers/plans/2026-06-15-finals-forecast-retrospective.md`

- [x] Document the completed Finals forecast retrospective in `README.md`.
- [x] Append the season-agnostic playoff backtest hypothesis and evaluation
  contract to `docs/experiments.md`.
- [x] Add retrospective reproduction and interpretation notes to
  `docs/runbook.md`.
- [x] Mark completed plan tasks.

### Task 4: Verification and Publication

**Files:**
- Verify all changed files

- [x] Run `.venv/bin/ruff check .`.
- [x] Run `.venv/bin/mypy src`.
- [x] Run `.venv/bin/pytest -q`.
- [x] Run `git diff --check`.
- [x] Visually verify the local Streamlit dashboard.
- [x] Audit claims and confirm `.omc/` remains untracked.
- [ ] Commit, push, and open a Draft PR.
