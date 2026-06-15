# Model Performance / Methodology Dashboard Pages and Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `streamlit_app.py` from two tabs to four (adding Model
Performance and Methodology), apply a monochrome dark + teal theme, and make
the app deployable to Streamlit Community Cloud using a small committed data
snapshot.

**Architecture:** A new pure module `application/model_performance.py`
transcribes documented results from `docs/experiments.md` /
`docs/model_card.md` into `pandas.DataFrame`s for the Model Performance tab.
The Methodology tab is static markdown built directly in `streamlit_app.py`.
Both new tabs depend only on existing docs/constants — no new file I/O. The
existing two tabs are repointed at a committed `data/snapshots/2026-06-10/`
snapshot and restyled with a new teal accent theme.

**Tech Stack:** Python, Streamlit (`st.tabs`, `st.metric`, `st.expander`,
`st.dataframe`), pandas, pytest, Streamlit `AppTest`.

Spec: `docs/superpowers/specs/2026-06-13-dashboard-deployment-design.md`

---

## Task 1: Frozen data/model snapshot and updated path constants

**Files:**
- Create: `data/snapshots/2026-06-10/games.parquet`
- Create: `data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib`
- Modify: `streamlit_app.py:13-14`
- Modify: `tests/test_streamlit_app.py:50-59`

- [ ] **Step 1: Run the existing test suite as a baseline**

Run: `pytest tests/test_streamlit_app.py -v`
Expected: 3 passed

- [ ] **Step 2: Copy the frozen data and model files into a snapshot directory**

```bash
mkdir -p data/snapshots/2026-06-10
cp data/processed/games.parquet data/snapshots/2026-06-10/games.parquet
cp artifacts/models/2026-06-11-recent5-raw.joblib data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib
ls -la data/snapshots/2026-06-10/
```
Expected: `games.parquet` ~267 KB (273112 bytes) and
`2026-06-11-recent5-raw.joblib` ~4 KB (4047 bytes).

- [ ] **Step 3: Confirm `.gitignore` does not exclude the new directory**

```bash
git check-ignore -v data/snapshots/2026-06-10/games.parquet data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib
```
Expected: no output (nothing is ignored). If this prints a matching rule,
stop and report it instead of proceeding.

- [ ] **Step 4: Update the app's path constants**

In `streamlit_app.py`, change:

```python
GAMES_PATH = Path("data/processed/games.parquet")
MODEL_PATH = Path("artifacts/models/2026-06-11-recent5-raw.joblib")
```

to:

```python
GAMES_PATH = Path("data/snapshots/2026-06-10/games.parquet")
MODEL_PATH = Path("data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib")
```

- [ ] **Step 5: Update the existing test's monkeypatched path strings**

In `tests/test_streamlit_app.py`, inside
`test_streamlit_app_renders_actual_next_game_forecast_and_fair_odds`, change:

```python
            True
            if str(path)
            in {
                "data/processed/games.parquet",
                "artifacts/models/2026-06-11-recent5-raw.joblib",
            }
            else original_exists(path)
```

to:

```python
            True
            if str(path)
            in {
                "data/snapshots/2026-06-10/games.parquet",
                "data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib",
            }
            else original_exists(path)
```

- [ ] **Step 6: Run the test suite again**

Run: `pytest tests/test_streamlit_app.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add data/snapshots/2026-06-10/games.parquet data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib streamlit_app.py tests/test_streamlit_app.py
git commit -m "feat: read app data and model from frozen 2026-06-10 snapshot"
```

---

## Task 2: Monochrome dark + teal theme

**Files:**
- Create: `.streamlit/config.toml`
- Modify: `streamlit_app.py:22-52` (injected CSS)
- Modify: `streamlit_app.py:77-80` and `streamlit_app.py:108` (chart colors)

- [ ] **Step 1: Create the Streamlit theme config**

Create `.streamlit/config.toml`:

```toml
[theme]
base = "dark"
primaryColor = "#2DD4BF"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1C2128"
textColor = "#E6E6E6"
```

- [ ] **Step 2: Update the injected CSS block to the teal palette**

In `streamlit_app.py`, in the `st.markdown("""<style> ... </style>""", ...)`
block, change:

```python
    .stApp { background: #07111f; color: #f7fafc; }
    [data-testid="stHeader"] { background: rgba(7, 17, 31, 0.82); }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #10233d, #0c192b);
        border: 1px solid #284463;
        border-radius: 16px;
        padding: 18px;
    }
    .hero {
        padding: 24px 28px;
        border-radius: 20px;
        background: linear-gradient(120deg, #102a4c, #0b1728 65%);
        border: 1px solid #31577e;
        margin-bottom: 18px;
    }
    .eyebrow { color: #70b7ff; font-weight: 700; letter-spacing: .12em; }
```

to:

```python
    .stApp { background: #0E1117; color: #f7fafc; }
    [data-testid="stHeader"] { background: rgba(14, 17, 23, 0.82); }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #1C2128, #161A1F);
        border: 1px solid #2A3038;
        border-radius: 16px;
        padding: 18px;
    }
    .hero {
        padding: 24px 28px;
        border-radius: 20px;
        background: linear-gradient(120deg, #1C2128, #0E1117 65%);
        border: 1px solid #2A3038;
        margin-bottom: 18px;
    }
    .eyebrow { color: #2DD4BF; font-weight: 700; letter-spacing: .12em; }
```

Leave the `.notice { ... }` block (amber warning colors) unchanged.

- [ ] **Step 3: Update chart series colors in `_render_charts`**

In `streamlit_app.py`, change:

```python
    team_colors = alt.Scale(
        domain=[team_a, team_b],
        range=["#4ba3ff", "#ff9f43"],
    )
```

to:

```python
    team_colors = alt.Scale(
        domain=[team_a, team_b],
        range=["#2DD4BF", "#A78BFA"],
    )
```

And change:

```python
            .mark_bar(color="#70b7ff", cornerRadiusEnd=4)
```

to:

```python
            .mark_bar(color="#2DD4BF", cornerRadiusEnd=4)
```

- [ ] **Step 4: Run the test suite**

Run: `pytest tests/test_streamlit_app.py -v`
Expected: 3 passed (color changes do not affect existing assertions)

- [ ] **Step 5: Manually verify the theme locally**

```bash
streamlit run streamlit_app.py
```
Open the printed local URL and confirm: dark `#0E1117` background, teal
`#2DD4BF` accents on the eyebrow label, metric card borders, and chart series,
no leftover navy/blue (`#07111f`, `#102a4c`, `#4ba3ff`, `#70b7ff`,
`#ff9f43`). Stop the server with Ctrl-C when done.

- [ ] **Step 6: Commit**

```bash
git add .streamlit/config.toml streamlit_app.py
git commit -m "feat: apply monochrome dark and teal dashboard theme"
```

---

## Task 3: `model_performance.py` data module (TDD)

**Files:**
- Create: `src/nba_forecast/application/model_performance.py`
- Test: `tests/application/test_model_performance.py`

- [ ] **Step 1: Write the failing test**

Create `tests/application/test_model_performance.py`:

```python
import pytest

from nba_forecast.application.model_performance import (
    ModelPerformanceReport,
    build_model_performance_report,
)


def test_final_metrics_match_frozen_model_card() -> None:
    report = build_model_performance_report()

    assert isinstance(report, ModelPerformanceReport)
    assert list(report.final_metrics.columns) == [
        "Brier Score",
        "Log Loss",
        "ECE",
        "ROC-AUC",
        "Accuracy",
    ]
    assert len(report.final_metrics) == 1
    final = report.final_metrics.iloc[0]
    assert final["Brier Score"] == pytest.approx(0.207254)
    assert final["Log Loss"] == pytest.approx(0.601983)
    assert final["ECE"] == pytest.approx(0.039914)
    assert final["ROC-AUC"] == pytest.approx(0.732116)
    assert final["Accuracy"] == pytest.approx(0.689431)


def test_baseline_comparison_matches_untouched_test_results() -> None:
    report = build_model_performance_report()

    assert list(report.baseline_comparison["Model"]) == [
        "Constant home rate",
        "Season win percentage",
        "Elo",
        "Logistic Regression",
    ]
    logreg = report.baseline_comparison.iloc[-1]
    assert logreg["Brier Score"] == pytest.approx(0.20649)
    assert logreg["ROC-AUC"] == pytest.approx(0.73357)


def test_training_window_comparison_selects_recent_five_logistic_regression() -> None:
    report = build_model_performance_report()

    assert len(report.training_window_comparison) == 6
    best = report.training_window_comparison.iloc[0]
    assert best["Model"] == "Logistic Regression"
    assert best["Training window"] == "Recent 5"
    assert best["Brier Score"] == pytest.approx(0.208594)


def test_calibration_selection_retains_raw() -> None:
    report = build_model_performance_report()

    assert list(report.calibration_selection["Method"]) == ["Raw", "Isotonic", "Platt"]
    raw = report.calibration_selection.iloc[0]
    assert raw["Brier Score"] == pytest.approx(0.201537)
    assert raw["ECE"] == pytest.approx(0.032448)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/application/test_model_performance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named
'nba_forecast.application.model_performance'`

- [ ] **Step 3: Implement the module**

Create `src/nba_forecast/application/model_performance.py`:

```python
"""Static model performance tables transcribed from documented results.

Values mirror docs/experiments.md and docs/model_card.md. This module
performs no computation and reads no files; it exists so the Streamlit Model
Performance tab and its tests share one source of the documented numbers.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ModelPerformanceReport:
    """Documented frozen-model and experiment-history tables."""

    final_metrics: pd.DataFrame
    baseline_comparison: pd.DataFrame
    training_window_comparison: pd.DataFrame
    calibration_selection: pd.DataFrame


def build_model_performance_report() -> ModelPerformanceReport:
    """Return the documented experiment and final-model result tables."""
    final_metrics = pd.DataFrame(
        [
            {
                "Brier Score": 0.207254,
                "Log Loss": 0.601983,
                "ECE": 0.039914,
                "ROC-AUC": 0.732116,
                "Accuracy": 0.689431,
            }
        ]
    )

    baseline_comparison = pd.DataFrame(
        [
            {
                "Model": "Constant home rate",
                "Brier Score": 0.24715,
                "Log Loss": 0.68745,
                "ROC-AUC": 0.50000,
                "Accuracy": 0.55447,
            },
            {
                "Model": "Season win percentage",
                "Brier Score": 0.22179,
                "Log Loss": 0.69051,
                "ROC-AUC": 0.71839,
                "Accuracy": 0.66992,
            },
            {
                "Model": "Elo",
                "Brier Score": 0.21360,
                "Log Loss": 0.61797,
                "ROC-AUC": 0.72531,
                "Accuracy": 0.66585,
            },
            {
                "Model": "Logistic Regression",
                "Brier Score": 0.20649,
                "Log Loss": 0.60051,
                "ROC-AUC": 0.73357,
                "Accuracy": 0.68293,
            },
        ]
    )

    training_window_comparison = pd.DataFrame(
        [
            {
                "Model": "Logistic Regression",
                "Training window": "Recent 5",
                "Train rows": 5829,
                "Brier Score": 0.208594,
                "Log Loss": 0.603709,
                "ROC-AUC": 0.730156,
                "Accuracy": 0.678049,
            },
            {
                "Model": "Logistic Regression",
                "Training window": "Decayed full history",
                "Train rows": 10749,
                "Brier Score": 0.208670,
                "Log Loss": 0.603964,
                "ROC-AUC": 0.730329,
                "Accuracy": 0.680488,
            },
            {
                "Model": "Logistic Regression",
                "Training window": "Recent 3",
                "Train rows": 3690,
                "Brier Score": 0.208736,
                "Log Loss": 0.604207,
                "ROC-AUC": 0.730118,
                "Accuracy": 0.678862,
            },
            {
                "Model": "XGBoost",
                "Training window": "Decayed full history",
                "Train rows": 10749,
                "Brier Score": 0.211099,
                "Log Loss": 0.609608,
                "ROC-AUC": 0.723284,
                "Accuracy": 0.653659,
            },
            {
                "Model": "XGBoost",
                "Training window": "Recent 3",
                "Train rows": 3690,
                "Brier Score": 0.211292,
                "Log Loss": 0.610053,
                "ROC-AUC": 0.722403,
                "Accuracy": 0.655285,
            },
            {
                "Model": "XGBoost",
                "Training window": "Recent 5",
                "Train rows": 5829,
                "Brier Score": 0.211721,
                "Log Loss": 0.611173,
                "ROC-AUC": 0.721448,
                "Accuracy": 0.672358,
            },
        ]
    )

    calibration_selection = pd.DataFrame(
        [
            {
                "Method": "Raw",
                "Brier Score": 0.201537,
                "Log Loss": 0.588339,
                "ECE": 0.032448,
                "ROC-AUC": 0.750629,
                "Accuracy": 0.689431,
            },
            {
                "Method": "Isotonic",
                "Brier Score": 0.204388,
                "Log Loss": 0.630123,
                "ECE": 0.037552,
                "ROC-AUC": 0.744941,
                "Accuracy": 0.682927,
            },
            {
                "Method": "Platt",
                "Brier Score": 0.205197,
                "Log Loss": 0.598572,
                "ECE": 0.053973,
                "ROC-AUC": 0.750629,
                "Accuracy": 0.686179,
            },
        ]
    )

    return ModelPerformanceReport(
        final_metrics=final_metrics,
        baseline_comparison=baseline_comparison,
        training_window_comparison=training_window_comparison,
        calibration_selection=calibration_selection,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/application/test_model_performance.py -v`
Expected: 4 passed

- [ ] **Step 5: Run lint and type checks**

Run: `ruff check . && mypy src`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add src/nba_forecast/application/model_performance.py tests/application/test_model_performance.py
git commit -m "feat: add model performance report data module"
```

---

## Task 4: Model Performance and Methodology tabs

**Files:**
- Modify: `streamlit_app.py:9-14` (imports)
- Modify: `streamlit_app.py:66-68` (tab declaration)
- Modify: `streamlit_app.py` (end of file, after the `assumption_tab` block)

- [ ] **Step 1: Add the import**

In `streamlit_app.py`, change:

```python
from nba_forecast.application.series_replay import SeriesReplayInput, run_series_replay
from nba_forecast.application.simulator_lab import SimulatorLabInput, run_simulator_lab
from nba_forecast.models.artifacts import load_model_bundle
```

to:

```python
from nba_forecast.application.model_performance import build_model_performance_report
from nba_forecast.application.series_replay import SeriesReplayInput, run_series_replay
from nba_forecast.application.simulator_lab import SimulatorLabInput, run_simulator_lab
from nba_forecast.models.artifacts import load_model_bundle
```

- [ ] **Step 2: Expand the tab declaration to four tabs**

Change:

```python
replay_tab, assumption_tab = st.tabs(
    ["Model-Backed Historical Replay", "Assumption Lab"]
)
```

to:

```python
replay_tab, assumption_tab, performance_tab, methodology_tab = st.tabs(
    [
        "Model-Backed Historical Replay",
        "Assumption Lab",
        "Model Performance",
        "Methodology",
    ]
)
```

- [ ] **Step 3: Add the Model Performance tab body**

At the end of `streamlit_app.py`, after the closing of the `assumption_tab`
block (after the `st.expander("Methodology and current limitation")` block),
add:

```python

with performance_tab:
    st.markdown(
        """
        <div class="notice"><strong>Model Performance.</strong> These tables
        mirror the documented experiment history in
        <code>docs/experiments.md</code> and the frozen model card in
        <code>docs/model_card.md</code>. No new evaluation is computed here.
        </div>
        """,
        unsafe_allow_html=True,
    )

    report = build_model_performance_report()
    final = report.final_metrics.iloc[0]

    st.subheader("Frozen Model: Final 2025-26 Test Result")
    final_metrics = st.columns(5)
    final_metrics[0].metric("Brier Score", f"{final['Brier Score']:.4f}")
    final_metrics[1].metric("Log Loss", f"{final['Log Loss']:.4f}")
    final_metrics[2].metric("ECE", f"{final['ECE']:.4f}")
    final_metrics[3].metric("ROC-AUC", f"{final['ROC-AUC']:.4f}")
    final_metrics[4].metric("Accuracy", f"{final['Accuracy']:.4f}")

    with st.expander("Baseline Comparison (Untouched 2025-26 Test)"):
        st.dataframe(report.baseline_comparison, hide_index=True, width="stretch")
        st.caption(
            "Logistic Regression reduced Brier Score by 3.33% versus Elo on "
            "the untouched 2025-26 regular season."
        )

    with st.expander("Training Window & Model Comparison (2024-25 Validation)"):
        st.dataframe(
            report.training_window_comparison, hide_index=True, width="stretch"
        )
        st.caption(
            "Recent-five Logistic Regression was selected for calibration: "
            "the lowest validation Brier Score and Log Loss across all "
            "compared windows and model classes."
        )

    with st.expander("Calibration Selection (2024-25 Validation, Second Half)"):
        st.dataframe(
            report.calibration_selection, hide_index=True, width="stretch"
        )
        st.caption(
            "Raw probabilities were retained: both Platt and Isotonic "
            "calibration worsened Brier Score and Log Loss on the later "
            "validation half."
        )

with methodology_tab:
    st.markdown(
        """
        <div class="notice"><strong>Methodology.</strong> These summaries link
        to the full documentation; nothing here changes the frozen model or
        its measured results.</div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Research Question"):
        st.markdown(
            """
> Using only information available before tip-off, how accurately can NBA
> game win probabilities be predicted, and how can those probabilities
> support playoff series simulations?

See `README.md` for the full project overview.
            """
        )

    with st.expander("Architecture & Data Flow"):
        st.markdown(
            """
```text
NBA Stats raw cache -> canonical games -> point-in-time features
    -> frozen model bundle -> best-of-seven simulation
```

Historical Replay scores both possible home/away venue directions once at the
declared cutoff and freezes those probabilities for the remaining-series
simulation. See `docs/architecture.md` for the full component diagrams.
            """
        )

    with st.expander("Leakage Prevention"):
        st.markdown(
            """
**Core rule:** every model feature for a game must be reproducible using
information available before that game's tip-off.

- Team state is shifted by one game before any rolling or Elo aggregation.
- Rolling windows (5/10/20 games) remain null until enough prior games exist.
- Scheduled-matchup snapshots include only completed games with
  `game_date < as_of_date`.

See `docs/leakage_prevention.md` for the complete control list and
mutation-based regression tests.
            """
        )

    with st.expander("Model Limitations & Scope"):
        st.markdown(
            """
- Trained and evaluated on regular-season games; playoff inference uses the
  same features but has no measured playoff-accuracy claim.
- Does not include injuries, player availability, travel, or roster
  continuity.
- Model-implied fair odds are a deterministic probability transform, not
  sportsbook prices, market data, or betting advice.
- This project does not provide betting advice and does not claim
  profitability.

See `docs/model_card.md` for the complete limitations list.
            """
        )
```

- [ ] **Step 4: Run the app and check for exceptions**

Run: `pytest tests/test_streamlit_app.py -v`
Expected: 3 passed (existing tests still pass; new tabs are not yet asserted)

- [ ] **Step 5: Run lint and type checks**

Run: `ruff check . && mypy src`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: add Model Performance and Methodology dashboard tabs"
```

---

## Task 5: AppTest coverage for the new tabs

**Files:**
- Modify: `tests/test_streamlit_app.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_streamlit_app.py`:

```python
def test_streamlit_app_has_four_tabs() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Model-Backed Historical Replay",
        "Assumption Lab",
        "Model Performance",
        "Methodology",
    ]


def test_model_performance_tab_renders_documented_metrics_and_tables() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()

    performance_tab = app.tabs[2]
    metric_labels = [metric.label for metric in performance_tab.metric]
    assert metric_labels == [
        "Brier Score",
        "Log Loss",
        "ECE",
        "ROC-AUC",
        "Accuracy",
    ]
    assert performance_tab.metric[0].value == "0.2073"
    assert performance_tab.metric[3].value == "0.7321"

    expander_labels = [expander.label for expander in performance_tab.expander]
    assert expander_labels == [
        "Baseline Comparison (Untouched 2025-26 Test)",
        "Training Window & Model Comparison (2024-25 Validation)",
        "Calibration Selection (2024-25 Validation, Second Half)",
    ]


def test_methodology_tab_renders_expected_sections() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()

    methodology_tab = app.tabs[3]
    expander_labels = [expander.label for expander in methodology_tab.expander]
    assert expander_labels == [
        "Research Question",
        "Architecture & Data Flow",
        "Leakage Prevention",
        "Model Limitations & Scope",
    ]
```

- [ ] **Step 2: Run the new tests**

Run: `pytest tests/test_streamlit_app.py -v`
Expected: 6 passed

If `performance_tab.metric[0].value` or `[3].value` does not match
`"0.2073"` / `"0.7321"`, print the actual value
(`print(performance_tab.metric[0].value)`) and adjust the assertion to the
actual formatted string — the underlying numeric values are fixed by Task 3's
test and must not change.

- [ ] **Step 3: Run the full test suite, lint, and type checks**

Run: `pytest && ruff check . && mypy src`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_streamlit_app.py
git commit -m "test: cover Model Performance and Methodology tabs"
```

---

## Task 6: ADR 0004 — frozen snapshot deployment

**Files:**
- Create: `docs/decisions/0004-frozen-snapshot-deployment.md`

- [ ] **Step 1: Write the ADR**

Create `docs/decisions/0004-frozen-snapshot-deployment.md`:

```markdown
# ADR 0004: Frozen Snapshot Data and Model Artifacts for Deployment

## Status

Accepted on 2026-06-13.

## Context

`streamlit_app.py` reads `data/processed/games.parquet` and a frozen model
bundle from `artifacts/models/`. Both are pipeline-generated outputs excluded
from Git by `.gitignore`, so they do not exist in a fresh clone or in the
environment Streamlit Community Cloud builds from a GitHub repository.

Deploying the app therefore requires some copy of these two files to be
present at runtime. The combined size of the files the app needs is small:
`games.parquet` is 267 KB and the `2026-06-11-recent5-raw.joblib` model bundle
is 4 KB, for a total of approximately 271 KB.

## Decision

Commit a small frozen snapshot under `data/snapshots/2026-06-10/`, containing:

- `games.parquet` — a copy of the verified `data/processed/games.parquet` as
  of the June 10, 2026 processed-data refresh described in `docs/runbook.md`
- `2026-06-11-recent5-raw.joblib` — a copy of the frozen
  `2026-06-11-recent5-raw` model bundle described in `docs/model_card.md`

`streamlit_app.py` reads `GAMES_PATH` and `MODEL_PATH` from this snapshot
directory instead of from `data/processed/` or `artifacts/models/`.

`data/snapshots/` is not covered by any existing `.gitignore` pattern
(`data/raw/`, `data/processed/`, `data/features/`, `data/predictions/`,
`artifacts/`), so no `.gitignore` change is required. Pipeline-generated files
under `data/processed/` and `artifacts/models/` remain gitignored and
independent of this snapshot; regenerating them does not change the deployed
app until the snapshot is intentionally refreshed.

## Alternatives Considered

### GitHub Release asset with runtime download

Rejected. Adds a network dependency and download/cache logic to the deployed
app for ~271 KB of data, which is small enough to commit directly.

### Recompute from `data/features/games.parquet` at deploy time

Rejected. The features parquet is 4.2 MB (versus 267 KB for the games
parquet), and the app would need to re-run evaluation/calibration code paths
that already have documented, frozen results in `docs/experiments.md`.

## Consequences

- The deployed app's data and model are static and dated 2026-06-10/11 until
  someone replaces the files under `data/snapshots/2026-06-10/` and
  redeploys.
- A future automated refresh (Phase 6) can write a new dated snapshot
  directory and update `GAMES_PATH`/`MODEL_PATH` without changing this
  decision's structure.
- README and the Streamlit app must disclose that the deployed instance
  reflects this frozen snapshot, not live data.
```

- [ ] **Step 2: Commit**

```bash
git add docs/decisions/0004-frozen-snapshot-deployment.md
git commit -m "docs: record frozen snapshot deployment decision"
```

---

## Task 7: Architecture doc update

**Files:**
- Modify: `docs/architecture.md` (append new section)

- [ ] **Step 1: Append a new section**

At the end of `docs/architecture.md`, after the "Model-Backed Series Replay
Flow" section, add:

```markdown

## Model Performance and Methodology Tabs

```text
docs/experiments.md + docs/model_card.md (documented results)
        |
        v
application/model_performance.py (static constants)
        |
        v
Streamlit Model Performance tab (st.metric + st.dataframe)
```

`application/model_performance.py` and the Methodology tab's static text have
no runtime dependency on `data/snapshots/`, `data/processed/`, or
`artifacts/models/`. Unlike Historical Replay and Assumption Lab, these two
tabs render identically whether or not the frozen snapshot is present.
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: describe model performance and methodology tab data flow"
```

---

## Task 8: Runbook update — theme and deployment

**Files:**
- Modify: `docs/runbook.md` (insert sections after "Run the Simulator Lab UI")

- [ ] **Step 1: Insert "Theme" and "Deploy to Streamlit Community Cloud" sections**

In `docs/runbook.md`, immediately before the `## Failure Recovery` section
(which currently follows the "Run the Simulator Lab UI" section), insert:

```markdown
## Theme

`.streamlit/config.toml` sets a monochrome dark theme with a teal (`#2DD4BF`)
accent. The injected CSS in `streamlit_app.py` is hand-tuned to match this
palette; if either changes, update the other so the app does not mix two
color schemes.

## Deploy to Streamlit Community Cloud

The deployed app reads `data/snapshots/2026-06-10/games.parquet` and
`data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib`, which are committed
to the repository (see ADR 0004). No additional data setup is required for
deployment.

One-time manual steps (performed by the repository owner):

1. Sign in at <https://share.streamlit.io> with the GitHub account that owns
   this repository.
2. Click "New app" and select this repository and the `main` branch.
3. Set the main file path to `streamlit_app.py`.
4. Deploy. Streamlit Community Cloud installs dependencies from
   `pyproject.toml`.
5. Once the app is live, add its public URL to the "Live Demo" section of
   `README.md`.

The deployed app reflects only the static `data/snapshots/2026-06-10/`
snapshot. Refreshing it requires replacing the files under that directory with
a newer pipeline run and redeploying; this is a manual step until Phase 6
automation exists.
```

- [ ] **Step 2: Commit**

```bash
git add docs/runbook.md
git commit -m "docs: add theme and Streamlit Community Cloud deploy steps"
```

---

## Task 9: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a "Live Demo" section after "Research Question"**

In `README.md`, immediately after the "Research Question" section (after the
blockquote, before "## Planned Product"), insert:

```markdown
## Live Demo

The dashboard is not yet deployed. Once deployed to Streamlit Community Cloud
(see `docs/runbook.md`), this section will link to the public app URL.

The deployed app will use the frozen `data/snapshots/2026-06-10/` data and
model snapshot (see
[ADR 0004](docs/decisions/0004-frozen-snapshot-deployment.md)) and will not
reflect games played after June 10-11, 2026 until manually redeployed with a
refreshed snapshot.
```

- [ ] **Step 2: Rename and expand the "Simulator Lab UI" section**

Change the section heading and body from:

```markdown
## Simulator Lab UI

The first interactive product surface is available locally:

```bash
source .venv/bin/activate
streamlit run streamlit_app.py
```

The app provides two modes:

- **Model-Backed Historical Replay:** reconstructs an observed playoff series
  at a declared cutoff, displays the actual next-game forecast, and simulates
  the remaining games.
- **Assumption Lab:** lets users edit hypothetical probabilities, simulation
  count, and random seed.

The two modes are clearly separated so manually entered assumptions are never
presented as observed historical evidence.
```

to:

```markdown
## Dashboard UI

The interactive product surface is available locally:

```bash
source .venv/bin/activate
streamlit run streamlit_app.py
```

The app provides four tabs:

- **Model-Backed Historical Replay:** reconstructs an observed playoff series
  at a declared cutoff, displays the actual next-game forecast, and simulates
  the remaining games.
- **Assumption Lab:** lets users edit hypothetical probabilities, simulation
  count, and random seed.
- **Model Performance:** presents the frozen model's final test metrics and
  the documented baseline, training-window, and calibration-selection
  experiment tables from `docs/experiments.md`.
- **Methodology:** summarizes the research question, architecture, leakage
  prevention, and model limitations, linking to the full documentation.

The first two tabs are clearly separated so manually entered assumptions are
never presented as observed historical evidence. The latter two tabs are
static and present only already-documented results.
```

- [ ] **Step 3: Add this spec to the Documentation list**

In `README.md`, in the `## Documentation` list, after the line:

```markdown
- [Model-backed series replay design](docs/superpowers/specs/2026-06-11-model-backed-series-replay-design.md)
```

add:

```markdown
- [Dashboard deployment and performance/methodology design](docs/superpowers/specs/2026-06-13-dashboard-deployment-design.md)
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: describe four-tab dashboard and add live demo placeholder"
```

---

## Task 10: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `pytest -v`
Expected: all tests pass, including the 4 new `test_model_performance.py`
tests and the 3 new `test_streamlit_app.py` tests (109 total, up from 102).

- [ ] **Step 2: Run lint and type checks**

Run: `ruff check . && mypy src`
Expected: no errors

- [ ] **Step 3: Manually verify the full app**

```bash
streamlit run streamlit_app.py
```

Confirm in the browser:
- Four tabs render: Model-Backed Historical Replay, Assumption Lab, Model
  Performance, Methodology.
- Model Performance shows 5 metric cards (Brier Score 0.2073, Log Loss
  0.6020, ECE 0.0399, ROC-AUC 0.7321, Accuracy 0.6894) and 3 expanders with
  tables matching `docs/experiments.md`.
- Methodology shows 4 expanders with the expected content.
- The teal/dark theme is consistent across all four tabs with no leftover
  navy/blue colors.
- Historical Replay and Assumption Lab still work as before (using the
  snapshot data).

Stop the server with Ctrl-C when done.

- [ ] **Step 4: Confirm git status is clean**

Run: `git status`
Expected: working tree clean, all changes committed across Tasks 1-9.
