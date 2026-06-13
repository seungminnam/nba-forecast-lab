# NBA Forecast Lab

NBA Forecast Lab is a documentation-first, end-to-end machine learning project
for calibrated NBA pre-game win probabilities and playoff series simulation.

The project is under active development. The repository now provides a
reproducible historical data pipeline, leakage-safe pre-game features, and
time-aware baseline evaluation. No historical model performance claim is made
until the full multi-season experiment is run.

## Research Question

> Using only information available before tip-off, how accurately can NBA game
> win probabilities be predicted, and how can those probabilities support
> playoff series simulations?

## Planned Product

- Leakage-safe team features and time-aware validation
- Elo, Logistic Regression, and XGBoost probability comparisons
- Probability calibration using Platt scaling and Isotonic Regression
- `as_of_date` historical replay
- Best-of-seven Monte Carlo simulations
- A deployed Streamlit dashboard

## Current Architecture

```text
NBA Stats team-game rows
        |
        v
immutable raw cache -> canonical games -> validation -> Parquet + DuckDB
                                                        |
                                                        v
                                           features, models, simulation
```

Canonical games preserve NBA Stats `season_id` and `season_type`, while a
separate `season_key` keeps rolling state and Elo continuous from the regular
season into the playoffs.

## Current Verified Status

- Cache-first `nba_api` source adapter with adjacent source metadata
- Canonical one-row-per-game transformation and validation
- Parquet and DuckDB processed storage
- Offline fixture build and network-free automated tests
- Live source smoke test: 2,460 NBA Stats team rows transformed into 1,230
  canonical 2025-26 regular-season games
- Live playoff refresh: 168 NBA Stats team rows transformed into 84 completed
  2025-26 playoff games through June 10, 2026
- Regular-season-to-playoff rolling-state and Elo continuity
- Shifted rolling team state and sequential pre-game Elo
- Explicit season holdouts and comparable probability baseline metrics
- Auditable `as_of_date` scheduled-matchup prediction workflow
- Model-backed playoff-series Historical Replay at arbitrary cutoffs
- Interactive Historical Replay and assumption-based Simulator Lab

## Measured Baseline Result

On the untouched 2025-26 regular season, the current Logistic Regression
baseline achieved:

| Brier Score | Log Loss | ROC-AUC | Accuracy |
|---:|---:|---:|---:|
| **0.20649** | **0.60051** | **0.73357** | **0.68293** |

It reduced Brier Score by **3.33%** relative to the Elo baseline. This earlier
full-history baseline remains useful context; subsequent validation-only model
and calibration selection produced the frozen recent-five Raw Logistic
Regression bundle described below.

## Current Model Selection Result

Using the existing 19 pre-game features, Logistic Regression and a
fixed-configuration XGBoost model were compared across recent three-season,
recent five-season, and decayed full-history training windows on the 2024-25
validation season.

Recent-five Logistic Regression produced the best validation probability
metrics:

| Model | Training window | Brier Score | Log Loss |
|---|---|---:|---:|
| Logistic Regression | Recent 5 | **0.208594** | **0.603709** |
| XGBoost | Decayed full history | 0.211099 | 0.609608 |

The result selected recent-five Logistic Regression for calibration. It does
not claim that XGBoost is universally worse; with the current compact and
correlated feature set, its added complexity did not improve validation
probability quality.

## Selected Probability Model

Raw, Platt, and Isotonic probabilities were selected using chronological
halves of the 2024-25 validation season. Raw Logistic Regression probabilities
performed best, so no additional probability transform was retained.

The frozen `2026-06-11-recent5-raw` bundle was then evaluated once on the
untouched 2025-26 regular season:

| Brier Score | Log Loss | ECE | ROC-AUC | Accuracy |
|---:|---:|---:|---:|---:|
| **0.207254** | **0.601983** | **0.039914** | **0.732116** | **0.689431** |

Retaining Raw is a measured calibration decision. See the model card and
experiment history for the temporal contract, alternatives, and limitations.

## Best-of-Seven Simulator

The model-independent Monte Carlo engine now supports:

- NBA home-court order `A, A, B, B, A, B, A`
- immediate stopping when either team reaches four wins
- context-aware home-team probability providers
- deterministic seeded simulation
- series winner, winner-in-N, length, and expected-length distributions

A 10,000-run seeded engine example using a synthetic `60%` probability for
whichever team is home produced a `53.87%` series win probability for the
home-court owner and an expected length of `5.8408` games. This is a simulator
verification example, not an NBA team prediction.

The frozen model now powers Historical Replay. It reconstructs the observed
playoff-series score strictly before an `as_of_date`, computes two frozen
venue-direction probabilities, and simulates only the remaining games.

Verified 2026 Finals replays:

| Cutoff | Observed score | SAS series win | NYK series win |
|---|---|---:|---:|
| Before Game 4, June 10 | SAS 1-2 NYK | 31.13% | 68.87% |
| Before Game 5, June 11 | SAS 1-3 NYK | 13.79% | 86.21% |

These seeded workflow results are not measured playoff predictive accuracy.
Venue probabilities remain frozen during simulation because sampled wins do
not provide future box scores needed to update rolling features.

## Simulator Lab UI

The first interactive product surface is available locally:

```bash
source .venv/bin/activate
streamlit run streamlit_app.py
```

The app provides two modes:

- **Model-Backed Historical Replay:** reconstructs an observed playoff series
  at a declared cutoff and simulates the remaining games.
- **Assumption Lab:** lets users edit hypothetical probabilities, simulation
  count, and random seed.

The two modes are clearly separated so manually entered assumptions are never
presented as observed historical evidence.

## Development Setup

Python 3.9 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest
```

No model result is reported until it has been measured on an untouched
out-of-time test period.

## Reproduce the Current Pipeline

The committed fixture provides an offline smoke test for the complete Phase 0/1
build:

```bash
nba-forecast build-games \
  --raw-csv tests/fixtures/team_game_rows.csv \
  --output-dir /tmp/nba-forecast-smoke
```

`--raw-csv` accepts multiple season files, so a complete historical build can
combine the season-level raw caches in one command. Every raw CSV requires its
adjacent `.metadata.json` sidecar so the build can preserve source season type
and derive the shared `season_key`.

Expected outputs:

```text
/tmp/nba-forecast-smoke/processed/games.parquet
/tmp/nba-forecast-smoke/nba_forecast.duckdb
```

Populate one raw source cache when network access is available:

```bash
nba-forecast fetch-games \
  --season 2025-26 \
  --season-type "Regular Season" \
  --cache-dir data/raw

nba-forecast fetch-games \
  --season 2025-26 \
  --season-type Playoffs \
  --cache-dir data/raw
```

Build pre-game features and evaluate baselines with explicit season holdouts:

```bash
nba-forecast build-features \
  --games-parquet data/processed/games.parquet \
  --output-dir data

nba-forecast evaluate-baselines \
  --features-parquet data/features/games.parquet \
  --train-seasons 22015 22016 22017 22018 22019 22020 22021 22022 22023 22024 \
  --test-season 22025 \
  --output-dir .

nba-forecast simulate-series \
  --team-a Knicks \
  --team-b Spurs \
  --team-a-home-probability 0.62 \
  --team-a-away-probability 0.47 \
  --simulations 10000 \
  --seed 2026 \
  --output-dir .

nba-forecast predict-matchup \
  --games-parquet data/processed/games.parquet \
  --model-bundle artifacts/models/2026-06-11-recent5-raw.joblib \
  --game-id scheduled-example \
  --game-date 2026-06-12 \
  --as-of-date 2026-06-11 \
  --season-id 42025 \
  --season-type Playoffs \
  --season-key 2025-26 \
  --home-team-id 1610612759 \
  --away-team-id 1610612752 \
  --home-team-abbreviation SAS \
  --away-team-abbreviation NYK \
  --output-dir .

nba-forecast replay-series \
  --games-parquet data/processed/games.parquet \
  --model-bundle artifacts/models/2026-06-11-recent5-raw.joblib \
  --as-of-date 2026-06-10 \
  --next-game-date 2026-06-10 \
  --season-id 42025 \
  --season-type Playoffs \
  --season-key 2025-26 \
  --team-a-id 1610612759 \
  --team-a-abbreviation SAS \
  --team-b-id 1610612752 \
  --team-b-abbreviation NYK \
  --simulations 10000 \
  --seed 2026 \
  --output-dir .
```

The verified local refresh now ends on **June 10, 2026** and includes 84
completed 2025-26 playoff games. A June 11 cutoff smoke prediction for Finals
Game 5 estimated a `54.57%` SAS home-win probability. This verifies the
current as-of workflow; it is not measured playoff accuracy and the frozen
model remains trained and evaluated on regular-season games only.

## Documentation

- [Product requirements and system design](docs/superpowers/specs/2026-06-10-nba-forecast-lab-design.md)
- [Phase 0/1 implementation plan](docs/superpowers/plans/2026-06-10-phase-0-1-foundation-data.md)
- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data_dictionary.md)
- [Storage decision](docs/decisions/0001-data-storage.md)
- [Data pipeline runbook](docs/runbook.md)
- [NBA Stats source report](docs/source_report.md)
- [Experiment history and model-selection evidence](docs/experiments.md)
- [Selected probability model card](docs/model_card.md)
- [Series simulation contract](docs/decisions/0002-series-simulation-contract.md)
- [As-of matchup prediction contract](docs/decisions/0003-as-of-matchup-prediction-contract.md)
- [Simulator Lab UI design](docs/superpowers/specs/2026-06-11-simulator-lab-ui-design.md)
- [Playoff data continuity design](docs/superpowers/specs/2026-06-11-playoff-data-continuity-design.md)
- [Model-backed series replay design](docs/superpowers/specs/2026-06-11-model-backed-series-replay-design.md)

## Attribution and Limitations

The primary planned source is the NBA Stats API accessed through `nba_api`.
Source availability, rate limits, data completeness, and usage restrictions
will be documented as the pipeline is verified.

This project does not provide betting advice and does not claim profitability.
