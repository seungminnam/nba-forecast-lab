# Prediction Registry Design

**Status:** Approved  
**Date:** 2026-06-15  
**Scope:** Local-first immutable prediction registration, result settlement, and
performance reporting

## 1. Problem

NBA Forecast Lab can produce auditable matchup predictions and evaluate a
frozen model through historical backtests. It does not yet preserve forward
predictions across days or attach completed outcomes to those original
predictions.

Saving only the latest prediction per game would erase evidence. The available
history, model version, and feature state can change between an early forecast
and a later forecast for the same game. A trustworthy operating system must
preserve each prediction as it was originally made and evaluate it only after
the result becomes available.

## 2. Goal

Build a local-first Prediction Registry that:

- stores auditable forward predictions without overwriting them
- safely handles repeated command execution
- attaches completed outcomes without changing original prediction evidence
- reports cumulative and model-version performance
- provides a reliable manual workflow before daily automation is introduced

The registry is the operational bridge between one-off predictions and a
continuously evaluated 2026-27 forecasting system.

## 3. Decisions

### 3.1 Local-first storage

Parquet is the durable source of truth. DuckDB is a replaceable SQL query
surface synchronized from the Parquet registry.

This follows the existing storage decision and keeps the first operating
workflow reproducible without hosted credentials, network-dependent tests, or
database migrations. Supabase or another hosted store remains a later option
when the deployed application needs shared mutable state.

### 3.2 Preserve multiple forecasts for one game

The registry permits multiple predictions for the same `game_id` when they
were made at different timestamps or by different model versions. This allows
future analysis of questions such as:

- Does performance improve closer to tip-off?
- Did a new model version improve probability quality?
- Which feature state produced a particular forecast?

The first registry does not define forecast-horizon buckets because canonical
games currently contain dates rather than tip-off timestamps. It preserves the
raw prediction timestamp and game date so horizon analysis can be added once
schedule timestamps are available.

### 3.3 Immutable prediction evidence

The original prediction payload is immutable after registration. Settlement
may populate only outcome-derived fields.

Immutable fields include:

- prediction identity and timestamp
- as-of date
- game, season, and team identity
- model and feature versions
- home and away win probabilities
- exact feature snapshot

Settlement fields include:

- final home-team outcome
- settlement timestamp
- Brier contribution
- correctness

Changing an immutable field for an existing prediction identity is rejected
rather than silently replacing history.

### 3.4 Idempotent registration

The logical prediction identity is:

```text
game_id + model_version + prediction_timestamp
```

A deterministic payload fingerprint covers all immutable prediction fields.

- Re-registering an identical prediction succeeds without creating a duplicate.
- Re-registering the same identity with a different immutable payload fails.
- A different prediction timestamp or model version creates a separate record.

The registry stores prediction timestamps in normalized UTC ISO-8601 form.
Naive timestamps are invalid.

### 3.5 Canonical feature snapshots

The exact feature snapshot is stored as canonical JSON rather than flattened
registry columns. Feature sets can change across model versions, so flattening
them would make the registry schema unstable and risk losing historical
evidence.

Canonical JSON uses deterministic key ordering and JSON-compatible scalar
values. The payload fingerprint includes this canonical representation.

### 3.6 Result settlement

Settlement joins unsettled registry records to validated canonical completed
games by `game_id`. Before attaching an outcome, it verifies that the recorded
home and away team identities match the canonical game.

For a valid completed game, settlement populates:

```text
final_outcome = canonical home_win
brier_contribution = (home_win_probability - final_outcome) ** 2
is_correct = int((home_win_probability >= 0.5) == final_outcome)
settled_at = caller-supplied or current UTC timestamp
```

Settlement behavior:

- predictions without a matching completed game remain unsettled
- already settled records with the same outcome remain unchanged
- an attempted conflicting outcome or team identity raises an error
- no immutable prediction field is modified

The first registry does not settle against raw source rows. It accepts only the
validated canonical games contract.

## 4. Registry Schema

One row represents one prediction event.

| Field | Type | Mutability | Meaning |
|---|---|---|---|
| `prediction_id` | string | immutable | Deterministic identity derived from the logical key |
| `payload_fingerprint` | string | immutable | Hash of canonical immutable payload |
| `prediction_timestamp` | UTC timestamp | immutable | When the forecast was produced |
| `as_of_date` | date | immutable | Latest permitted historical cutoff |
| `game_id` | string | immutable | Scheduled or source game identifier |
| `game_date` | date | immutable | Scheduled game date |
| `season_id` | string | immutable | Source season identifier |
| `season_type` | string | immutable | Regular Season or Playoffs |
| `season_key` | string | immutable | Cross-season-phase grouping key |
| `home_team_id` | integer | immutable | Home team identifier |
| `away_team_id` | integer | immutable | Away team identifier |
| `home_team_abbreviation` | string | immutable | Home team abbreviation |
| `away_team_abbreviation` | string | immutable | Away team abbreviation |
| `model_version` | string | immutable | Frozen model bundle version |
| `feature_version` | string | immutable | Feature contract version |
| `home_win_probability` | float | immutable | Model probability for the home team |
| `away_win_probability` | float | immutable | Complementary away-team probability |
| `features_json` | string | immutable | Canonical exact feature snapshot |
| `final_outcome` | nullable integer | settlement-only | Observed home-team win indicator |
| `settled_at` | nullable UTC timestamp | settlement-only | When outcome was attached |
| `brier_contribution` | nullable float | settlement-only | Per-prediction squared error |
| `is_correct` | nullable integer | settlement-only | Thresholded correctness indicator |

The registry validates probability bounds and requires home and away
probabilities to sum to one within floating-point tolerance.

## 5. Component Boundaries

### `application/prediction_registry.py`

Owns the domain workflow:

- convert `MatchupPredictionOutput` into a registry record
- calculate deterministic identity and fingerprint
- register idempotently
- settle completed outcomes
- compute cumulative and model-version reports

It does not read or write files directly.

### `data/prediction_registry_storage.py`

Owns local persistence:

- read an absent registry as an empty schema-compatible table
- atomically write `predictions.parquet`
- create or replace the DuckDB `predictions` table
- reject invalid registry tables before persistence

### `cli.py`

Composes the domain and persistence workflows:

- optional registration from `predict-matchup`
- result settlement
- performance report generation

CLI code does not implement registry rules.

## 6. Paths and CLI

Default local registry artifacts under a supplied `--registry-dir`:

```text
<registry-dir>/predictions.parquet
<registry-dir>/prediction_registry.duckdb
```

### Register during prediction

The existing command gains an optional registry directory:

```bash
nba-forecast predict-matchup \
  ... \
  --registry-dir data/registry
```

Without `--registry-dir`, existing single-report behavior remains unchanged.

### Settle completed predictions

```bash
nba-forecast settle-predictions \
  --registry-dir data/registry \
  --games-parquet data/processed/games.parquet
```

The command reports counts for settled, already-settled, and still-unmatched
predictions.

### Report operating performance

```bash
nba-forecast report-predictions \
  --registry-dir data/registry \
  --output-dir .
```

The command writes:

```text
artifacts/reports/prediction_registry_summary.csv
artifacts/reports/prediction_registry_metrics.csv
```

The summary reports total, settled, and unsettled counts. Metrics include
Brier Score, Log Loss, Expected Calibration Error, ROC-AUC when defined, and
Accuracy for all settled predictions and for each model version. Empty or
single-class groups remain reportable and use nullable metrics where a metric
is mathematically undefined.

## 7. Failure Handling

- Missing registry files initialize an empty registry.
- Malformed registry schemas, duplicate prediction IDs, invalid probabilities,
  or partial settlement fields are rejected before persistence.
- Registration conflicts fail without changing existing artifacts.
- Settlement conflicts fail without changing existing artifacts.
- Parquet writes use a temporary file followed by atomic replacement.
- DuckDB synchronization occurs only after a valid Parquet write.

If DuckDB synchronization fails after Parquet replacement, Parquet remains the
authoritative record and a later operation may rebuild DuckDB from it.

## 8. Testing Strategy

Highest-risk behaviors receive focused network-free tests:

- identical re-registration is idempotent
- conflicting re-registration is rejected
- different timestamps and model versions are preserved
- feature JSON and fingerprints are deterministic
- settlement adds only outcome-derived fields
- unmatched games remain unsettled
- mismatched teams and conflicting outcomes are rejected
- persistence round-trips Parquet and synchronizes DuckDB
- reporting handles empty, unsettled, settled, and multi-model registries
- CLI registration, settlement, and reporting compose the shared services

Regression tests must compare immutable columns before and after settlement.

## 9. Documentation Updates

The implementation work unit updates:

- `README.md`: current capability and operating workflow
- `docs/architecture.md`: registry flow and component ownership
- `docs/data_dictionary.md`: authoritative registry schema
- `docs/runbook.md`: register, settle, report, and failure recovery commands
- `docs/decisions/`: local-first immutable registry decision

Public documentation must distinguish operating forward predictions from
historical backtests and must not claim live automation before it exists.

## 10. Excluded from This Milestone

- future NBA schedule ingestion
- daily GitHub Actions execution
- hosted databases or Supabase
- Streamlit live-registry views
- prediction-horizon buckets based on tip-off timestamps
- automated retraining, model promotion, drift alerts, or betting analysis

These are intentionally deferred until the manual registry workflow is
reliable and reproducible.

## 11. Acceptance Criteria

The milestone is complete when:

1. A matchup prediction can optionally be registered without changing existing
   single-report behavior.
2. Re-running identical registration creates no duplicate.
3. Conflicting attempts cannot overwrite original evidence.
4. Completed canonical games can settle matching predictions while unmatched
   forecasts remain open.
5. Aggregate and model-version probability metrics can be reproduced from the
   registry.
6. Parquet and DuckDB artifacts contain the same validated registry rows.
7. Tests prove prediction evidence remains unchanged through settlement.
8. Documentation explains the operating contract and the next automation
   boundary.
