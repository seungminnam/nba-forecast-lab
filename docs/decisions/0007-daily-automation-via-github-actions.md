# ADR 0007 — Daily prediction automation via GitHub Actions

**Status:** Accepted  
**Date:** 2026-06-16

## Context

The Daily Forecasts tab reads pre-generated prediction JSON files from
`artifacts/predictions/`. During the 2025-26 season these files were
produced manually. For the 2026-27 season and beyond, predictions must
be generated automatically each day games are scheduled so the Streamlit
dashboard stays current without manual intervention.

Three approaches were considered:

| Option | Cost | Complexity | Notes |
|---|---|---|---|
| A — GitHub Actions + git commit | Free (public repo) | Low | Output lands in git history; Streamlit Cloud redeploys on push |
| B — External cron service (e.g. Railway, Render) | Paid tier likely needed | Medium | Extra secrets management, additional infrastructure |
| C — Streamlit scheduled jobs | Not available on Community tier | — | Ruled out |

## Decision

Use **GitHub Actions cron** (Option A). A daily workflow runs
`nba-forecast predict-daily`, then commits the resulting JSON to
`artifacts/predictions/` and pushes to `main`. Streamlit Cloud detects
the push and redeploys automatically.

## Data strategy

The `predict-daily` command requires four inputs. Their committed
locations are:

| Input | Committed path | Updated |
|---|---|---|
| Model bundle | `data/snapshots/{date}/{version}.joblib` | When model is retrained (per season or on significant data drift) |
| Games parquet | `data/snapshots/{date}/games.parquet` | Same cadence as model retraining |
| Schedule parquet | `data/snapshots/{date}/schedule.parquet` | Once per season, during season-setup |
| Prediction registry | `artifacts/predictions/registry/` | Each CI run; committed alongside prediction JSON |

All of these live under `data/snapshots/` (not gitignored) or
`artifacts/predictions/` (explicitly committed since ADR 0005).

The games snapshot will grow stale across a season (recent-5 features
drift). The acceptable trade-off: rebuild the snapshot when retraining,
targeting a monthly cadence during the regular season. Live per-game
accuracy is not a goal of this project.

## Season-setup checklist (required before 2026-27 opening night)

- [ ] Fetch 2026-27 season schedule: `nba-forecast fetch-schedule --season 2026-27`
- [ ] Build schedule parquet: `nba-forecast build-schedule ...`
- [ ] Copy schedule parquet to `data/snapshots/{new-date}/schedule.parquet`
- [ ] Retrain model on updated games data; commit bundle to `data/snapshots/{new-date}/`
- [ ] Update `SNAPSHOT_DIR` variable in `.github/workflows/daily-predictions.yml`
- [ ] Enable the cron trigger (uncomment `schedule:` block)

## Off-season behaviour

Between seasons the workflow runs daily but the schedule has no eligible
games. `predict-daily` exits cleanly with `eligible_game_count: 0` and
writes no prediction file. No commit is made. The Streamlit tab shows
the most recent committed report.

## Consequences

- Prediction history accumulates in git as plain JSON — transparent and
  diffable.
- Each retraining cycle requires a manual snapshot update and a one-line
  workflow change (the `SNAPSHOT_DIR` variable).
- `data/registry/` (gitignored) is not used; the registry lives under
  `artifacts/predictions/registry/` instead.
