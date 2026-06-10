# NBA Forecast Lab

NBA Forecast Lab is a documentation-first, end-to-end machine learning project
for calibrated NBA pre-game win probabilities and playoff series simulation.

The project is under active development. Phase 0/1 builds a reproducible,
validated historical game-data pipeline before any model performance claims are
made.

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

## Development Setup

Python 3.9 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest
```

No model result is reported until it has been measured on an untouched
out-of-time test period.

## Documentation

- [Product requirements and system design](docs/superpowers/specs/2026-06-10-nba-forecast-lab-design.md)
- [Phase 0/1 implementation plan](docs/superpowers/plans/2026-06-10-phase-0-1-foundation-data.md)
- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data_dictionary.md)
- [Storage decision](docs/decisions/0001-data-storage.md)

## Attribution and Limitations

The primary planned source is the NBA Stats API accessed through `nba_api`.
Source availability, rate limits, data completeness, and usage restrictions
will be documented as the pipeline is verified.

This project does not provide betting advice and does not claim profitability.

