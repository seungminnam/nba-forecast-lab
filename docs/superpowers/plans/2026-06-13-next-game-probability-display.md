# Next-Game Probability Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the actual next playoff game's model probabilities and
model-implied fair odds through Historical Replay, JSON, and Streamlit.

**Architecture:** Add a small odds-formatting module and a `NextGameForecast`
application contract. Historical Replay selects one of its existing two venue
predictions according to the reconstructed next home team, avoiding additional
model inference.

**Tech Stack:** Python dataclasses, pandas, Streamlit, pytest

---

### Task 1: Fair Odds Conversion

**Files:**
- Create: `src/nba_forecast/application/fair_odds.py`
- Create: `tests/application/test_fair_odds.py`

- [x] Write failing tests for decimal odds, positive and negative American
  odds, even probability, and zero/one rejection.
- [x] Run the focused test and verify failure because the module is absent.
- [x] Implement immutable `FairOdds` and `fair_odds_from_probability`.
- [x] Run the focused odds tests.

### Task 2: Next-Game Forecast Contract

**Files:**
- Modify: `src/nba_forecast/application/series_replay.py`
- Modify: `tests/application/test_series_replay.py`

- [x] Write failing tests proving Team A-home and Team B-home next games select
  the correct existing prediction.
- [x] Add immutable `NextGameForecast` to `SeriesReplayOutput`.
- [x] Build fair odds for both teams without a third model inference.
- [x] Return no next-game forecast for completed series.
- [x] Add explicit non-market and non-betting flags to the JSON report.
- [x] Run focused replay tests.

### Task 3: Streamlit Product Surface

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_streamlit_app.py`

- [x] Write failing AppTest assertions for next-game and fair-odds labels.
- [x] Replace generic venue probability cards with an actual next-game
  forecast section.
- [x] Display both team probabilities, decimal odds, American odds, and the
  non-betting disclaimer.
- [x] Preserve series probability cards and charts.
- [x] Run Streamlit AppTest.

### Task 4: Documentation and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/data_dictionary.md`
- Modify: `docs/model_card.md`
- Modify: `docs/runbook.md`
- Modify: `docs/superpowers/plans/2026-06-13-next-game-probability-display.md`

- [x] Document next-game forecast versus remaining-series forecast.
- [x] Document fair-odds formulas and non-market/non-betting boundaries.
- [x] Visually verify the pre-Game-5 Historical Replay UI.
- [x] Run `ruff check .`, `mypy src`, `pytest`, and `git diff --check`.
- [x] Audit generated artifacts and public claims.
- [ ] Commit, push, and open a Draft PR.
