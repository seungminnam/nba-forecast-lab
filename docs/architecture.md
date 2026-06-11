# Architecture

## Phase 0/1 Data Flow

```text
nba_api LeagueGameFinder
        |
        v
immutable raw team-game CSV + source metadata
        |
        v
contextual transform preserving season_id, season_type, and season_key
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

The adjacent metadata sidecar supplies the request's season and season type.
The raw CSV remains unmodified. Canonical `season_key` uses that season label
to connect regular-season and playoff state without rewriting the source
`season_id`.

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

## Feature and Baseline Flow

```text
processed/games.parquet
        |
        v
shifted team state + sequential pre-game Elo by season_key
        |
        v
features/games.parquet
        |
        v
explicit season holdout -> comparable baseline_metrics.csv
```

The feature table stores identifiers and the target for evaluation, but trained
models receive only the authoritative `MODEL_FEATURE_COLUMNS` list.

Rolling state resets and Elo offseason reversion occur only when `season_key`
changes. A source transition from regular-season `season_id=22025` to playoff
`season_id=42025` within `season_key=2025-26` does not reset team state.

## Model and Simulation Boundary

```text
prepared game context
        |
        v
frozen probability model bundle
        |
        v
home-team win probability provider
        |
        v
model-independent best-of-seven simulator
        |
        v
series winner and length distributions
```

The simulator consumes a callable that returns the home team's probability for
one `SeriesGameContext`. It does not load a model, construct features, or
change probabilities itself. This boundary allows deterministic fixed-
probability tests today and prepared model-backed probabilities in the future.

Each sampled series follows home order `A, A, B, B, A, B, A`, where Team A
owns home-court advantage, and stops immediately when either team reaches four
wins. The default displayed result uses 10,000 simulations.

The current frozen model bundle evaluates historical or scheduled matchup
feature rows. Connecting stored matchup predictions to the simulation provider
remains application-integration work; the simulator must not invent missing
team state.

## As-of Matchup Prediction Flow

```text
canonical completed games + ScheduledMatchup + as_of_date
        |
        v
strict game_date < as_of_date history snapshot
        |
        v
ephemeral scheduled row -> shared historical feature builders
        |
        v
frozen ModelBundle -> auditable matchup prediction JSON
```

`features/matchup_features.py` owns the scheduled feature snapshot.
`application/matchup_prediction.py` owns bundle scoring and report assembly.
The ephemeral scheduled row exists only during feature computation and is
never persisted as a canonical completed game.

## Simulator Lab Application Boundary

`application/simulator_lab.py` is the shared application workflow used by both
the CLI and Streamlit. It validates explicit assumptions, converts Team A's
home and away win probabilities into the simulator's home-team probability
provider, and returns chart-ready tables.

```text
CLI arguments or Streamlit controls
        |
        v
SimulatorLabInput -> run_simulator_lab
        |
        +--> JSON report
        |
        +--> Streamlit metrics and charts
```

Neither CLI nor Streamlit trains a model during a request. The current UI is
an assumption-based simulator lab; the model-backed matchup workflow currently
exists through the CLI and is not yet connected to the UI or simulator.
