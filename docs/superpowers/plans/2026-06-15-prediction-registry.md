# Prediction Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-first immutable registry that stores forward predictions,
settles completed outcomes, and reports cumulative operating performance.

**Architecture:** Pure application services own prediction identity,
idempotency, immutability, settlement, and reporting. A separate data adapter
persists the validated registry to Parquet and synchronizes a replaceable
DuckDB query table. The CLI composes these layers without reimplementing domain
rules.

**Tech Stack:** Python 3.9, pandas, Parquet/pyarrow, DuckDB, argparse, pytest

---

## File Structure

- Create `src/nba_forecast/application/prediction_registry.py`
  - Authoritative registry schema, validation, registration, settlement, and
    performance-report domain logic.
- Create `src/nba_forecast/data/prediction_registry_storage.py`
  - Missing-file initialization, Parquet reads, atomic Parquet writes, and
    DuckDB synchronization.
- Modify `src/nba_forecast/cli.py`
  - Optional registration from `predict-matchup` plus `settle-predictions` and
    `report-predictions` commands.
- Create `tests/application/test_prediction_registry.py`
  - Pure domain behavior and immutability regression tests.
- Create `tests/data/test_prediction_registry_storage.py`
  - Local persistence round-trip and DuckDB synchronization tests.
- Modify `tests/test_cli.py`
  - End-to-end CLI composition tests.
- Modify `tests/test_project_config.py`
  - Prove generated local registry artifacts remain excluded from Git.
- Modify `.gitignore`
  - Exclude the default local `data/registry/` operating directory.
- Create `docs/decisions/0005-immutable-prediction-registry.md`
  - Record why the registry is local-first, append-oriented, and immutable.
- Modify `README.md`, `docs/architecture.md`, `docs/data_dictionary.md`, and
  `docs/runbook.md`
  - Document verified capability, schema, flow, commands, and limitations.

## Task 1: Define and Validate Registry Records

**Files:**
- Create: `tests/application/test_prediction_registry.py`
- Create: `src/nba_forecast/application/prediction_registry.py`

- [x] **Step 1: Write failing tests for deterministic record creation and validation**

Create a small `MatchupPredictionOutput` fixture with a fixed UTC timestamp and
assert:

```python
record = prediction_to_record(_prediction())

assert record["game_id"] == "scheduled-1"
assert record["prediction_timestamp"] == pd.Timestamp(
    "2026-10-20T12:00:00Z"
)
assert record["features_json"] == '{"elo_diff":12.5,"rest_days_diff":1.0}'
assert record["final_outcome"] is pd.NA
assert len(record["prediction_id"]) == 64
assert len(record["payload_fingerprint"]) == 64
```

Add table-validation cases for:

```python
validate_prediction_registry(empty_prediction_registry())
validate_prediction_registry(pd.DataFrame([record]))
```

and expected failures for duplicate `prediction_id`, probability values outside
`[0, 1]`, probabilities that do not sum to one, naive timestamps, malformed
feature JSON, and partially populated settlement fields.

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/application/test_prediction_registry.py -v
```

Expected: collection fails because
`nba_forecast.application.prediction_registry` does not exist.

- [x] **Step 3: Implement the minimal schema and record conversion**

Define:

```python
REGISTRY_COLUMNS = (
    "prediction_id",
    "payload_fingerprint",
    "prediction_timestamp",
    "as_of_date",
    "game_id",
    "game_date",
    "season_id",
    "season_type",
    "season_key",
    "home_team_id",
    "away_team_id",
    "home_team_abbreviation",
    "away_team_abbreviation",
    "model_version",
    "feature_version",
    "home_win_probability",
    "away_win_probability",
    "features_json",
    "final_outcome",
    "settled_at",
    "brier_contribution",
    "is_correct",
)

IMMUTABLE_REGISTRY_COLUMNS = REGISTRY_COLUMNS[:18]
SETTLEMENT_COLUMNS = REGISTRY_COLUMNS[18:]
```

Implement:

```python
def empty_prediction_registry() -> pd.DataFrame: ...

def prediction_to_record(output: MatchupPredictionOutput) -> dict[str, object]: ...

def validate_prediction_registry(registry: pd.DataFrame) -> None: ...
```

Use canonical `json.dumps(..., sort_keys=True, separators=(",", ":"))` and
SHA-256 hashes. Normalize timezone-aware prediction timestamps to UTC. Derive
`prediction_id` from canonical JSON containing only `game_id`,
`model_version`, and normalized `prediction_timestamp`. Derive
`payload_fingerprint` from all immutable values.

Validation must reject:

- missing or extra columns
- duplicate prediction IDs
- null immutable values
- invalid or non-UTC-aware prediction timestamps
- invalid probabilities or non-complementary probabilities
- invalid canonical feature JSON
- settlement fields that are only partially populated
- settled outcomes outside `{0, 1}`

- [x] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/application/test_prediction_registry.py -v
```

Expected: record-conversion and validation tests pass.

- [x] **Step 5: Commit Task 1**

```bash
git add src/nba_forecast/application/prediction_registry.py \
  tests/application/test_prediction_registry.py
git commit -m "feat: define prediction registry contract"
```

## Task 2: Add Idempotent Registration and Immutable Settlement

**Files:**
- Modify: `tests/application/test_prediction_registry.py`
- Modify: `src/nba_forecast/application/prediction_registry.py`

- [x] **Step 1: Write failing registration tests**

Test the wished-for API:

```python
result = register_prediction(empty_prediction_registry(), _prediction())
assert result.status == "registered"
assert len(result.registry) == 1

repeated = register_prediction(result.registry, _prediction())
assert repeated.status == "already_registered"
assert len(repeated.registry) == 1
```

Also assert that:

- a matching `prediction_id` with a changed probability raises `ValueError`
- another timestamp is preserved as another row
- another model version is preserved as another row

- [x] **Step 2: Run the registration tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/application/test_prediction_registry.py -k register -v
```

Expected: failure because `register_prediction` is missing.

- [x] **Step 3: Implement idempotent registration**

Add:

```python
@dataclass(frozen=True)
class RegistrationResult:
    registry: pd.DataFrame
    status: str
    prediction_id: str


def register_prediction(
    registry: pd.DataFrame,
    prediction: MatchupPredictionOutput,
) -> RegistrationResult: ...
```

Validate the input registry first. Return it unchanged for an identical
fingerprint. Raise on an existing identity with a different fingerprint.
Otherwise append exactly one validated record and sort deterministically by
`prediction_timestamp`, `game_id`, and `prediction_id`.

- [x] **Step 4: Write failing settlement and immutability tests**

Register two predictions, provide one matching completed canonical game, and
assert:

```python
immutable_before = registry.loc[:, IMMUTABLE_REGISTRY_COLUMNS].copy(deep=True)
result = settle_predictions(
    registry,
    completed_games,
    settled_at=datetime(2026, 10, 22, tzinfo=timezone.utc),
)

pd.testing.assert_frame_equal(
    immutable_before,
    result.registry.loc[:, IMMUTABLE_REGISTRY_COLUMNS],
)
assert result.settled_count == 1
assert result.unmatched_count == 1
assert result.registry.loc[0, "brier_contribution"] == pytest.approx(
    (0.60 - 1) ** 2
)
```

Add cases proving:

- repeated settlement with the same outcome is unchanged
- team identity mismatch raises
- a conflicting existing outcome raises
- unmatched predictions remain entirely unsettled

- [x] **Step 5: Run settlement tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/application/test_prediction_registry.py -k settle -v
```

Expected: failure because `settle_predictions` is missing.

- [x] **Step 6: Implement minimal settlement**

Add:

```python
@dataclass(frozen=True)
class SettlementResult:
    registry: pd.DataFrame
    settled_count: int
    already_settled_count: int
    unmatched_count: int


def settle_predictions(
    registry: pd.DataFrame,
    completed_games: pd.DataFrame,
    *,
    settled_at: Optional[datetime] = None,
) -> SettlementResult: ...
```

Call `validate_games(completed_games)` before matching by `game_id`. Verify both
team IDs for every match. Populate all settlement fields together and never
assign to `IMMUTABLE_REGISTRY_COLUMNS`. Validate the result before returning.

- [x] **Step 7: Run domain tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/application/test_prediction_registry.py -v
```

Expected: all registry domain tests pass.

- [x] **Step 8: Commit Task 2**

```bash
git add src/nba_forecast/application/prediction_registry.py \
  tests/application/test_prediction_registry.py
git commit -m "feat: register and settle predictions"
```

## Task 3: Add Registry Performance Reporting

**Files:**
- Modify: `tests/application/test_prediction_registry.py`
- Modify: `src/nba_forecast/application/prediction_registry.py`

- [x] **Step 1: Write failing report tests**

Test empty, unsettled-only, settled single-class, and settled multi-model
registries:

```python
report = build_prediction_registry_report(registry)

assert report.summary.to_dict("records") == [
    {"total_predictions": 3, "settled_predictions": 2, "unsettled_predictions": 1}
]
assert report.metrics["scope"].tolist() == [
    "all_models",
    "model:model-a",
    "model:model-b",
]
```

Assert that each metrics row includes `predictions`, `brier_score`,
`log_loss`, `expected_calibration_error`, `roc_auc`, and `accuracy`. For an
empty or unsettled-only registry, metrics is an empty table with the stable
schema. For a settled single-class group, `roc_auc` is `NaN`.

- [x] **Step 2: Run report tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/application/test_prediction_registry.py -k report -v
```

Expected: failure because `build_prediction_registry_report` is missing.

- [x] **Step 3: Implement report generation**

Add:

```python
@dataclass(frozen=True)
class PredictionRegistryReport:
    summary: pd.DataFrame
    metrics: pd.DataFrame


def build_prediction_registry_report(
    registry: pd.DataFrame,
) -> PredictionRegistryReport: ...
```

Validate the registry, filter settled rows, and reuse `probability_metrics`.
Create one aggregate row and deterministic model-version rows. Do not infer
performance from unsettled predictions.

- [x] **Step 4: Run domain tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/application/test_prediction_registry.py -v
```

Expected: all domain tests pass.

- [x] **Step 5: Commit Task 3**

```bash
git add src/nba_forecast/application/prediction_registry.py \
  tests/application/test_prediction_registry.py
git commit -m "feat: report prediction registry performance"
```

## Task 4: Persist the Registry to Parquet and DuckDB

**Files:**
- Create: `tests/data/test_prediction_registry_storage.py`
- Create: `src/nba_forecast/data/prediction_registry_storage.py`

- [x] **Step 1: Write failing storage tests**

Test:

```python
registry = load_prediction_registry(tmp_path)
assert registry.empty
assert registry.columns.tolist() == list(REGISTRY_COLUMNS)

parquet_path, database_path = write_prediction_registry(populated, tmp_path)
round_trip = load_prediction_registry(tmp_path)
pd.testing.assert_frame_equal(round_trip, populated)
```

Query DuckDB and assert its `predictions` rows match the Parquet rows. Also
assert invalid data fails before either artifact changes and that an existing
Parquet file remains intact after the rejected write.

- [x] **Step 2: Run storage tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/data/test_prediction_registry_storage.py -v
```

Expected: collection fails because
`nba_forecast.data.prediction_registry_storage` does not exist.

- [x] **Step 3: Implement storage adapter**

Add:

```python
def load_prediction_registry(registry_dir: Path) -> pd.DataFrame: ...

def write_prediction_registry(
    registry: pd.DataFrame,
    registry_dir: Path,
) -> tuple[Path, Path]: ...
```

Use:

```text
<registry_dir>/predictions.parquet
<registry_dir>/prediction_registry.duckdb
```

Validate before writing, write `predictions.parquet.tmp`, atomically replace
the Parquet artifact, then `CREATE OR REPLACE TABLE predictions` in DuckDB.
Validate the loaded Parquet table before returning it.

- [x] **Step 4: Run storage tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/data/test_prediction_registry_storage.py -v
```

Expected: all storage tests pass.

- [x] **Step 5: Commit Task 4**

```bash
git add src/nba_forecast/data/prediction_registry_storage.py \
  tests/data/test_prediction_registry_storage.py
git commit -m "feat: persist prediction registry"
```

## Task 5: Compose Registry CLI Workflows

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `src/nba_forecast/cli.py`

- [x] **Step 1: Write failing CLI registration test**

Extend the existing `predict-matchup` command test with:

```text
--registry-dir <tmp_path>/registry
```

Call the internal `_predict_matchup` composition function twice with the same
fixed `prediction_timestamp` and assert:

- `matchup_prediction.json` still exists
- `registry/predictions.parquet` contains one row
- `registry/prediction_registry.duckdb` contains one row
- output says the prediction was registered on the first run and already
  registered on the second

Pass a fixed prediction timestamp into the CLI workflow through a small
internal `_predict_matchup(..., prediction_timestamp=None)` parameter used by
the test; do not expose a user-facing timestamp override. Two normal CLI
invocations occur at different timestamps and therefore correctly represent
two distinct prediction events.

- [x] **Step 2: Run CLI registration test and verify RED**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -k "predict_matchup and registry" -v
```

Expected: parser failure because `--registry-dir` is unsupported.

- [x] **Step 3: Implement optional registration composition**

Add optional `--registry-dir` to `predict-matchup`. When present:

1. load the registry
2. call `register_prediction`
3. persist the returned registry
4. print the registration status

Keep the existing standalone JSON report behavior unchanged when the flag is
absent.

- [x] **Step 4: Write failing settlement and reporting CLI tests**

Add tests invoking:

```bash
nba-forecast settle-predictions \
  --registry-dir <registry> \
  --games-parquet <completed-games>

nba-forecast report-predictions \
  --registry-dir <registry> \
  --output-dir <tmp-path>
```

Assert settlement counts, persisted outcomes, and these report files:

```text
artifacts/reports/prediction_registry_summary.csv
artifacts/reports/prediction_registry_metrics.csv
```

- [x] **Step 5: Run new CLI tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -k "settle_predictions or report_predictions" -v
```

Expected: parser failure because both commands are unsupported.

- [x] **Step 6: Implement settlement and reporting CLI composition**

Add parser entries and private command functions that call only the shared
application and storage APIs. Do not duplicate matching, metric, or validation
logic in `cli.py`.

- [x] **Step 7: Run CLI tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -v
```

Expected: all CLI tests pass.

- [x] **Step 8: Commit Task 5**

```bash
git add src/nba_forecast/cli.py tests/test_cli.py
git commit -m "feat: add prediction registry commands"
```

## Task 6: Document and Demonstrate the Manual Operating Workflow

**Files:**
- Create: `docs/decisions/0005-immutable-prediction-registry.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/data_dictionary.md`
- Modify: `docs/runbook.md`
- Modify: `.gitignore`
- Modify: `tests/test_project_config.py`

- [x] **Step 1: Add the architecture decision record**

Document:

- why overwrite-by-game was rejected
- why Parquet remains authoritative and DuckDB replaceable
- why hosted storage and automation are deferred
- consequences of preserving multiple prediction timestamps

- [x] **Step 2: Add a failing repository-hygiene test and exclude local registry artifacts**

Extend `tests/test_project_config.py` with:

```python
def test_local_prediction_registry_is_gitignored() -> None:
    gitignore = (Path(__file__).parents[1] / ".gitignore").read_text().splitlines()

    assert "data/registry/" in gitignore
```

Run:

```bash
.venv/bin/pytest tests/test_project_config.py -v
```

Expected: the new assertion fails before `.gitignore` changes.

Add:

```text
data/registry/
```

to `.gitignore`, then rerun the focused test and expect it to pass.

- [x] **Step 3: Update public and operational documentation**

Add:

- verified registry capability and limitations to `README.md`
- registry data flow and component ownership to `docs/architecture.md`
- exact schema and mutability classes to `docs/data_dictionary.md`
- register, repeat-register, settle, report, inspect-DuckDB, and failure
  recovery commands to `docs/runbook.md`

State explicitly that this is a manual local operating workflow, not yet a live
daily automated service.

- [x] **Step 4: Run a local smoke workflow**

Using a test or local model bundle and canonical games:

1. register one fixed-timestamp scheduled matchup twice through the internal
   composition workflow
2. verify one registry row remains, then run a normal new-timestamp prediction
   and verify it is preserved as another event
3. settle it against a matching completed canonical game
4. generate summary and metrics reports
5. query the DuckDB `predictions` table

Record only verified behavior in documentation. Do not commit generated
registry artifacts.

- [x] **Step 5: Run full verification**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/pytest -q
git diff --check
```

Expected: all checks pass.

- [x] **Step 6: Commit Task 6**

```bash
git add .gitignore README.md docs/architecture.md docs/data_dictionary.md \
  docs/runbook.md docs/decisions/0005-immutable-prediction-registry.md \
  tests/test_project_config.py
git commit -m "docs: add prediction registry workflow"
```

## Task 7: Publish the Focused Work Unit

**Files:**
- Modify: `docs/superpowers/plans/2026-06-15-prediction-registry.md`

- [x] **Step 1: Review scope and repository hygiene**

Confirm:

- only registry implementation, tests, and related documentation are included
- `AGENTS.md`, `.omc/`, model artifacts, generated reports, Parquet, and DuckDB
  files are not staged
- public claims distinguish forward operating records from historical
  backtests and future automation

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
Branch: feature/prediction-registry
Title: Add immutable prediction registry
```

The PR description must summarize the problem, immutable/idempotent contract,
manual operating workflow, verification results, and deferred automation
boundary.
