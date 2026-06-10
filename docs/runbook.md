# Data Pipeline Runbook

## Purpose

This runbook describes how to operate the implemented historical game-data
pipeline. It will expand alongside training, prediction, evaluation, and
deployment workflows.

## Environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Raw NBA Stats Cache

The NBA Stats source adapter is cache-first. A season and season type map to a
stable path:

```text
data/raw/nba_stats/league_game_finder/<season>/<season-type>.csv
data/raw/nba_stats/league_game_finder/<season>/<season-type>.metadata.json
```

Normal operation reuses an existing CSV without a network request. A force
refresh replaces the raw CSV and metadata. Raw extracts should not be edited by
hand.

Metadata records the endpoint, season, season type, fetch timestamp, and source
row count.

Fetch or reuse one raw cache:

```bash
nba-forecast fetch-games \
  --season 2025-26 \
  --season-type "Regular Season" \
  --cache-dir data/raw
```

Use `--force` only when an intentional source refresh should replace the
existing raw extract.

## Build Canonical Games

Build from any source-shaped raw CSV:

```bash
nba-forecast build-games \
  --raw-csv tests/fixtures/team_game_rows.csv \
  --output-dir /tmp/nba-forecast-smoke
```

The command transforms and validates the rows before writing
`processed/games.parquet` and `nba_forecast.duckdb`.

`--raw-csv` accepts one or more paths. Pass all season-level source caches to
build the combined historical game table used by temporal evaluation.

## Verify Processed Output

Query the local DuckDB artifact:

```bash
python -c "import duckdb; print(duckdb.connect('/tmp/nba-forecast-smoke/nba_forecast.duckdb').execute('select count(*) from games').fetchone())"
```

The committed fixture build should report exactly two canonical games.

## Build Point-in-Time Features

```bash
nba-forecast build-features \
  --games-parquet data/processed/games.parquet \
  --output-dir data
```

The command writes `data/features/games.parquet`. Current-game outcomes and
scores are not included in `MODEL_FEATURE_COLUMNS`.

## Evaluate Baselines

```bash
nba-forecast evaluate-baselines \
  --features-parquet data/features/games.parquet \
  --train-seasons 22022 22023 22024 \
  --test-season 22025 \
  --output-dir .
```

The command rejects overlapping or reversed temporal splits and writes
`artifacts/reports/baseline_metrics.csv`.

## Failure Recovery

- If NBA Stats is unavailable, retain and use the existing raw cache.
- If a fetch creates incomplete data, do not build processed artifacts from it;
  retain the previous known-good extract and investigate source coverage.
- If canonical validation fails, read every rule failure in the exception
  before changing transformation logic or accepting the source data.
