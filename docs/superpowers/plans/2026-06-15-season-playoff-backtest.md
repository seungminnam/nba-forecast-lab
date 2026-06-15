# Season-Agnostic Playoff Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluate one frozen model across every completed playoff game in an
arbitrary season under the existing point-in-time feature contract.

**Architecture:** Add a focused application service that converts each
completed playoff game into a scheduled matchup, invokes the existing
leakage-safe predictor at that game's cutoff, then attaches outcomes and
calculates aggregate metrics. Add a CLI report workflow and document the first
completed 2025-26 playoff run.

**Tech Stack:** Python dataclasses, pandas, pytest, existing matchup prediction
and probability metrics services

---

### Task 1: Backtest Application Service

**Files:**
- Create: `src/nba_forecast/application/playoff_backtest.py`
- Create: `tests/application/test_playoff_backtest.py`

- [x] Write failing tests for chronological predictions, outcome attachment,
  aggregate metrics, leakage mutation resistance, and invalid inputs.
- [x] Run focused tests and verify failure because the module is missing.
- [x] Implement `PlayoffBacktestInput`, `PlayoffBacktestOutput`, and
  `run_playoff_backtest`.
- [x] Run focused tests and verify they pass.

### Task 2: CLI Reports

**Files:**
- Modify: `src/nba_forecast/cli.py`
- Modify: `tests/test_cli.py`

- [x] Write a failing CLI test for `backtest-playoffs`.
- [x] Add parser arguments and report writing.
- [x] Run focused CLI tests and verify they pass.

### Task 3: Completed Data and Measured Report

**Files:**
- Refresh local raw and processed data
- Generate local report artifacts
- Modify: `README.md`
- Modify: `docs/experiments.md`
- Modify: `docs/runbook.md`

- [x] Refresh completed 2025-26 playoff data without replacing the frozen
  deployment snapshot.
- [x] Run the backtest command on the complete season.
- [x] Document dataset coverage, metrics, interpretation, and limitations.

### Task 4: Verification and Publication

- [x] Run `.venv/bin/ruff check .`.
- [x] Run `.venv/bin/mypy src`.
- [x] Run `.venv/bin/pytest -q`.
- [x] Run `git diff --check`.
- [x] Confirm generated artifacts and `.omc/` remain untracked.
- [x] Commit, push, and open a Draft PR.
