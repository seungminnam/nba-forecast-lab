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

On macOS, XGBoost also requires the OpenMP runtime:

```bash
brew install libomp
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

Fetch all configured historical regular seasons:

```bash
nba-forecast fetch-history \
  --season-types "Regular Season" \
  --cache-dir data/raw
```

`fetch-history` is also cache-first. It requests only missing files unless
`--force` is supplied.

Fetch or reuse the current playoff cache:

```bash
nba-forecast fetch-games \
  --season 2025-26 \
  --season-type Playoffs \
  --cache-dir data/raw
```

## Build Canonical Games

Build from a source-shaped raw CSV with its adjacent metadata sidecar:

```bash
nba-forecast build-games \
  --raw-csv tests/fixtures/team_game_rows.csv \
  --output-dir /tmp/nba-forecast-smoke
```

The command transforms and validates the rows before writing
`processed/games.parquet` and `nba_forecast.duckdb`.

`--raw-csv` accepts one or more paths. Pass all season-level source caches to
build the combined historical game table used by temporal evaluation. The
command rejects files without valid metadata because `season_type` and
`season_key` cannot be safely inferred from game rows alone.

Build the verified regular-season history plus current playoffs:

```bash
nba-forecast build-games \
  --raw-csv data/raw/nba_stats/league_game_finder/*/regular-season.csv \
    data/raw/nba_stats/league_game_finder/2025-26/playoffs.csv \
  --output-dir data
```

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

## Compare Training Windows and Model Classes

Until the model experiment is exposed through the consolidated Phase 3 CLI,
run the validation-only comparison with:

```bash
python -c "from pathlib import Path; import pandas as pd; from nba_forecast.evaluation.model_comparison import compare_models_by_training_window; features = pd.read_parquet('data/features/games.parquet'); results = compare_models_by_training_window(features, validation_season='22024'); path = Path('artifacts/reports/training_window_validation.csv'); path.parent.mkdir(parents=True, exist_ok=True); results.to_csv(path, index=False); print(results.sort_values(['brier_score', 'log_loss']).to_string(index=False))"
```

This compares Logistic Regression and fixed-configuration XGBoost using recent
three-season, recent five-season, and annually decayed full-history windows.
It selects on the 2024-25 validation season and excludes all 2025-26 rows.

## Run Calibration Selection and Final Evaluation

The calibration workflow chronologically splits the 2024-25 validation season,
selects Raw, Platt, or Isotonic on its later half, refits the selected method
on the full validation predictions, and evaluates the frozen bundle once on
2025-26.

```bash
python -c "from pathlib import Path; import pandas as pd; from nba_forecast.models.calibration import run_calibration_experiment; features = pd.read_parquet('data/features/games.parquet'); result = run_calibration_experiment(features, validation_season='22024', test_season='22025'); report_dir = Path('artifacts/reports'); report_dir.mkdir(parents=True, exist_ok=True); result.selection_metrics.to_csv(report_dir / 'calibration_selection_metrics.csv', index=False); result.test_metrics.to_csv(report_dir / 'final_test_metrics.csv', index=False); print(result.selected_method); print(result.selection_metrics.to_string(index=False)); print(result.test_metrics.to_string(index=False))"
```

The complete versioned model bundle is generated programmatically with
`ModelBundle`, `ModelBundleMetadata`, and `save_model_bundle`. Generated
artifacts remain excluded from Git.

## Predict One Scheduled Matchup

```bash
nba-forecast predict-matchup \
  --games-parquet data/processed/games.parquet \
  --model-bundle artifacts/models/2026-06-11-recent5-raw.joblib \
  --game-id scheduled-2026-finals-game-5 \
  --game-date 2026-06-13 \
  --as-of-date 2026-06-11 \
  --season-id 42025 \
  --season-type Playoffs \
  --season-key 2025-26 \
  --home-team-id 1610612759 \
  --away-team-id 1610612752 \
  --home-team-abbreviation SAS \
  --away-team-abbreviation NYK \
  --output-dir .
```

The command writes `artifacts/predictions/matchup_prediction.json`, including
the UTC prediction timestamp, model and feature versions, cutoff, matchup
identity, home and away probabilities, nullable final outcome, and the exact
19 feature values used.

Only completed games with `game_date < as_of_date` are included. Because the
current canonical contract has dates rather than timestamps, same-day games
are conservatively excluded.

The verified June 11 refresh includes completed games through June 10. The
example command produced a `54.57%` SAS home-win probability for Finals Game
5. This is a timestamped workflow smoke prediction, not measured playoff
accuracy.

## Replay a Playoff Series at a Historical Cutoff

Replay the 2026 Finals immediately before Game 4:

```bash
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

The command writes
`artifacts/reports/model_backed_series_replay.json`. The verified seeded
pre-Game-4 replay reconstructed `SAS 1-2 NYK` from Games 1-3 and estimated
remaining-series win probabilities of `31.13%` SAS and `68.87%` NYK.

Changing Game 4 or later results cannot change this replay. The application
uses only games strictly before the cutoff, scores both venue directions once,
and freezes those probabilities during the remaining-series simulation.

Historical Replay does not model future box-score-driven team-state changes,
injuries, momentum, or elimination-game psychology. Use the Assumption Lab
for explicitly hypothetical probability inputs.

## Run a Seeded Series Simulation

Run a model-independent engine check with a synthetic probability provider:

```bash
python -c "from nba_forecast.simulation.series import simulate_best_of_seven; result = simulate_best_of_seven('Team A', 'Team B', lambda context: 0.60, simulations=10000, seed=2026); print(result)"
```

The provider returns the current game's home-team win probability. This
synthetic example verifies scheduling, stopping, and distribution behavior; it
is not an NBA matchup prediction. A later application workflow will construct
scheduled-game feature rows and query the frozen model bundle.

Write the same assumption-based result as a machine-readable JSON report:

```bash
nba-forecast simulate-series \
  --team-a Knicks \
  --team-b Spurs \
  --team-a-home-probability 0.62 \
  --team-a-away-probability 0.47 \
  --simulations 10000 \
  --seed 2026 \
  --output-dir .
```

This writes `artifacts/reports/series_simulation.json`.

## Run the Simulator Lab UI

```bash
streamlit run streamlit_app.py
```

Open the printed local URL, normally `http://localhost:8501`. The page is an
assumption-based demo and must not be described as a frozen-model matchup
prediction.

Verified locally on 2026-06-11:

- high-contrast dark UI rendered without browser console errors
- assumption-based warning and controls were visible
- two Vega/Altair distribution charts rendered
- Streamlit AppTest verified default results and invalid duplicate-team input

## Failure Recovery

- If NBA Stats is unavailable, retain and use the existing raw cache.
- If a fetch creates incomplete data, do not build processed artifacts from it;
  retain the previous known-good extract and investigate source coverage.
- If canonical validation fails, read every rule failure in the exception
  before changing transformation logic or accepting the source data.
