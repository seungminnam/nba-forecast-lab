# Daily Forecasts Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Streamlit Daily Forecasts tab that reads generated daily prediction reports, defaults to the latest report, supports date-specific inspection, and clearly labels the workflow as manual/local.

**Architecture:** A small application service parses and validates daily report JSON artifacts into dataclasses. Streamlit remains a read-only presentation layer that discovers local artifacts, renders report state, and never fetches schedules, scores games, mutates the registry, or calls hosted services.

**Tech Stack:** Python 3.9, dataclasses, pathlib, pandas, Streamlit, Streamlit AppTest, pytest, ruff, mypy

---

## File Structure

- Create `src/nba_forecast/application/daily_dashboard.py`
  - Read-only artifact discovery and parsing for daily prediction reports.
- Create `tests/application/test_daily_dashboard.py`
  - Unit tests for latest report discovery, path construction, parsing, and validation.
- Modify `streamlit_app.py`
  - Add `Daily Forecasts` as the first tab and render latest/date-specific daily report states.
- Modify `tests/test_streamlit_app.py`
  - Cover tab order, missing-report state, mocked report rendering, selected-date missing state, and no-game state.
- Modify `README.md`
  - Mention the dashboard can inspect generated daily reports.
- Modify `docs/runbook.md`
  - Add commands to generate a report and view it in Streamlit.
- Modify `docs/architecture.md`
  - Document the read-only dashboard artifact boundary.
- Modify `docs/superpowers/plans/2026-06-16-daily-forecasts-dashboard.md`
  - Track implementation progress.

## Task 1: Add Daily Report Loader Service

**Files:**
- Create: `tests/application/test_daily_dashboard.py`
- Create: `src/nba_forecast/application/daily_dashboard.py`

- [x] **Step 1: Write failing loader tests**

Create `tests/application/test_daily_dashboard.py` with tests for:

```python
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from nba_forecast.application.daily_dashboard import (
    DailyForecastReportError,
    daily_report_path,
    find_latest_daily_report,
    load_daily_report,
)


def _write_report(path: Path, *, prediction_date: str, predictions: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "prediction_date": prediction_date,
                "prediction_timestamp": f"{prediction_date}T12:00:00+00:00",
                "schedule_snapshot_at_utc": "2026-06-15T12:00:00+00:00",
                "total_schedule_rows": 3,
                "eligible_game_count": len(predictions),
                "excluded_game_count": 3 - len(predictions),
                "predictions": predictions,
            }
        )
    )


def _prediction(game_id: str = "0022600001") -> dict:
    return {
        "prediction_timestamp": "2026-10-22T12:00:00+00:00",
        "as_of_date": "2026-10-22",
        "matchup": {
            "game_id": game_id,
            "game_date": "2026-10-22",
            "season_id": "22026",
            "season_type": "Regular Season",
            "season_key": "2026-27",
            "home_team_id": 1610612752,
            "away_team_id": 1610612759,
            "home_team_abbreviation": "NYK",
            "away_team_abbreviation": "SAS",
        },
        "model_version": "2026-06-11-recent5-raw",
        "feature_version": "model-features-v1",
        "home_win_probability": 0.584,
        "away_win_probability": 0.416,
        "final_outcome": None,
        "features": {"elo_diff": 3.2},
    }


def test_find_latest_daily_report_chooses_newest_date(tmp_path: Path) -> None:
    _write_report(tmp_path / "daily_predictions_2026-10-22.json", prediction_date="2026-10-22", predictions=[])
    _write_report(tmp_path / "daily_predictions_2026-10-24.json", prediction_date="2026-10-24", predictions=[])
    (tmp_path / "other.json").write_text("{}")

    assert find_latest_daily_report(tmp_path) == tmp_path / "daily_predictions_2026-10-24.json"


def test_find_latest_daily_report_returns_none_when_absent(tmp_path: Path) -> None:
    assert find_latest_daily_report(tmp_path) is None


def test_daily_report_path_uses_expected_filename(tmp_path: Path) -> None:
    assert daily_report_path(tmp_path, date(2026, 10, 22)) == tmp_path / "daily_predictions_2026-10-22.json"


def test_load_daily_report_parses_valid_prediction_report(tmp_path: Path) -> None:
    path = tmp_path / "daily_predictions_2026-10-22.json"
    _write_report(path, prediction_date="2026-10-22", predictions=[_prediction()])

    report = load_daily_report(path)

    assert report.prediction_date == date(2026, 10, 22)
    assert report.eligible_game_count == 1
    assert report.prediction_count == 1
    assert report.games[0].matchup_label == "SAS at NYK"
    assert report.games[0].home_win_probability == 0.584
    assert report.games[0].away_win_probability == 0.416
    assert report.model_versions == ("2026-06-11-recent5-raw",)


def test_load_daily_report_accepts_no_game_report(tmp_path: Path) -> None:
    path = tmp_path / "daily_predictions_2026-10-26.json"
    _write_report(path, prediction_date="2026-10-26", predictions=[])

    report = load_daily_report(path)

    assert report.prediction_date == date(2026, 10, 26)
    assert report.games == ()
    assert report.prediction_count == 0


def test_load_daily_report_rejects_malformed_report(tmp_path: Path) -> None:
    path = tmp_path / "daily_predictions_2026-10-22.json"
    path.write_text(json.dumps({"prediction_date": "2026-10-22"}))

    with pytest.raises(DailyForecastReportError, match="missing"):
        load_daily_report(path)


def test_load_daily_report_rejects_non_complementary_probabilities(tmp_path: Path) -> None:
    path = tmp_path / "daily_predictions_2026-10-22.json"
    bad = _prediction()
    bad["away_win_probability"] = 0.50
    _write_report(path, prediction_date="2026-10-22", predictions=[bad])

    with pytest.raises(DailyForecastReportError, match="sum to one"):
        load_daily_report(path)
```

- [x] **Step 2: Run loader tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/application/test_daily_dashboard.py -v
```

Expected: collection fails because `nba_forecast.application.daily_dashboard`
does not exist.

- [x] **Step 3: Implement minimal loader service**

Create `src/nba_forecast/application/daily_dashboard.py` with:

```python
"""Read-only dashboard helpers for daily prediction artifacts."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

_REPORT_PATTERN = re.compile(r"daily_predictions_(\d{4}-\d{2}-\d{2})\.json$")


class DailyForecastReportError(ValueError):
    """Raised when a daily prediction report cannot be used by the dashboard."""


@dataclass(frozen=True)
class DailyForecastGame:
    game_id: str
    matchup_label: str
    game_date: date
    season_type: str
    model_version: str
    feature_version: str
    home_team_abbreviation: str
    away_team_abbreviation: str
    home_win_probability: float
    away_win_probability: float


@dataclass(frozen=True)
class DailyForecastReport:
    path: Path
    prediction_date: date
    prediction_timestamp: datetime
    schedule_snapshot_at_utc: datetime
    total_schedule_rows: int
    eligible_game_count: int
    excluded_game_count: int
    games: tuple[DailyForecastGame, ...]

    @property
    def prediction_count(self) -> int:
        return len(self.games)

    @property
    def model_versions(self) -> tuple[str, ...]:
        return tuple(sorted({game.model_version for game in self.games}))


def daily_report_path(predictions_dir: Path, prediction_date: date) -> Path:
    return predictions_dir / f"daily_predictions_{prediction_date.isoformat()}.json"


def find_latest_daily_report(predictions_dir: Path) -> Path | None:
    if not predictions_dir.exists():
        return None
    candidates: list[tuple[date, Path]] = []
    for path in predictions_dir.iterdir():
        match = _REPORT_PATTERN.fullmatch(path.name)
        if match is None:
            continue
        candidates.append((date.fromisoformat(match.group(1)), path))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def load_daily_report(path: Path) -> DailyForecastReport:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise DailyForecastReportError(f"Could not read daily report: {path}") from error

    required = (
        "prediction_date",
        "prediction_timestamp",
        "schedule_snapshot_at_utc",
        "total_schedule_rows",
        "eligible_game_count",
        "excluded_game_count",
        "predictions",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise DailyForecastReportError(f"daily report missing fields: {missing}")
    predictions = payload["predictions"]
    if not isinstance(predictions, list):
        raise DailyForecastReportError("daily report predictions must be a list")
    games = tuple(_parse_prediction(prediction) for prediction in predictions)
    return DailyForecastReport(
        path=path,
        prediction_date=date.fromisoformat(str(payload["prediction_date"])),
        prediction_timestamp=_parse_datetime(payload["prediction_timestamp"]),
        schedule_snapshot_at_utc=_parse_datetime(payload["schedule_snapshot_at_utc"]),
        total_schedule_rows=int(payload["total_schedule_rows"]),
        eligible_game_count=int(payload["eligible_game_count"]),
        excluded_game_count=int(payload["excluded_game_count"]),
        games=games,
    )


def _parse_prediction(prediction: Any) -> DailyForecastGame:
    if not isinstance(prediction, dict):
        raise DailyForecastReportError("prediction entries must be objects")
    matchup = prediction.get("matchup")
    if not isinstance(matchup, dict):
        raise DailyForecastReportError("prediction missing matchup object")
    home_probability = float(prediction["home_win_probability"])
    away_probability = float(prediction["away_win_probability"])
    if not math.isclose(home_probability + away_probability, 1.0, abs_tol=1e-9):
        raise DailyForecastReportError("prediction probabilities must sum to one")
    home = str(matchup["home_team_abbreviation"])
    away = str(matchup["away_team_abbreviation"])
    return DailyForecastGame(
        game_id=str(matchup["game_id"]),
        matchup_label=f"{away} at {home}",
        game_date=pd.Timestamp(matchup["game_date"]).date(),
        season_type=str(matchup["season_type"]),
        model_version=str(prediction["model_version"]),
        feature_version=str(prediction["feature_version"]),
        home_team_abbreviation=home,
        away_team_abbreviation=away,
        home_win_probability=home_probability,
        away_win_probability=away_probability,
    )


def _parse_datetime(value: Any) -> datetime:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise DailyForecastReportError("daily report timestamps must be timezone-aware")
    return timestamp.to_pydatetime()
```

- [x] **Step 4: Run loader tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/application/test_daily_dashboard.py -v
.venv/bin/ruff check src/nba_forecast/application/daily_dashboard.py tests/application/test_daily_dashboard.py
.venv/bin/mypy src/nba_forecast/application/daily_dashboard.py
```

Expected: all pass.

- [x] **Step 5: Commit Task 1**

```bash
git add src/nba_forecast/application/daily_dashboard.py \
  tests/application/test_daily_dashboard.py \
  docs/superpowers/plans/2026-06-16-daily-forecasts-dashboard.md
git commit -m "feat: load daily forecast reports"
```

## Task 2: Add Streamlit Daily Forecasts Tab

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_streamlit_app.py`

- [x] **Step 1: Write failing Streamlit tests**

Extend `tests/test_streamlit_app.py`:

```python
import json
from datetime import date, datetime, timezone

from nba_forecast.application import daily_dashboard
```

Add helpers:

```python
def _daily_report(predictions=None) -> daily_dashboard.DailyForecastReport:
    games = tuple(predictions or [])
    return daily_dashboard.DailyForecastReport(
        path=Path("artifacts/predictions/daily_predictions_2026-10-22.json"),
        prediction_date=date(2026, 10, 22),
        prediction_timestamp=datetime(2026, 10, 22, 12, tzinfo=timezone.utc),
        schedule_snapshot_at_utc=datetime(2026, 10, 22, 6, tzinfo=timezone.utc),
        total_schedule_rows=3,
        eligible_game_count=len(games),
        excluded_game_count=3 - len(games),
        games=games,
    )


def _daily_game() -> daily_dashboard.DailyForecastGame:
    return daily_dashboard.DailyForecastGame(
        game_id="0022600001",
        matchup_label="SAS at NYK",
        game_date=date(2026, 10, 22),
        season_type="Regular Season",
        model_version="2026-06-11-recent5-raw",
        feature_version="model-features-v1",
        home_team_abbreviation="NYK",
        away_team_abbreviation="SAS",
        home_win_probability=0.584,
        away_win_probability=0.416,
    )
```

Add tests:

```python
def test_streamlit_app_has_daily_forecasts_tab_first() -> None:
    app = _run_app()

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Daily Forecasts",
        "Model-Backed Historical Replay",
        "Assumption Lab",
        "Model Performance",
        "Methodology",
    ]


def test_daily_forecasts_tab_handles_missing_reports() -> None:
    app = _run_app()

    assert not app.exception
    daily_tab = app.tabs[0]
    assert any("Manual local workflow" in value for value in [m.value for m in daily_tab.markdown])
    assert any("No daily prediction reports found" in info.value for info in daily_tab.info)


def test_daily_forecasts_tab_renders_latest_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(daily_dashboard, "find_latest_daily_report", lambda _: Path("latest.json"))
    monkeypatch.setattr(daily_dashboard, "load_daily_report", lambda _: _daily_report([_daily_game()]))

    app = _run_app()

    daily_tab = app.tabs[0]
    assert not app.exception
    assert any(metric.label == "Eligible games" and metric.value == "1" for metric in daily_tab.metric)
    assert any(metric.label == "Predictions" and metric.value == "1" for metric in daily_tab.metric)
    assert any("SAS at NYK" in markdown.value for markdown in daily_tab.markdown)
    assert any("NYK 58.4%" in markdown.value for markdown in daily_tab.markdown)


def test_daily_forecasts_tab_renders_no_game_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(daily_dashboard, "find_latest_daily_report", lambda _: Path("latest.json"))
    monkeypatch.setattr(daily_dashboard, "load_daily_report", lambda _: _daily_report([]))

    app = _run_app()

    daily_tab = app.tabs[0]
    assert not app.exception
    assert any("No eligible games" in info.value for info in daily_tab.info)


def test_daily_forecasts_tab_shows_selected_date_missing_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(daily_dashboard, "find_latest_daily_report", lambda _: None)
    app = _run_app()

    app.date_input[0].set_value(date(2026, 10, 24)).run()
    app.button[0].click().run()

    daily_tab = app.tabs[0]
    assert not app.exception
    assert any("daily_predictions_2026-10-24.json" in warning.value for warning in daily_tab.warning)
```

Update existing tab index expectations:

- Model Performance tab index changes from `2` to `3`.
- Methodology tab index changes from `3` to `4`.
- Existing tests that count exact tab labels must include `Daily Forecasts`.

- [x] **Step 2: Run Streamlit tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/test_streamlit_app.py -v
```

Expected: failures because the new tab and rendering functions do not exist.

- [x] **Step 3: Implement Daily Forecasts tab**

Modify `streamlit_app.py`:

1. Add imports:

```python
from datetime import date

from nba_forecast.application import daily_dashboard
from nba_forecast.application.daily_dashboard import DailyForecastReport
```

2. Add constants:

```python
PREDICTIONS_DIR = Path("artifacts/predictions")
```

3. Add helpers near existing formatting helpers:

```python
def _format_percent(value: float) -> str:
    return f"{value:.1%}"


def _render_daily_missing_state(expected_path: Path | None = None) -> None:
    if expected_path is None:
        st.info(
            "No daily prediction reports found. Generate one with "
            "`nba-forecast predict-daily ... --output-dir .`."
        )
    else:
        st.warning(
            f"No report found at `{expected_path}`. Generate it with "
            "`nba-forecast predict-daily ... --prediction-date YYYY-MM-DD`."
        )


def _render_daily_report(report: DailyForecastReport) -> None:
    st.subheader(f"Daily Forecasts · {report.prediction_date.isoformat()}")
    st.caption(f"Report: `{report.path}`")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Eligible games", str(report.eligible_game_count))
    col2.metric("Predictions", str(report.prediction_count))
    col3.metric("Excluded rows", str(report.excluded_game_count))
    model_label = ", ".join(report.model_versions) if report.model_versions else "No predictions"
    col4.metric("Model", model_label)
    st.caption(
        "Prediction timestamp: "
        f"{report.prediction_timestamp.isoformat()} · Schedule snapshot: "
        f"{report.schedule_snapshot_at_utc.isoformat()}"
    )
    if not report.games:
        st.info("No eligible games were available for this report date.")
        return
    for game in report.games:
        st.markdown(
            f"""
            <div class="forecast-card">
              <div class="forecast-label">{game.season_type.upper()}</div>
              <div class="forecast-matchup">{game.matchup_label}</div>
              <div class="forecast-probability">
                {game.home_team_abbreviation} {_format_percent(game.home_win_probability)}
              </div>
              <div class="forecast-context">
                {game.away_team_abbreviation} {_format_percent(game.away_win_probability)}
                · Game date {game.game_date.isoformat()}
                · Model {game.model_version}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_daily_forecasts_tab() -> None:
    st.markdown(
        """
        <div class="notice">ℹ️ <strong>Manual local workflow.</strong>
        This tab reads generated local daily prediction reports. It is not a
        live feed, not market odds, and not betting advice.</div>
        """,
        unsafe_allow_html=True,
    )
    latest_path = daily_dashboard.find_latest_daily_report(PREDICTIONS_DIR)
    selected_date = st.date_input("Inspect report date", value=date.today())
    load_selected = st.button("Load date report")
    if load_selected:
        report_path = daily_dashboard.daily_report_path(PREDICTIONS_DIR, selected_date)
        if report_path.exists():
            _render_daily_report(daily_dashboard.load_daily_report(report_path))
        else:
            _render_daily_missing_state(report_path)
        return
    if latest_path is None:
        _render_daily_missing_state()
        return
    try:
        _render_daily_report(daily_dashboard.load_daily_report(latest_path))
    except daily_dashboard.DailyForecastReportError as error:
        st.error(f"Daily forecast report could not be loaded: {error}")
```

4. Change tab construction to:

```python
daily_tab, replay_tab, assumption_tab, performance_tab, methodology_tab = st.tabs(
    [
        "Daily Forecasts",
        "Model-Backed Historical Replay",
        "Assumption Lab",
        "Model Performance",
        "Methodology",
    ]
)

with daily_tab:
    _render_daily_forecasts_tab()
```

- [x] **Step 4: Run Streamlit tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/test_streamlit_app.py -v
.venv/bin/ruff check streamlit_app.py tests/test_streamlit_app.py
```

Expected: all pass.

- [x] **Step 5: Commit Task 2**

```bash
git add streamlit_app.py tests/test_streamlit_app.py \
  docs/superpowers/plans/2026-06-16-daily-forecasts-dashboard.md
git commit -m "feat: add daily forecasts dashboard tab"
```

## Task 3: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/runbook.md`
- Modify: `docs/architecture.md`

- [x] **Step 1: Update README**

In `README.md`, under `Manual Daily Schedule Predictions`, add:

```markdown
The Streamlit dashboard can inspect generated daily reports in the
**Daily Forecasts** tab. The tab is read-only: it does not fetch schedules,
score games, or write registry rows.
```

- [x] **Step 2: Update runbook**

In `docs/runbook.md`, after the `predict-daily` command section, add:

```markdown
View the generated report locally:

```bash
streamlit run streamlit_app.py
```

Open the **Daily Forecasts** tab. By default it loads the newest
`artifacts/predictions/daily_predictions_*.json` file. Use the date override
to inspect a specific report date. Missing and no-game dates are expected
operating states, not dashboard failures.
```
```

- [x] **Step 3: Update architecture**

In `docs/architecture.md`, under `Daily Schedule Prediction Flow`, add:

```markdown
The Streamlit Daily Forecasts tab is a read-only artifact viewer. It consumes
daily JSON reports and never calls `run_daily_predictions`, fetches NBA data,
or writes the registry.
```

- [x] **Step 4: Run docs-adjacent checks**

Run:

```bash
.venv/bin/pytest tests/test_streamlit_app.py tests/application/test_daily_dashboard.py -v
git diff --check
```

Expected: all pass.

- [x] **Step 5: Commit Task 3**

```bash
git add README.md docs/runbook.md docs/architecture.md \
  docs/superpowers/plans/2026-06-16-daily-forecasts-dashboard.md
git commit -m "docs: document daily forecasts dashboard"
```

## Task 4: Final Verification and Pull Request

**Files:**
- Modify: `docs/superpowers/plans/2026-06-16-daily-forecasts-dashboard.md`

- [x] **Step 1: Run full verification**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/pytest
git diff --check
```

Expected: all checks pass.

- [x] **Step 2: Review scope and hygiene**

Confirm:

- PR contains only loader service, dashboard tab, tests, docs, and plan/spec.
- `.omc/`, `.superpowers/`, `AGENTS.md`, local reports, data artifacts, and model artifacts are not staged.
- UI copy says manual/local and not live automation.
- Streamlit does not call schedule fetchers, model scoring, registry writes, or hosted persistence.

- [x] **Step 3: Commit final plan checkbox updates**

```bash
git add docs/superpowers/plans/2026-06-16-daily-forecasts-dashboard.md
git commit -m "docs: complete daily forecasts dashboard plan"
```

- [ ] **Step 4: Push and open Draft PR**

Use:

```text
Branch: feature/daily-forecasts-dashboard
Title: Add daily forecasts dashboard tab
```

PR description must summarize:

- latest-report-first UX
- read-only artifact boundary
- missing/no-game/malformed states
- tests and verification
- deferred automation/hosted persistence boundary
