# Daily Schedule Predictions Design

**Status:** Approved  
**Date:** 2026-06-15  
**Scope:** Immutable season-schedule snapshots, canonical scheduled matchups,
and one daily local batch-prediction workflow

## 1. Problem

NBA Forecast Lab can score one explicitly supplied scheduled matchup and
preserve it in the Prediction Registry. It cannot yet discover upcoming games
without manually entering every matchup.

The existing `LeagueGameFinder` source is appropriate for completed game
results, but it does not provide a reliable future schedule. A daily
forecasting system needs a separate schedule source and a deterministic rule
for deciding which games are eligible to predict.

## 2. Goal

Build a local-first workflow that:

- fetches and preserves an auditable NBA season-schedule snapshot
- transforms source-shaped schedule rows into a stable scheduled-matchup table
- selects the not-yet-started games on one NBA calendar date
- scores every eligible game once in one batch
- registers each prediction through the existing immutable Prediction Registry
- treats a no-game day as a successful empty batch

This milestone proves the complete manual daily prediction path before hosted
registry persistence and GitHub Actions automation are introduced.

## 3. Operating Contract

### 3.1 Once per NBA calendar day

The workflow predicts one daily batch using the NBA's primary schedule
timezone, `America/New_York`. This produces a comparable operating forecast
horizon while the model has no injury, lineup, or same-day live feature feed.

The caller supplies an explicit `prediction_date` for reproducibility. A
future automation wrapper may default that value from its scheduled execution
time, but the application workflow itself does not depend on the wall clock to
choose a date.

### 3.2 Eligible games

A scheduled game is eligible only when:

- its NBA calendar date equals `prediction_date`
- its source `game_status` is `1`, meaning not started
- it is not marked postponed or conditional
- its home and away teams are confirmed
- it has a valid UTC tip-off timestamp
- its UTC tip-off timestamp is strictly after the UTC prediction timestamp
- its game ID and team identities are valid

Games that are live, final, postponed, conditional, missing confirmed teams or
a confirmed tip-off, canceled, or already past the prediction timestamp are
excluded.

`game_status == 1` is necessary but not sufficient. The timestamp check
protects against stale source status near tip-off.

### 3.3 Honest point-in-time cutoff

Every eligible matchup is scored with:

```text
as_of_date = prediction_date
```

The existing matchup feature builder therefore includes only canonical
completed games where `game_date < prediction_date`. Same-day results remain
conservatively excluded because the completed-game contract still has dates
rather than exact completion timestamps.

All predictions in one batch share one caller-supplied UTC
`prediction_timestamp`.

## 4. Source Decision

Use NBA Stats `ScheduleLeagueV2` as the first future-schedule source.

It provides the fields needed for discovery and audit:

- season year
- game ID
- game status
- NBA calendar date
- UTC tip-off timestamp
- home and away team IDs and tricodes
- postponed status and schedule labels

The source is distinct from `LeagueGameFinder`. Schedule ingestion does not
change the completed canonical-game contract or use incomplete schedule rows
as completed games.

### Alternatives considered

#### `ScoreboardV2` only

It provides a convenient date-level lookup but does not preserve the full
season schedule context. It is deferred as a later operational cross-check.

#### `ScheduleLeagueV2` plus `ScoreboardV2`

Dual-source confirmation could improve resilience but introduces conflict
resolution before the first schedule contract is proven. It is deferred.

## 5. Immutable Raw Schedule Snapshots

Each explicit fetch creates one immutable source-shaped CSV and adjacent
metadata JSON. The installed `nba_api` endpoint accepts the same season-key
format used by the project, such as `2026-27`.

```text
data/raw/nba_stats/schedule_league_v2/<season>/<fetched-at-utc-with-microseconds>.csv
data/raw/nba_stats/schedule_league_v2/<season>/<fetched-at-utc-with-microseconds>.metadata.json
```

Metadata records:

- source and endpoint
- requested season
- fetch timestamp in UTC
- source row count
- source columns

Snapshots are append-only. Filenames use filesystem-safe UTC timestamps with
microseconds, and creation fails rather than replacing a path that already
exists. A later fetch must not replace an earlier snapshot. This preserves
evidence of postponements, reschedules, status changes, and what the daily
workflow could observe at prediction time.

The fetch service accepts an injected fetcher so all automated tests remain
network-free.

## 6. Canonical Scheduled-Matchup Table

Schedule transformation emits one row per source game:

| Column | Meaning |
|---|---|
| `game_id` | Stable NBA game identifier |
| `season_id` | Derived source-compatible season identifier |
| `season_type` | `Regular Season` or `Playoffs` |
| `season_key` | Shared NBA season continuity key |
| `schedule_snapshot_at_utc` | UTC fetch timestamp from snapshot metadata |
| `nba_game_date` | NBA calendar date in `America/New_York` |
| `tipoff_at_utc` | Nullable timezone-aware UTC scheduled tip-off |
| `game_status` | Integer source status |
| `game_status_text` | Source status label |
| `is_postponed` | Normalized postponed indicator |
| `is_conditional` | Whether the game is listed only if necessary |
| `has_confirmed_matchup` | Whether both team identities are finalized |
| `home_team_id`, `away_team_id` | Nullable team identifiers |
| `home_team_abbreviation`, `away_team_abbreviation` | Nullable team tricodes |

The table is a schedule contract, not a completed-game contract. It does not
contain scores, box scores, or `home_win`.

`schedule_snapshot_at_utc` makes every transformed row traceable to the raw
schedule evidence used by the daily workflow.

### 6.1 Season-type derivation

`ScheduleLeagueV2` contains multiple competition phases. The transform derives
the supported phase for each row from its `gameId` prefix:

- `002` -> `Regular Season`
- `004` -> `Playoffs`

Preseason, All-Star, play-in, tournament-only, or unrecognized game prefixes
are excluded from this initial workflow rather than silently assigned to the
wrong modeling context.

The derived `season_type` determines each row's canonical `season_id` through
the existing `expected_season_id` contract. One canonical schedule table may
therefore preserve both supported phases and continue from the regular season
into the playoffs without changing artifacts or workflows.

### 6.2 Validation

The canonical scheduled table rejects:

- missing required columns
- duplicate or empty game IDs
- invalid season context
- invalid non-null UTC tip-off timestamps
- invalid NBA calendar dates
- identical confirmed home and away teams
- partially populated or invalid confirmed team identities
- null, non-integer, or negative game statuses
- a non-null UTC tip-off whose New York calendar date disagrees with
  `nba_game_date`

An empty table is valid, including dates with no games or schedule snapshots
that contain no rows for the requested supported phase.

A null tip-off is valid schedule evidence for postponed, conditional, or
not-yet-finalized games. It is never eligible for prediction.

Unknown or zero-valued source team identities are normalized to null together.
A row with unconfirmed teams is valid schedule evidence and is never eligible
for prediction.

Known source statuses are `1` (not started), `2` (in progress), and `3`
(final). Other nonnegative integer statuses remain audit evidence but are
never eligible because the daily selector accepts only status `1`.
`is_conditional` is derived from `ifNecessary`. `is_postponed` is true when
the source postponed indicator is populated with a nonzero value.

## 7. Daily Batch Prediction Application

`application/daily_predictions.py` owns the pure orchestration workflow:

```text
canonical scheduled matchups
        +
validated canonical completed games
        +
one frozen model bundle
        +
prediction_date and UTC prediction_timestamp
        |
        v
select eligible daily games
        |
        v
convert each row to ScheduledMatchup
        |
        v
predict_scheduled_matchup with shared as_of_date
        |
        v
register each event in a candidate registry
        |
        v
return predictions, candidate registry, and batch summary
```

The application service does not read or write files.

The daily application requires a non-empty canonical season schedule containing
exactly one snapshot timestamp. A no-game day means that this valid season
schedule has zero eligible rows for `prediction_date`; it does not mean that
the schedule artifact itself is empty.

### 7.1 Determinism

Eligible games are sorted by `tipoff_at_utc` then `game_id`. All calls receive
the same UTC prediction timestamp. Re-running the same batch with the same
inputs and timestamp is idempotent through the existing registry contract.

Running the same date at another timestamp creates another legitimate forecast
event for each still-eligible game.

### 7.2 Batch atomicity

The workflow registers predictions into an in-memory candidate registry.
If any matchup fails feature construction, scoring, or registration, the
workflow raises and does not return a partially updated registry for
persistence.

The CLI writes the candidate registry only after the entire batch succeeds.

### 7.3 Output

The application result contains:

- `prediction_date`
- batch prediction timestamp
- total schedule rows inspected
- eligible game count
- excluded game count
- one auditable matchup report per eligible game
- the schedule snapshot timestamp used for the batch
- the complete candidate registry

The CLI writes one batch report:

```text
artifacts/predictions/daily_predictions_<prediction-date>.json
```

The existing Registry Parquet and DuckDB artifacts are updated only after a
successful non-conflicting batch. A zero-game batch writes a valid empty
report and leaves the registry unchanged.

## 8. Component Boundaries

### `data/source_schedule.py`

- fetch `ScheduleLeagueV2`
- write immutable raw snapshots and metadata
- load an explicit snapshot

### `data/schedule_transform.py`

- transform source-shaped rows into the canonical scheduled table
- derive supported season context per row
- validate schedule-only invariants

### `application/daily_predictions.py`

- select eligible daily games
- convert rows to `ScheduledMatchup`
- score and register the complete candidate batch atomically

### `cli.py`

- compose fetch, transform, batch prediction, and persistence commands
- never reimplement eligibility, transformation, or registry rules

## 9. CLI Workflows

### Fetch one immutable season-schedule snapshot

```bash
nba-forecast fetch-schedule \
  --season 2026-27 \
  --cache-dir data/raw
```

The command prints the exact snapshot CSV and metadata paths.

### Build one canonical scheduled-matchup table

```bash
nba-forecast build-schedule \
  --raw-schedule-csv <explicit-snapshot.csv> \
  --output-dir data
```

The command writes:

```text
data/schedules/scheduled_matchups.parquet
data/schedules/schedule.duckdb
```

### Predict one NBA calendar day

```bash
nba-forecast predict-daily \
  --schedule-parquet data/schedules/scheduled_matchups.parquet \
  --games-parquet data/processed/games.parquet \
  --model-bundle artifacts/models/2026-06-11-recent5-raw.joblib \
  --prediction-date 2026-10-22 \
  --registry-dir data/registry \
  --output-dir .
```

The CLI captures one UTC prediction timestamp at command start and supplies it
to the application workflow. The command does not expose an arbitrary
prediction timestamp override to normal users; tests call the private
composition function with a fixed timestamp.

## 10. Failure Handling

- Source fetch failure or snapshot-path collision leaves all prior immutable
  snapshots untouched.
- A malformed snapshot fails before canonical schedule artifacts are written.
- Schedule build uses an atomic Parquet replacement and rebuildable DuckDB
  table, following the existing local analytical-storage pattern.
- A no-game day is successful and produces an empty daily report.
- Batch scoring or registration conflict fails before registry persistence.
- The workflow does not fall back to predicting live or completed games.
- Tests inject source rows and never call NBA Stats.

## 11. Documentation Updates

The implementation work unit updates:

- `README.md`: manual daily prediction capability and limitations
- `docs/architecture.md`: schedule and batch prediction flow
- `docs/data_dictionary.md`: scheduled-matchup schema and statuses
- `docs/runbook.md`: fetch, build, predict, inspect, and recovery commands
- `docs/decisions/`: schedule-source and once-daily operating decision

Public documentation must not call the workflow live or automated before
hosted persistence and a scheduled runner exist.

## 12. Excluded from This Milestone

- GitHub Actions cron execution
- persistence across ephemeral CI runners
- Supabase or other hosted registry storage
- automated completed-game refresh and result settlement
- `ScoreboardV2` cross-checks
- multiple same-day forecast horizons
- injury, lineup, market, travel, or live game data
- future rolling-feature updates between games on the same date
- Streamlit live schedule or registry views

## 13. Acceptance Criteria

The milestone is complete when:

1. One explicit `ScheduleLeagueV2` fetch creates a new immutable snapshot.
2. Source schedule rows transform into a validated canonical scheduled table.
3. Unsupported phases, started games, stale status rows, and invalid schedule
   rows cannot become daily forecasts.
4. One daily batch scores and registers every eligible game with one shared UTC
   timestamp and one shared `as_of_date`.
5. Re-running the same fixed-timestamp batch is idempotent.
6. A batch failure cannot persist a partial registry.
7. A no-game date succeeds with an empty report and unchanged registry.
8. Schedule Parquet and DuckDB contain the same validated rows.
9. Tests are network-free and protect schedule transformation, eligibility,
   point-in-time scoring, atomicity, persistence, and CLI composition.
10. Documentation clearly separates this manual daily workflow from the next
    hosted-persistence and automation milestone.
