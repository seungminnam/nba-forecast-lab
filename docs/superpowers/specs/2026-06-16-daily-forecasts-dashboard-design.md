# Daily Forecasts Dashboard Design

## Goal

Add a Streamlit product surface for the manual daily schedule prediction
workflow. The tab should make the project feel reusable beyond the 2026 Finals
by showing the latest generated daily forecast artifact, while clearly stating
that the workflow is local and manual rather than live automation.

## User Experience Decision

Use **Latest Report First** as the default layout, with a date override as a
secondary inspection control.

This is the recommended portfolio direction because the dashboard opens on the
most recent operating result instead of asking the viewer to configure a date
before seeing value. The date override remains useful for historical artifact
inspection and no-game/offseason days.

## Scope

In scope:

- Add a new Streamlit tab before Historical Replay.
- Load the newest `daily_predictions_YYYY-MM-DD.json` report from
  `artifacts/predictions/`.
- Allow a user-selected date override to load a specific daily report.
- Display batch-level status: prediction date, timestamp, schedule snapshot,
  eligible games, excluded games, and prediction count.
- Display game-level cards or a table with home/away teams, probabilities,
  model version, feature version, and matchup date.
- Show calm empty states when no daily reports exist or a selected date has no
  eligible games.
- Show a clear disclosure that this is a manual local workflow, not a live
  feed, not market odds, and not betting advice.
- Add a small application service for loading and validating daily report
  artifacts so the Streamlit file does not own parsing logic.
- Update tests and documentation.

Out of scope:

- GitHub Actions cron.
- Supabase or other hosted persistence.
- Automatic settlement.
- Live NBA schedule fetching inside Streamlit.
- New model training or feature engineering.
- Betting recommendations.

## Data Contract

The UI reads JSON reports produced by:

```bash
nba-forecast predict-daily \
  --schedule-parquet data/schedules/scheduled_matchups.parquet \
  --games-parquet data/processed/games.parquet \
  --model-bundle artifacts/models/2026-06-11-recent5-raw.joblib \
  --prediction-date YYYY-MM-DD \
  --registry-dir data/registry \
  --output-dir .
```

The report path is:

```text
artifacts/predictions/daily_predictions_YYYY-MM-DD.json
```

The loader should treat the JSON report as an operating artifact and validate
the fields used by the UI. It should not infer missing predictions or call the
model.

## Proposed Components

### `application/daily_dashboard.py`

Owns report discovery and presentation-ready parsing.

Functions:

- `find_latest_daily_report(predictions_dir: Path) -> Path | None`
- `daily_report_path(predictions_dir: Path, prediction_date: date) -> Path`
- `load_daily_report(path: Path) -> DailyForecastReport`

`DailyForecastReport` should be a dataclass with normalized fields for batch
metadata and a tuple of `DailyForecastGame` rows.

### `streamlit_app.py`

Adds a `Daily Forecasts` tab before the current Historical Replay tab.

The tab should:

- Prefer the latest report when available.
- Provide a date input and load button for override.
- Render a missing-report state with the exact expected path and CLI command
  pattern.
- Render a no-game report as a successful empty state, not an error.
- Render prediction cards or a compact dataframe for report predictions.

## Visual Layout

The approved mockup uses:

- left-side main report panel
- top metric row for eligible games, registry/report status, model, and
  schedule snapshot
- prediction rows/cards ordered as the report provides them
- right-side utility column with date override, manual-workflow disclosure,
  and no-game/offseason explanation

The exact styling should follow the existing dark/teal Streamlit theme rather
than the rough browser mockup typography.

## Error Handling

- Missing predictions directory: show setup guidance and do not fail the app.
- No daily report files: show an empty operating-state card.
- Selected date without a report: show the expected filename and the
  `predict-daily` command pattern.
- Malformed report: show a readable error in the tab and keep the rest of the
  dashboard usable.
- Report with zero predictions: show batch metadata and an empty-state
  explanation.

## Testing Strategy

Add application tests for the daily dashboard loader:

- latest report discovery chooses the newest report date
- date-specific path construction
- valid report parsing
- malformed report rejection
- zero-prediction report parsing

Extend Streamlit AppTest coverage:

- tab list includes `Daily Forecasts` first
- missing local reports do not raise
- a mocked latest report renders batch metrics and game probabilities
- selected date without a report shows missing-artifact guidance
- no-game report renders as a successful empty state

Run the standard verification set:

```bash
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/pytest
git diff --check
```

## Documentation

Update:

- `README.md`: mention the dashboard can inspect generated daily reports.
- `docs/runbook.md`: add how to generate a report and view it in Streamlit.
- `docs/architecture.md`: document the dashboard read-only artifact boundary.

## Acceptance Criteria

1. The dashboard opens with a `Daily Forecasts` tab before Historical Replay.
2. The default view loads the latest local daily report if one exists.
3. Date override can inspect a specific report path.
4. Missing, malformed, and no-game states are clear and non-crashing.
5. The UI explicitly says it is manual/local and not live automation.
6. No model scoring, fetching, hosted persistence, or registry mutation occurs
   inside Streamlit.
7. Automated tests cover the loader and Streamlit rendering paths.
