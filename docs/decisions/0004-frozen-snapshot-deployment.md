# ADR 0004: Frozen Snapshot Data and Model Artifacts for Deployment

## Status

Accepted on 2026-06-13.

## Context

`streamlit_app.py` reads `data/processed/games.parquet` and a frozen model
bundle from `artifacts/models/`. Both are pipeline-generated outputs excluded
from Git by `.gitignore`, so they do not exist in a fresh clone or in the
environment Streamlit Community Cloud builds from a GitHub repository.

Deploying the app therefore requires some copy of these two files to be
present at runtime. The combined size of the files the app needs is small:
`games.parquet` is 267 KB and the `2026-06-11-recent5-raw.joblib` model bundle
is 4 KB, for a total of approximately 271 KB.

## Decision

Commit a small frozen snapshot under `data/snapshots/2026-06-10/`, containing:

- `games.parquet` — a copy of the verified `data/processed/games.parquet` as
  of the June 10, 2026 processed-data refresh described in `docs/runbook.md`
- `2026-06-11-recent5-raw.joblib` — a copy of the frozen
  `2026-06-11-recent5-raw` model bundle described in `docs/model_card.md`

`streamlit_app.py` reads `GAMES_PATH` and `MODEL_PATH` from this snapshot
directory instead of from `data/processed/` or `artifacts/models/`.

`data/snapshots/` is not covered by any existing `.gitignore` pattern
(`data/raw/`, `data/processed/`, `data/features/`, `data/predictions/`,
`artifacts/`), so no `.gitignore` change is required. Pipeline-generated files
under `data/processed/` and `artifacts/models/` remain gitignored and
independent of this snapshot; regenerating them does not change the deployed
app until the snapshot is intentionally refreshed.

## Alternatives Considered

### GitHub Release asset with runtime download

Rejected. Adds a network dependency and download/cache logic to the deployed
app for ~271 KB of data, which is small enough to commit directly.

### Recompute from `data/features/games.parquet` at deploy time

Rejected. The features parquet is 4.2 MB (versus 267 KB for the games
parquet), and the app would need to re-run evaluation/calibration code paths
that already have documented, frozen results in `docs/experiments.md`.

## Consequences

- The deployed app's data and model are static and dated 2026-06-10/11 until
  someone replaces the files under `data/snapshots/2026-06-10/` and
  redeploys.
- A future automated refresh (Phase 6) can write a new dated snapshot
  directory and update `GAMES_PATH`/`MODEL_PATH` without changing this
  decision's structure.
- README and the Streamlit app must disclose that the deployed instance
  reflects this frozen snapshot, not live data.
