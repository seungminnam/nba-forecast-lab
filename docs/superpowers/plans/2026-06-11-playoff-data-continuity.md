# Playoff Data Continuity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend canonical games and pre-game features through the playoffs
while preserving source identity and continuous team state.

**Architecture:** Raw CSV files remain source-shaped and receive season context
from adjacent metadata sidecars during CLI builds. Canonical rows preserve
`season_id`, `season_type`, and `season_key`; rolling state and Elo use
`season_key`, while model features and the frozen bundle remain unchanged.

**Tech Stack:** Python, pandas, DuckDB, nba_api, argparse, pytest

---

### Task 1: Contextual Canonical Game Contract

**Files:**
- Modify: `src/nba_forecast/data/contracts.py`
- Modify: `src/nba_forecast/data/transform.py`
- Modify: `src/nba_forecast/data/validate.py`
- Modify: `tests/data/test_transform.py`
- Modify: `tests/data/test_validate.py`
- Modify: `tests/data/test_storage.py`

- [x] Write failing tests proving explicit regular-season and playoff context
  preserves source `season_id`, `season_type`, and shared `season_key`.
- [x] Run focused tests and confirm failure because context fields are absent.
- [x] Require `season_type` and `season_key` in `team_rows_to_games`, add the
  fields to the canonical contract, and reject inconsistent source context.
- [x] Add canonical validation for supported season types, non-empty season
  keys, and source-ID-to-context consistency.
- [x] Run focused transformation, validation, and storage tests.

### Task 2: Metadata-Aware Multi-File Build

**Files:**
- Modify: `src/nba_forecast/data/source_nba.py`
- Modify: `src/nba_forecast/cli.py`
- Modify: `tests/data/test_source_nba.py`
- Modify: `tests/test_cli.py`
- Add fixture sidecars beside `tests/fixtures/*.csv`

- [x] Write failing tests for loading raw-cache request context and rejecting
  missing metadata.
- [x] Implement a typed metadata loader that validates `season` and
  `season_type`.
- [x] Add a CLI test proving regular-season and playoff files combine
  with a shared `season_key`.
- [x] Transform each raw file with its metadata context before concatenation
  and canonical validation.
- [x] Run source and CLI tests.

### Task 3: Continuous Rolling State and Elo

**Files:**
- Modify: `src/nba_forecast/features/team_state.py`
- Modify: `src/nba_forecast/features/elo.py`
- Modify: `src/nba_forecast/features/game_features.py`
- Modify: `tests/features/test_team_state.py`
- Modify: `tests/features/test_elo.py`
- Modify: `tests/features/test_game_features.py`

- [x] Write failing boundary tests proving first-playoff-game rolling state
  includes regular-season history and a true new season resets it.
- [x] Change rolling groups from `season_id` to `season_key`.
- [x] Write failing Elo tests proving playoffs do not trigger offseason
  reversion and a true new season does.
- [x] Change Elo reversion boundaries from `season_id` to `season_key`.
- [x] Preserve source identifiers in feature rows and run focused tests.

### Task 4: Scheduled Playoff Matchup Compatibility

**Files:**
- Modify: `src/nba_forecast/features/matchup_features.py`
- Modify: `src/nba_forecast/application/matchup_prediction.py`
- Modify: `src/nba_forecast/cli.py`
- Modify: `tests/features/test_matchup_features.py`
- Modify: `tests/application/test_matchup_prediction.py`
- Modify: `tests/test_cli.py`

- [x] Write a failing historical-parity test at a
  regular-season-to-playoffs boundary.
- [x] Add `season_type` and `season_key` to `ScheduledMatchup`, its ephemeral
  canonical row, CLI arguments, and auditable report.
- [x] Prove future playoff-result mutation cannot change an earlier scheduled
  snapshot.
- [x] Run focused matchup workflow tests.

### Task 5: Documentation and Offline Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/data_dictionary.md`
- Modify: `docs/leakage_prevention.md`
- Modify: `docs/model_card.md`
- Modify: `docs/runbook.md`
- Modify: `docs/source_report.md`

- [x] Document the expanded canonical contract, continuity behavior, rebuild
  command, measured limitations, and unchanged model-performance claim.
- [x] Rebuild the offline fixture pipeline.
- [x] Run `ruff check .`, `mypy src`, `pytest`, and `git diff --check`.

### Task 6: Live 2025-26 Playoff Refresh and Publication

**Files:**
- Modify: `docs/source_report.md`
- Modify: `README.md`
- Modify: `docs/runbook.md`
- Modify: `docs/superpowers/plans/2026-06-11-playoff-data-continuity.md`

- [x] Fetch or reuse the 2025-26 `Playoffs` raw cache.
- [x] Rebuild processed games and features from all required regular-season
  caches plus the 2025-26 playoff cache.
- [x] Verify row counts, date range, season types, unique game IDs, and the
  first-playoff-game continuity values.
- [x] Run one frozen-bundle scheduled matchup smoke prediction if the required
  live schedule context is available; otherwise document the exact blocker.
- [x] Append measured live-source evidence without changing historical
  regular-season model metrics.
- [x] Run full verification.
- [ ] Commit, push, and open a Draft PR.
