# Architecture

## Phase 0/1 Data Flow

```text
nba_api LeagueGameFinder
        |
        v
immutable raw team-game CSV + source metadata
        |
        v
pair home and away rows into canonical completed games
        |
        v
validate identifiers, teams, outcomes, scores, and uniqueness
        |
        +------------------+
        |                  |
        v                  v
games.parquet       DuckDB games table
```

The raw cache preserves source-shaped records. Transformation and validation
are pure, network-free operations so tests and historical rebuilds remain
reliable when the source is unavailable.

## Component Boundaries

- `data/source_nba.py` owns NBA Stats access and raw-cache behavior.
- `data/transform.py` owns source-row to canonical-game transformation.
- `data/validate.py` owns canonical table invariants.
- `data/storage.py` owns processed Parquet and DuckDB persistence.
- `cli.py` composes the components into reproducible user commands.

Future feature generation must consume the canonical game contract rather than
source-shaped NBA Stats rows.

## Source Cache Contract

NBA Stats access is cache-first. Each `LeagueGameFinder` season and season-type
request maps to a stable raw CSV and adjacent metadata JSON. Network access
occurs only when the cache is missing or a force refresh is explicitly
requested. Tests inject a fetcher and never access the network.

The source adapter was live-smoke-tested against the 2025-26 regular season.
The resulting 2,460 team-game rows produced 1,230 validated canonical games.
See `docs/source_report.md` for source behavior and observed anomalies.

## Persistence Contract

Only validated canonical games are persisted. The writer atomically replaces
`processed/games.parquet`, then creates or replaces the DuckDB `games` table.
Parquet is the durable processed artifact; DuckDB is the local analytical query
surface.
