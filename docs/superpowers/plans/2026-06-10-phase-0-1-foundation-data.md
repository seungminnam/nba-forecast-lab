# Phase 0/1 Foundation and Historical Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Completed and verified on 2026-06-10

**Goal:** Create a documented, tested Python repository that can turn cached NBA Stats team-game records into a validated canonical historical game table stored as Parquet and DuckDB.

**Architecture:** A source adapter fetches or reads source-shaped team-game rows and persists immutable raw CSV extracts. A pure transformation module pairs the home and away rows into one canonical game row, a validation module enforces data contracts, and a build command writes processed Parquet plus a DuckDB analytical table. Tests use committed fixtures and never require network access.

**Tech Stack:** Python 3.9+, pandas, PyArrow, DuckDB, nba_api, pytest, Ruff, mypy, GitHub Actions

---

## File Structure

```text
pyproject.toml                         package metadata, dependencies, tool config
.gitignore                             generated data, environments, caches
.github/workflows/ci.yml               lint, type, and unit-test checks
README.md                              recruiter-facing overview and quickstart
docs/architecture.md                   implemented Phase 0/1 data flow
docs/data_dictionary.md                raw and canonical game field contracts
docs/decisions/0001-data-storage.md    DuckDB and Parquet decision record
src/nba_forecast/__init__.py           package version
src/nba_forecast/config.py             repository data paths and seasons
src/nba_forecast/data/contracts.py     required columns and validation errors
src/nba_forecast/data/transform.py     team-game rows to canonical games
src/nba_forecast/data/validate.py      canonical table validation
src/nba_forecast/data/storage.py       Parquet and DuckDB persistence
src/nba_forecast/data/source_nba.py    nba_api fetch and raw-cache adapter
src/nba_forecast/cli.py                fetch and build command-line interface
tests/fixtures/team_game_rows.csv      small source-shaped deterministic fixture
tests/data/test_transform.py           pairing and normalization tests
tests/data/test_validate.py            data-contract failure tests
tests/data/test_storage.py             Parquet and DuckDB round-trip tests
tests/data/test_source_nba.py          raw-cache behavior tests
```

### Task 1: Repository Foundation and Documentation Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.github/workflows/ci.yml`
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/data_dictionary.md`
- Create: `docs/decisions/0001-data-storage.md`
- Create: `src/nba_forecast/__init__.py`
- Create: `src/nba_forecast/config.py`
- Create: `src/nba_forecast/data/__init__.py`
- Create: `tests/__init__.py`

- [x] **Step 1: Define package and development tooling**

Create a `pyproject.toml` using a `src` layout, Python `>=3.9`, runtime
dependencies `pandas`, `pyarrow`, `duckdb`, and `nba_api`, and a `dev`
dependency group containing `pytest`, `ruff`, and `mypy`.

- [x] **Step 2: Define generated-file exclusions**

Ignore virtual environments, Python caches, `.superpowers/`, downloaded raw
data, processed data, DuckDB files, and generated artifacts while preserving
directory-level `.gitkeep` files if needed.

- [x] **Step 3: Write the initial documentation surfaces**

Document the product goal, MVP scope, current Phase 0/1 status, architecture,
quickstart commands, source lineage, canonical fields, and the DuckDB/Parquet
decision. Do not include unmeasured model results.

- [x] **Step 4: Add continuous integration**

Configure GitHub Actions on pushes and pull requests to run:

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest
```

- [x] **Step 5: Verify package configuration**

Run:

```bash
python -m compileall src
```

Expected: package files compile without errors.

- [x] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore .github README.md docs src tests
git commit -m "chore: initialize documented python project"
```

### Task 2: Canonical Game Transformation

**Files:**
- Create: `src/nba_forecast/data/contracts.py`
- Create: `src/nba_forecast/data/transform.py`
- Create: `tests/fixtures/team_game_rows.csv`
- Create: `tests/data/test_transform.py`
- Modify: `docs/data_dictionary.md`

- [x] **Step 1: Write fixture rows and failing transformation tests**

The fixture contains two completed games with exactly two source rows per game:
one `MATCHUP` containing `vs.` and one containing `@`. Tests assert:

```python
games = team_rows_to_games(team_rows)

assert games["game_id"].is_unique
assert games.loc[0, "home_team_id"] == 1
assert games.loc[0, "away_team_id"] == 2
assert games.loc[0, "home_win"] == 1
assert games.loc[0, "home_points"] == 110
assert games.loc[0, "away_points"] == 101
```

Also assert that a game with a missing away row raises
`CanonicalGameError`.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/data/test_transform.py -v
```

Expected: FAIL because transformation modules do not exist.

- [x] **Step 3: Implement source contracts and transformation**

Define required source columns and implement:

```python
def team_rows_to_games(team_rows: pd.DataFrame) -> pd.DataFrame:
    """Pair NBA Stats team-game rows into one chronologically sorted game row."""
```

The implementation normalizes column names, determines home/away from
`MATCHUP`, requires exactly two rows per game, verifies opposite teams, derives
`home_win`, and returns canonical columns in a stable order.

- [x] **Step 4: Run focused tests**

Run:

```bash
pytest tests/data/test_transform.py -v
ruff check src/nba_forecast/data tests/data/test_transform.py
```

Expected: all focused checks pass.

- [x] **Step 5: Update data dictionary**

Document every required source column and canonical output column, including
type, meaning, source, and point-in-time availability.

- [x] **Step 6: Commit**

```bash
git add src/nba_forecast/data tests/fixtures tests/data/test_transform.py docs/data_dictionary.md
git commit -m "feat: build canonical games from team rows"
```

### Task 3: Canonical Data Validation

**Files:**
- Create: `src/nba_forecast/data/validate.py`
- Create: `tests/data/test_validate.py`
- Modify: `docs/data_dictionary.md`

- [x] **Step 1: Write failing validation tests**

Tests cover duplicate `game_id`, home and away team equality, missing scores,
invalid `home_win`, and a valid canonical table.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/data/test_validate.py -v
```

Expected: FAIL because `validate_games` does not exist.

- [x] **Step 3: Implement validation**

Implement:

```python
def validate_games(games: pd.DataFrame) -> None:
    """Raise CanonicalGameError when the canonical completed-game table is invalid."""
```

The error message lists every failed rule so pipeline failures are actionable.

- [x] **Step 4: Run focused tests**

Run:

```bash
pytest tests/data/test_validate.py tests/data/test_transform.py -v
```

Expected: all tests pass.

- [x] **Step 5: Document validation rules and commit**

```bash
git add src/nba_forecast/data/validate.py tests/data/test_validate.py docs/data_dictionary.md
git commit -m "feat: validate canonical game data"
```

### Task 4: Parquet and DuckDB Persistence

**Files:**
- Create: `src/nba_forecast/data/storage.py`
- Create: `tests/data/test_storage.py`
- Modify: `docs/architecture.md`
- Modify: `docs/decisions/0001-data-storage.md`

- [x] **Step 1: Write failing round-trip tests**

Using `tmp_path`, assert `write_processed_games` creates:

```text
processed/games.parquet
nba_forecast.duckdb
```

Query DuckDB and assert the `games` table matches the canonical fixture row
count and IDs.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/data/test_storage.py -v
```

Expected: FAIL because persistence code does not exist.

- [x] **Step 3: Implement atomic persistence**

Implement a function that validates games, writes Parquet, and creates or
replaces the DuckDB `games` table. Parent directories are created explicitly.

- [x] **Step 4: Run focused tests**

Run:

```bash
pytest tests/data/test_storage.py tests/data/test_validate.py -v
```

Expected: all tests pass.

- [x] **Step 5: Update architecture and decision record, then commit**

```bash
git add src/nba_forecast/data/storage.py tests/data/test_storage.py docs/architecture.md docs/decisions/0001-data-storage.md
git commit -m "feat: persist canonical games to parquet and duckdb"
```

### Task 5: NBA Stats Source Adapter and Raw Cache

**Files:**
- Create: `src/nba_forecast/data/source_nba.py`
- Create: `tests/data/test_source_nba.py`
- Modify: `docs/architecture.md`
- Modify: `docs/runbook.md`

- [x] **Step 1: Write failing source-adapter tests**

Inject a fake fetcher and assert:

- A missing raw CSV invokes the fetcher once and writes the response.
- An existing raw CSV is returned without invoking the fetcher.
- `force=True` invokes the fetcher and replaces the cache.
- Season and season-type values produce stable cache paths.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/data/test_source_nba.py -v
```

Expected: FAIL because the source adapter does not exist.

- [x] **Step 3: Implement cached source adapter**

Implement an injectable cache-first adapter around
`nba_api.stats.endpoints.LeagueGameFinder`. Network requests occur only on a
cache miss or explicit force refresh. The adapter records source metadata beside
each raw CSV.

- [x] **Step 4: Run focused tests**

Run:

```bash
pytest tests/data/test_source_nba.py -v
```

Expected: all tests pass without network access.

- [x] **Step 5: Document source operation and commit**

```bash
git add src/nba_forecast/data/source_nba.py tests/data/test_source_nba.py docs/architecture.md docs/runbook.md
git commit -m "feat: add cache-first nba stats source adapter"
```

### Task 6: Reproducible Data CLI

**Files:**
- Create: `src/nba_forecast/cli.py`
- Create: `tests/test_cli.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/runbook.md`

- [x] **Step 1: Write failing CLI tests**

Test the build command against `tests/fixtures/team_game_rows.csv` and a
temporary output directory. Assert successful exit and created Parquet and
DuckDB outputs.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_cli.py -v
```

Expected: FAIL because CLI entry points do not exist.

- [x] **Step 3: Implement commands**

Expose:

```bash
nba-forecast build-games --raw-csv PATH --output-dir PATH
nba-forecast fetch-games --season 2025-26 --season-type "Regular Season"
```

The build command performs transform, validate, and persistence. The fetch
command only populates raw source cache.

- [x] **Step 4: Run end-to-end fixture build**

Run:

```bash
nba-forecast build-games \
  --raw-csv tests/fixtures/team_game_rows.csv \
  --output-dir /tmp/nba-forecast-smoke
```

Expected: command reports the number of games written and both storage outputs.

- [x] **Step 5: Run full quality checks**

Run:

```bash
ruff check .
mypy src
pytest
```

Expected: all checks pass.

- [x] **Step 6: Update README and runbook, then commit**

```bash
git add src/nba_forecast/cli.py tests/test_cli.py pyproject.toml README.md docs/runbook.md
git commit -m "feat: add reproducible historical game build command"
```

### Task 7: Phase 0/1 Verification and Documentation Audit

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/data_dictionary.md`
- Modify: `docs/runbook.md`

- [x] **Step 1: Verify clean installation**

Create a fresh virtual environment and run:

```bash
python -m pip install -e ".[dev]"
```

Expected: installation succeeds.

- [x] **Step 2: Verify offline fixture workflow**

Run the documented fixture build command from the README and query the resulting
DuckDB table.

Expected: exactly two fixture games with unique IDs.

- [x] **Step 3: Verify quality suite**

Run:

```bash
ruff check .
mypy src
pytest
```

Expected: all checks pass.

- [x] **Step 4: Audit documentation**

Confirm every implemented command, canonical field, validation rule, data path,
and known limitation is represented in README or linked documentation. Remove
claims about behavior that has not been verified.

- [x] **Step 5: Commit final Phase 0/1 documentation**

```bash
git add README.md docs
git commit -m "docs: finalize phase one data pipeline guide"
```
