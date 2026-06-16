# Daily Schedule Predictions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discover an NBA season schedule from immutable snapshots, build a
validated scheduled-matchup table, and atomically predict and register every
eligible game on one NBA calendar date.

**Architecture:** A source adapter preserves append-only `ScheduleLeagueV2`
snapshots. Pure transform and application modules own the scheduled-game
contract and daily eligibility rules, while separate storage adapters persist
validated Parquet and DuckDB tables. The CLI composes the layers and writes a
registry only after the complete daily batch succeeds.

**Tech Stack:** Python 3.9, pandas, `zoneinfo`, nba_api, Parquet/pyarrow,
DuckDB, argparse, pytest

---

## File Structure

- Create `src/nba_forecast/data/source_schedule.py`
  - Fetch and load immutable `ScheduleLeagueV2` snapshots and metadata.
- Create `src/nba_forecast/data/schedule_transform.py`
  - Authoritative scheduled-matchup schema, source transformation, and
    validation.
- Create `src/nba_forecast/data/schedule_storage.py`
  - Validated schedule Parquet and DuckDB persistence.
- Create `src/nba_forecast/application/daily_predictions.py`
  - Daily eligibility selection and atomic batch prediction/registration.
- Modify `src/nba_forecast/cli.py`
  - Compose fetch, build, and daily prediction commands.
- Create `tests/data/test_source_schedule.py`
  - Immutable snapshot and metadata tests.
- Create `tests/data/test_schedule_transform.py`
  - Schedule normalization, phase derivation, and validation tests.
- Create `tests/data/test_schedule_storage.py`
  - Parquet and DuckDB persistence tests.
- Create `tests/application/test_daily_predictions.py`
  - Eligibility, cutoff, idempotency, and batch atomicity tests.
- Create `tests/fixtures/schedule_league_v2_rows.csv`
  - Small source-shaped offline schedule fixture.
- Modify `tests/test_cli.py`
  - CLI composition tests.
- Modify `tests/test_project_config.py` and `.gitignore`
  - Keep local schedule artifacts out of Git.
- Create `docs/decisions/0006-schedule-source-and-daily-horizon.md`
  - Record source and once-daily operating decisions.
- Modify `README.md`, `docs/architecture.md`, `docs/data_dictionary.md`, and
  `docs/runbook.md`
  - Document verified schedule and daily prediction workflows.

## Task 1: Preserve Immutable Schedule Snapshots

**Files:**
- Create: `tests/data/test_source_schedule.py`
- Create: `src/nba_forecast/data/source_schedule.py`

- [x] **Step 1: Write failing immutable-snapshot tests**

Use an injected fetcher and fixed UTC timestamps:

```python
snapshot = fetch_schedule_snapshot(
    "2026-27",
    tmp_path,
    fetcher=lambda season: _source_rows(),
    fetched_at=datetime(2026, 6, 15, 12, 0, 0, 123456, tzinfo=timezone.utc),
)

assert snapshot.csv_path.name == "20260615T120000.123456Z.csv"
assert snapshot.metadata_path.name == "20260615T120000.123456Z.metadata.json"
assert load_schedule_snapshot(snapshot.csv_path).equals(_source_rows())
```

Assert metadata contains endpoint, season, exact UTC timestamp, row count, and
source columns. Add failures proving:

- a naive `fetched_at` is rejected
- a second fetch with the same timestamp refuses to overwrite either file
- a fetcher failure leaves the snapshot directory unchanged
- missing or invalid adjacent metadata is rejected by
  `load_schedule_snapshot_context`

- [x] **Step 2: Run source tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/data/test_source_schedule.py -v
```

Expected: collection fails because `nba_forecast.data.source_schedule` does not
exist.

- [x] **Step 3: Implement the minimal schedule source adapter**

Define:

```python
ScheduleFetcher = Callable[[str], pd.DataFrame]

@dataclass(frozen=True)
class ScheduleSnapshot:
    csv_path: Path
    metadata_path: Path

@dataclass(frozen=True)
class ScheduleSnapshotContext:
    season_key: str
    fetched_at_utc: datetime

def fetch_schedule_snapshot(
    season: str,
    cache_dir: Path,
    *,
    fetcher: Optional[ScheduleFetcher] = None,
    fetched_at: Optional[datetime] = None,
) -> ScheduleSnapshot: ...

def load_schedule_snapshot(csv_path: Path) -> pd.DataFrame: ...

def load_schedule_snapshot_context(csv_path: Path) -> ScheduleSnapshotContext: ...
```

Default fetching uses:

```python
scheduleleaguev2.ScheduleLeagueV2(season=season).season_games.get_data_frame()
```

Validate the season with the existing season-key contract. Normalize
`fetched_at` to UTC and use `%Y%m%dT%H%M%S.%fZ` for the filename. Refuse an
existing CSV or metadata path before fetching or writing. Write temporary CSV
and metadata files, then replace only the new target paths.

- [x] **Step 4: Run source tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/data/test_source_schedule.py -v
```

Expected: all source tests pass without network access.

- [x] **Step 5: Commit Task 1**

```bash
git add src/nba_forecast/data/source_schedule.py \
  tests/data/test_source_schedule.py
git commit -m "feat: preserve schedule snapshots"
```

## Task 2: Define and Transform the Canonical Schedule Contract

**Files:**
- Create: `tests/fixtures/schedule_league_v2_rows.csv`
- Create: `tests/data/test_schedule_transform.py`
- Create: `src/nba_forecast/data/schedule_transform.py`

- [x] **Step 1: Add a source-shaped fixture**

Create a fixture with:

- one valid `002` not-started regular-season game
- one valid `004` playoff game
- one unsupported phase row
- one conditional row with no tip-off and unknown teams
- one postponed row

Include the exact source fields consumed by the transform:

```text
gameId, gameStatus, gameStatusText, gameDateTimeUTC, gameDateEst,
ifNecessary, postponedStatus, homeTeam_teamId, homeTeam_teamTricode,
awayTeam_teamId, awayTeam_teamTricode
```

- [x] **Step 2: Write failing transform and validation tests**

Test the wished-for API:

```python
schedule = schedule_rows_to_matchups(
    rows,
    season_key="2026-27",
    schedule_snapshot_at_utc=datetime(
        2026, 6, 15, 12, tzinfo=timezone.utc
    ),
)

assert schedule["game_id"].tolist() == ["0022600001", "0042600001", ...]
assert schedule.loc[0, "season_type"] == "Regular Season"
assert schedule.loc[1, "season_type"] == "Playoffs"
assert schedule.loc[0, "season_id"] == "22026"
assert schedule.loc[1, "season_id"] == "42026"
assert schedule.loc[conditional_index, "has_confirmed_matchup"] is False
assert pd.isna(schedule.loc[conditional_index, "tipoff_at_utc"])
```

Prove unsupported phases are excluded and New York date conversion handles a
UTC tip-off after midnight. Test `validate_scheduled_matchups` accepts empty
and valid tables and rejects:

- missing or extra columns
- duplicate or blank game IDs
- inconsistent season context
- null, non-integer, or negative game statuses
- invalid non-null UTC timestamps
- mismatched New York calendar dates
- partially populated confirmed matchup identities
- identical confirmed teams
- invalid snapshot timestamps

- [x] **Step 3: Run transform tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/data/test_schedule_transform.py -v
```

Expected: collection fails because
`nba_forecast.data.schedule_transform` does not exist.

- [x] **Step 4: Implement the canonical schedule transform**

Define:

```python
SCHEDULED_MATCHUP_COLUMNS = (
    "game_id",
    "season_id",
    "season_type",
    "season_key",
    "schedule_snapshot_at_utc",
    "nba_game_date",
    "tipoff_at_utc",
    "game_status",
    "game_status_text",
    "is_postponed",
    "is_conditional",
    "has_confirmed_matchup",
    "home_team_id",
    "away_team_id",
    "home_team_abbreviation",
    "away_team_abbreviation",
)

def empty_scheduled_matchups() -> pd.DataFrame: ...

def schedule_rows_to_matchups(
    rows: pd.DataFrame,
    *,
    season_key: str,
    schedule_snapshot_at_utc: datetime,
) -> pd.DataFrame: ...

def validate_scheduled_matchups(schedule: pd.DataFrame) -> None: ...
```

Map `002` to `Regular Season`, `004` to `Playoffs`, and exclude other
prefixes. Derive `season_id` with `expected_season_id`. Normalize zero or
unknown team identities to nullable fields and derive
`has_confirmed_matchup`. Derive `is_conditional` from `ifNecessary` and
`is_postponed` from nonzero `postponedStatus`. Parse timestamps with
`pd.to_datetime(..., utc=True, errors="coerce")`, preserve nullable tip-offs,
and derive `nba_game_date` using `ZoneInfo("America/New_York")`.

- [x] **Step 5: Run transform tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/data/test_schedule_transform.py -v
```

Expected: all transform and validation tests pass.

- [x] **Step 6: Commit Task 2**

```bash
git add src/nba_forecast/data/schedule_transform.py \
  tests/data/test_schedule_transform.py \
  tests/fixtures/schedule_league_v2_rows.csv
git commit -m "feat: define scheduled matchup contract"
```

## Task 3: Persist the Canonical Schedule

**Files:**
- Create: `tests/data/test_schedule_storage.py`
- Create: `src/nba_forecast/data/schedule_storage.py`

- [x] **Step 1: Write failing persistence tests**

Test:

```python
parquet_path, database_path = write_scheduled_matchups(schedule, tmp_path)

assert parquet_path == tmp_path / "schedules" / "scheduled_matchups.parquet"
assert database_path == tmp_path / "schedules" / "schedule.duckdb"
pd.testing.assert_frame_equal(pd.read_parquet(parquet_path), schedule)
```

Query DuckDB and assert the `scheduled_matchups` table matches Parquet.
Attempt an invalid write after a valid write and prove the prior Parquet bytes
remain unchanged.

- [x] **Step 2: Run storage tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/data/test_schedule_storage.py -v
```

Expected: collection fails because `nba_forecast.data.schedule_storage` does
not exist.

- [x] **Step 3: Implement schedule persistence**

Define:

```python
def write_scheduled_matchups(
    schedule: pd.DataFrame,
    output_dir: Path,
) -> tuple[Path, Path]: ...
```

Validate before writing. Atomically replace
`schedules/scheduled_matchups.parquet`, then create or replace the DuckDB
`scheduled_matchups` table in `schedules/schedule.duckdb`.

- [x] **Step 4: Run storage tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/data/test_schedule_storage.py -v
```

Expected: all schedule persistence tests pass.

- [x] **Step 5: Commit Task 3**

```bash
git add src/nba_forecast/data/schedule_storage.py \
  tests/data/test_schedule_storage.py
git commit -m "feat: persist scheduled matchups"
```

## Task 4: Select Eligible Games and Run Atomic Daily Batches

**Files:**
- Create: `tests/application/test_daily_predictions.py`
- Create: `src/nba_forecast/application/daily_predictions.py`

- [x] **Step 1: Write failing eligibility tests**

Test:

```python
eligible = select_daily_matchups(
    schedule,
    prediction_date=date(2026, 10, 22),
    prediction_timestamp=datetime(2026, 10, 22, 12, tzinfo=timezone.utc),
)

assert eligible["game_id"].tolist() == ["0022600001", "0022600002"]
```

Prove the selector excludes:

- another NBA calendar date
- live and final games
- postponed and conditional games
- unconfirmed teams
- null tip-offs
- not-started rows whose tip-off is no longer in the future

Assert deterministic sorting by `tipoff_at_utc`, then `game_id`, and rejection
of a naive prediction timestamp. The selector accepts an empty canonical table
and returns an empty selection; the batch application handles the stronger
audit requirement below.

- [x] **Step 2: Run eligibility tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/application/test_daily_predictions.py -k select -v
```

Expected: collection fails because
`nba_forecast.application.daily_predictions` does not exist.

- [x] **Step 3: Implement eligibility selection**

Define:

```python
def select_daily_matchups(
    schedule: pd.DataFrame,
    *,
    prediction_date: date,
    prediction_timestamp: datetime,
) -> pd.DataFrame: ...
```

Validate the complete schedule first. Normalize the prediction timestamp to
UTC. Apply every approved eligibility rule and return a sorted copy.

- [x] **Step 4: Write failing daily batch tests**

Monkeypatch `predict_scheduled_matchup` with a deterministic test scorer and
test:

```python
output = run_daily_predictions(
    schedule,
    completed_games,
    registry,
    bundle,
    prediction_date=date(2026, 10, 22),
    prediction_timestamp=datetime(2026, 10, 22, 12, tzinfo=timezone.utc),
)

assert output.eligible_game_count == 2
assert output.excluded_game_count == len(schedule) - 2
assert len(output.predictions) == 2
assert len(output.registry) == 2
assert all(
    report["prediction_timestamp"] == "2026-10-22T12:00:00+00:00"
    for report in output.prediction_reports()
)
```

Assert:

- every scorer call receives `as_of_date == prediction_date`
- fixed-timestamp rerun is idempotent
- another timestamp creates new prediction events for still-eligible games
- a no-game date returns an empty report and unchanged registry
- a completely empty schedule table is rejected because it cannot identify a
  source snapshot for the audit report
- failure on the second game raises and the original input registry is
  unchanged
- schedule snapshot timestamps are included in the batch report

- [x] **Step 5: Run batch tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/application/test_daily_predictions.py -k run_daily -v
```

Expected: failure because `run_daily_predictions` is missing.

- [x] **Step 6: Implement the atomic batch application**

Define:

```python
@dataclass(frozen=True)
class DailyPredictionsOutput:
    prediction_date: date
    prediction_timestamp: datetime
    schedule_snapshot_at_utc: datetime
    total_schedule_rows: int
    eligible_game_count: int
    excluded_game_count: int
    predictions: tuple[MatchupPredictionOutput, ...]
    registry: pd.DataFrame

    def to_report(self) -> dict[str, object]: ...

def run_daily_predictions(
    schedule: pd.DataFrame,
    completed_games: pd.DataFrame,
    registry: pd.DataFrame,
    bundle: ModelBundle,
    *,
    prediction_date: date,
    prediction_timestamp: datetime,
) -> DailyPredictionsOutput: ...
```

Require the canonical schedule to be non-empty and contain exactly one
`schedule_snapshot_at_utc`; reject empty or mixed-snapshot batch inputs. Work
on a deep candidate registry copy, convert each eligible row to
`ScheduledMatchup`, call
`predict_scheduled_matchup` with the shared date and timestamp, then call
`register_prediction`. Return only after the entire loop succeeds.

- [x] **Step 7: Run application tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/application/test_daily_predictions.py -v
```

Expected: all daily application tests pass.

- [x] **Step 8: Commit Task 4**

```bash
git add src/nba_forecast/application/daily_predictions.py \
  tests/application/test_daily_predictions.py
git commit -m "feat: predict daily schedule batches"
```

## Task 5: Compose Fetch, Build, and Daily Prediction CLI Commands

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `src/nba_forecast/cli.py`

- [x] **Step 1: Write failing fetch and build CLI tests**

Call the private composition functions with an injected schedule fetcher and
fixed fetch timestamp, then use `main` for build:

```python
snapshot = _fetch_schedule(
    "2026-27",
    tmp_path / "raw",
    fetcher=lambda season: rows,
    fetched_at=fixed_timestamp,
)

exit_code = main([
    "build-schedule",
    "--raw-schedule-csv", str(snapshot.csv_path),
    "--output-dir", str(tmp_path),
])
```

Assert immutable snapshot paths, canonical Parquet, and schedule DuckDB exist
and contain supported regular-season and playoff rows.

- [x] **Step 2: Run fetch/build CLI tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -k "fetch_schedule or build_schedule" -v
```

Expected: import or parser failure because the commands are missing.

- [x] **Step 3: Implement fetch and build composition**

Add:

```text
fetch-schedule --season --cache-dir
build-schedule --raw-schedule-csv --output-dir
```

Private `_fetch_schedule(..., fetcher=None, fetched_at=None)` calls only
`fetch_schedule_snapshot`. `_build_schedule` loads snapshot rows and context,
calls `schedule_rows_to_matchups`, and persists via `write_scheduled_matchups`.

- [x] **Step 4: Write failing predict-daily CLI tests**

Call private `_predict_daily(..., prediction_timestamp=fixed_timestamp)` and
assert:

- all eligible games are registered with the same timestamp
- the registry Parquet and DuckDB are written only after success
- `daily_predictions_<prediction-date>.json` contains counts and reports
- rerunning the fixed timestamp remains idempotent
- a no-game date writes an empty report and leaves registry rows unchanged
- a monkeypatched batch failure leaves prior registry Parquet bytes unchanged

- [x] **Step 5: Run predict-daily CLI tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -k predict_daily -v
```

Expected: failure because `_predict_daily` and parser support are missing.

- [x] **Step 6: Implement predict-daily composition**

Add:

```text
predict-daily --schedule-parquet --games-parquet --model-bundle
  --prediction-date --registry-dir --output-dir
```

The private composition function loads all artifacts, captures or accepts one
UTC timestamp, calls `run_daily_predictions`, writes the complete candidate
registry, then writes the JSON report. Do not expose a timestamp override on
the public parser.

- [x] **Step 7: Run CLI tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -v
```

Expected: all CLI tests pass.

- [x] **Step 8: Commit Task 5**

```bash
git add src/nba_forecast/cli.py tests/test_cli.py
git commit -m "feat: add daily schedule commands"
```

## Task 6: Document and Smoke-Test the Manual Daily Workflow

**Files:**
- Create: `docs/decisions/0006-schedule-source-and-daily-horizon.md`
- Modify: `.gitignore`
- Modify: `tests/test_project_config.py`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/data_dictionary.md`
- Modify: `docs/runbook.md`

- [x] **Step 1: Write a failing repository-hygiene test**

Add:

```python
def test_local_schedule_artifacts_are_gitignored() -> None:
    gitignore = (Path(__file__).parents[1] / ".gitignore").read_text().splitlines()

    assert "data/schedules/" in gitignore
```

Run:

```bash
.venv/bin/pytest tests/test_project_config.py -v
```

Expected: the new test fails.

- [x] **Step 2: Ignore local schedule artifacts and verify GREEN**

Add `data/schedules/` to `.gitignore`, rerun the focused test, and expect it to
pass.

- [x] **Step 3: Add ADR 0006**

Document:

- why `ScheduleLeagueV2` is selected over `ScoreboardV2`
- why one daily NBA-calendar forecast horizon is selected
- why incomplete schedule evidence is preserved but not predicted
- why GitHub Actions and hosted persistence remain separate

- [x] **Step 4: Update public and operational documentation**

Add:

- verified manual schedule discovery and batch prediction to `README.md`
- source, transform, storage, and batch flow to `docs/architecture.md`
- the authoritative scheduled-matchup schema to `docs/data_dictionary.md`
- fetch, build, daily predict, inspect, no-game, and recovery commands to
  `docs/runbook.md`

State explicitly that the workflow is manual and local, not yet live or
scheduled.

- [x] **Step 5: Run an offline fixture smoke workflow**

Using `tests/fixtures/schedule_league_v2_rows.csv` and a local test model
bundle:

1. create a fixed-timestamp immutable schedule snapshot
2. build canonical schedule Parquet and DuckDB
3. run one fixed-timestamp daily prediction batch
4. rerun it and confirm idempotent registry row count
5. run a no-game date and confirm an empty report
6. inspect schedule and prediction DuckDB tables

Use `/tmp/nba-forecast-daily-smoke` so generated artifacts remain outside Git.
Record only verified behavior in documentation.

- [x] **Step 6: Run full verification**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/pytest -q
git diff --check
```

Expected: all checks pass.

- [x] **Step 7: Commit Task 6**

```bash
git add .gitignore README.md docs/architecture.md docs/data_dictionary.md \
  docs/runbook.md docs/decisions/0006-schedule-source-and-daily-horizon.md \
  tests/test_project_config.py
git commit -m "docs: add daily schedule workflow"
```

## Task 7: Publish the Focused Work Unit

**Files:**
- Modify: `docs/superpowers/plans/2026-06-15-daily-schedule-predictions.md`

- [x] **Step 1: Review scope and repository hygiene**

Confirm:

- the PR contains schedule snapshots, transform, storage, daily batch
  application, CLI, tests, and related docs only
- GitHub Actions cron, hosted persistence, automatic settlement, and
  Streamlit live views are absent
- `.omc/`, `AGENTS.md`, raw snapshots, schedule Parquet/DuckDB, registry
  artifacts, models, and generated reports are not staged
- public claims say manual daily workflow, not live automation

- [x] **Step 2: Re-run final verification**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/pytest -q
git diff --check
```

- [x] **Step 3: Push and open a Draft PR**

Use:

```text
Branch: feature/daily-schedule-predictions
Title: Add daily schedule prediction workflow
```

The PR description must summarize the schedule source, once-daily eligibility
contract, batch atomicity, verified smoke workflow, and the deferred hosted
persistence/automation boundary.
