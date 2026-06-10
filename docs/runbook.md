# Data Pipeline Runbook

## Purpose

This runbook describes how to operate the implemented historical game-data
pipeline. It will expand alongside training, prediction, evaluation, and
deployment workflows.

## Environment

```bash
python -m venv .venv
source .venv/bin/activate
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

## Failure Recovery

- If NBA Stats is unavailable, retain and use the existing raw cache.
- If a fetch creates incomplete data, do not build processed artifacts from it;
  retain the previous known-good extract and investigate source coverage.
- If canonical validation fails, read every rule failure in the exception
  before changing transformation logic or accepting the source data.

