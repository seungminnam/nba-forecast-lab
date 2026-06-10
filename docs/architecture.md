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

