# Model Performance / Methodology Dashboard Pages and Deployment Design

## Goal

Expand the Streamlit app from two tabs to four by adding **Model Performance**
and **Methodology** tabs that present already-documented results, apply a
cohesive app-wide visual theme, and prepare the app for deployment to
Streamlit Community Cloud using a small frozen data/model snapshot committed
to the repository.

This is a presentation, packaging, and deployment feature. It does not change
the frozen model, feature set, calibration, or measured performance, and it
introduces no new evaluation or computation.

## Background and Current State

- The frozen model bundle `2026-06-11-recent5-raw` (Logistic Regression,
  recent-five training window, Raw calibration) is final. Its untouched
  2025-26 test metrics are documented in `docs/model_card.md` and
  `docs/experiments.md`.
- `streamlit_app.py` currently defines two tabs via
  `replay_tab, assumption_tab = st.tabs(["Model-Backed Historical Replay",
  "Assumption Lab"])`. It reads `data/processed/games.parquet` (267 KB) and
  `artifacts/models/2026-06-11-recent5-raw.joblib` (4 KB), both gitignored
  pipeline outputs that do not exist in a fresh clone.
- The app already has a hand-rolled dark theme via an injected CSS block
  (`st.markdown(..., unsafe_allow_html=True)`): navy/blue background
  (`#07111f`), hero gradient (`#102a4c` → `#0b1728`), blue eyebrow accent
  (`#70b7ff`), and chart series colors `#4ba3ff` / `#ff9f43`. This is the
  theme the new design replaces, not a default Streamlit theme.
- The brief's Phase 5 describes a four-page dashboard (Today's Games /
  Playoff Simulator / Model Performance / Methodology). The existing two tabs
  already cover next-game and remaining-series probability (closer to
  "Today's Games") and hypothetical simulation ("Playoff Simulator"). This
  design adds the missing Model Performance and Methodology tabs without
  renaming or restructuring the existing two.

## Chosen Approach

### 1. Frozen Snapshot Assets

New directory `data/snapshots/2026-06-10/` containing:

- `games.parquet` — copy of the current `data/processed/games.parquet`
  (267 KB)
- `2026-06-11-recent5-raw.joblib` — copy of the current
  `artifacts/models/2026-06-11-recent5-raw.joblib` (4 KB)

These are the only two files the deployed app reads. Total committed size is
approximately 271 KB.

`streamlit_app.py`'s path constants change from:

```python
GAMES_PATH = Path("data/processed/games.parquet")
MODEL_PATH = Path("artifacts/models/2026-06-11-recent5-raw.joblib")
```

to:

```python
GAMES_PATH = Path("data/snapshots/2026-06-10/games.parquet")
MODEL_PATH = Path("data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib")
```

No `.gitignore` change is required. The existing ignore patterns
(`data/raw/`, `data/processed/`, `data/features/`, `data/predictions/`,
`artifacts/`) do not match `data/snapshots/`, so the new directory is tracked
normally.

A new ADR, `docs/decisions/0004-frozen-snapshot-deployment.md`, documents why
these two generated files are intentionally committed: their provenance (the
June 10/11 pipeline run already described in `docs/runbook.md`), that they are
static until a future deployment refresh, and that pipeline-generated files
under `data/processed/` and `artifacts/models/` remain gitignored and
independent of this snapshot.

### 2. App-Wide Visual Theme

New `.streamlit/config.toml`:

```toml
[theme]
base = "dark"
primaryColor = "#2DD4BF"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1C2128"
textColor = "#E6E6E6"
```

This is the "monochrome dark + teal accent" theme selected via the visual
companion, replacing the current hand-rolled navy/blue theme. Because the
existing injected CSS block hardcodes navy/blue colors, it must be updated to
the new palette so the two theme layers do not conflict:

| Element | Current | New |
|---|---|---|
| `.stApp` background | `#07111f` | `#0E1117` |
| `[data-testid="stHeader"]` background | `rgba(7,17,31,0.82)` | `rgba(14,17,23,0.82)` |
| `[data-testid="stMetric"]` background gradient | `linear-gradient(145deg, #10233d, #0c192b)` | `linear-gradient(145deg, #1C2128, #161A1F)` |
| `[data-testid="stMetric"]` border | `#284463` | `#2A3038` |
| `.hero` gradient | `linear-gradient(120deg, #102a4c, #0b1728 65%)` | `linear-gradient(120deg, #1C2128, #0E1117 65%)` |
| `.hero` border | `#31577e` | `#2A3038` |
| `.eyebrow` color | `#70b7ff` | `#2DD4BF` |
| Chart series colors (`_render_charts`) | `#4ba3ff` / `#ff9f43` | `#2DD4BF` / `#A78BFA` |
| Series-length bar color | `#70b7ff` | `#2DD4BF` |

The `.notice` warning-box colors (`#261d0c` / `#75561d` / `#ffd98a`, amber)
are unchanged — amber-for-warning is an independent convention and does not
clash with the teal accent.

This is the only styling change in scope. No per-tab custom styling is added
for the two new tabs; they inherit the app-wide theme and reuse the existing
`.notice`/`st.container(border=True)` patterns.

### 3. Model Performance Tab

New shared module `src/nba_forecast/application/model_performance.py`,
following the `application/fair_odds.py` pattern: a frozen dataclass plus a
pure builder function, with no file I/O and no new computation. Values are
transcribed from `docs/experiments.md` and `docs/model_card.md`.

```python
@dataclass(frozen=True)
class ModelPerformanceReport:
    final_metrics: pd.DataFrame
    baseline_comparison: pd.DataFrame
    training_window_comparison: pd.DataFrame
    calibration_selection: pd.DataFrame


def build_model_performance_report() -> ModelPerformanceReport: ...
```

Each field is a 1:1 transcription of one documented table:

- `final_metrics` (1 row) — "Final Test Metrics" /
  "Frozen 2025-26 Final Test Result": columns `Brier Score`, `Log Loss`,
  `ECE`, `ROC-AUC`, `Accuracy` with values `0.207254`, `0.601983`,
  `0.039914`, `0.732116`, `0.689431`.
- `baseline_comparison` (4 rows) — "Untouched 2025-26 Test Results":
  `Model`, `Brier Score`, `Log Loss`, `ROC-AUC`, `Accuracy` for Constant home
  rate, Season win percentage, Elo, and Logistic Regression.
- `training_window_comparison` (6 rows) — "Training Window and XGBoost
  Experiment" validation results: `Model`, `Training window`, `Train rows`,
  `Brier Score`, `Log Loss`, `ROC-AUC`, `Accuracy` for Logistic Regression and
  XGBoost across recent-3, recent-5, and decayed-full-history windows.
- `calibration_selection` (3 rows) — "Calibration Selection Results":
  `Method`, `Brier Score`, `Log Loss`, `ECE`, `ROC-AUC`, `Accuracy` for Raw,
  Isotonic, and Platt.

Streamlit layout (KPI Hero + collapsible sections, per the approved
visual-companion mockup):

- 5 `st.metric` columns from `final_metrics` (Brier Score, Log Loss, ECE,
  ROC-AUC, Accuracy) as the page header.
- Three `st.expander` sections, each containing one `st.dataframe` and a
  1-2 sentence interpretation already present in `docs/experiments.md`:
  - "Baseline Comparison (Untouched 2025-26 Test)" →
    `baseline_comparison`, with the documented 3.33% Brier-Score reduction
    versus Elo.
  - "Training Window & Model Comparison (2024-25 Validation)" →
    `training_window_comparison`, with the documented selection of
    recent-five Logistic Regression.
  - "Calibration Selection (2024-25 Validation, Second Half)" →
    `calibration_selection`, with the documented decision to retain Raw.

### 4. Methodology Tab

Static content tab, no new application module. Built directly in
`streamlit_app.py` from short excerpts of existing docs, each inside an
`st.expander` ending with a pointer to the full document:

- **Research Question** — the blockquote from `README.md`:
  > Using only information available before tip-off, how accurately can NBA
  > game win probabilities be predicted, and how can those probabilities
  > support playoff series simulations?
- **Architecture & Data Flow** — condensed description of the pipeline:
  raw NBA Stats cache → canonical games → point-in-time features → frozen
  model bundle → best-of-seven simulation, plus a one-line description of how
  Historical Replay scores both venue directions once at the cutoff. Points
  to `docs/architecture.md`.
- **Leakage Prevention** — the Core Rule ("Every model feature for a game must
  be reproducible using information available before that game's tip-off")
  plus 3-4 representative implemented controls (shift-by-one-game state,
  rolling windows null before history exists, `game_date < as_of_date`
  scheduled snapshots). Points to `docs/leakage_prevention.md`.
- **Model Limitations & Scope** — a representative subset of
  `docs/model_card.md`'s limitations (regular-season-only training with
  playoff calibration drift risk, no injuries/travel/roster continuity, fair
  odds are a deterministic transform and not market data, no betting advice).
  Points to `docs/model_card.md`.

### 5. Tab Wiring

`streamlit_app.py`'s tab declaration expands from two to four:

```python
replay_tab, assumption_tab, performance_tab, methodology_tab = st.tabs(
    ["Model-Backed Historical Replay", "Assumption Lab", "Model Performance", "Methodology"]
)
```

The bodies of `replay_tab` and `assumption_tab` are unchanged except for the
updated `GAMES_PATH`/`MODEL_PATH` constants (item 1) and the theme color
updates (item 2).

### 6. Streamlit Community Cloud Deployment

- The app entry point remains `streamlit_app.py` at the repo root.
- `streamlit_app.py` imports from the installed `nba_forecast` package, so
  the deployment environment must run `pip install .` (or equivalent) against
  the existing PEP 621 `pyproject.toml`. Streamlit Community Cloud supports
  `pyproject.toml`-based dependency resolution natively, so no separate
  `requirements.txt` is added. If Streamlit Cloud fails to resolve
  dependencies from `pyproject.toml` during the actual deploy, add a minimal
  `requirements.txt` mirroring `[project.dependencies]` as a fallback — this
  is not expected to be necessary and is not part of this design's scope
  unless it occurs.
- New `docs/runbook.md` section, "Deploy to Streamlit Community Cloud,"
  documenting the manual one-time steps Ryan performs: connect the GitHub
  repository at share.streamlit.io, select branch `main`, set the main file
  path to `streamlit_app.py`, deploy, then add the resulting public URL to
  `README.md`.
- Document that the deployed app reflects the static
  `data/snapshots/2026-06-10/` snapshot and does not update automatically;
  refreshing it is a manual snapshot-replacement step, out of scope here
  (Phase 6 automation is a separate future effort).

### 7. Documentation Updates

- **README.md** — update the Simulator Lab UI section to describe four tabs,
  add a "Live Demo" section with a placeholder for the Streamlit Cloud URL
  (to be filled in after Ryan's manual deploy), add a short disclosure that
  the deployed app uses the frozen `2026-06-10` snapshot (cross-referencing
  ADR 0004), and add this spec to the Documentation list.
- **docs/architecture.md** — add a subsection describing the Model
  Performance and Methodology tabs' data flow: both read only from
  `application/model_performance.py` constants and static doc-derived text,
  with zero runtime dependency on `data/snapshots/`, `data/processed/`, or
  `artifacts/models/` — unlike Historical Replay and Assumption Lab.
- **docs/runbook.md** — add the deployment section (item 6) and a short note
  about `.streamlit/config.toml` and the updated theme colors.
- **docs/decisions/0004-frozen-snapshot-deployment.md** — new ADR (item 1).

## Alternatives Considered

### Multipage app (`pages/` directory) instead of expanding tabs

Rejected for this iteration. The brief's four-page structure maps onto four
tabs within the existing single-file app without a navigation rewrite or
disruption to existing `AppTest` coverage. A multipage layout remains an
option for a future iteration if the app grows further.

### Recompute Model Performance tables at runtime from `data/features/games.parquet`

Rejected. This would require committing the 4.2 MB features parquet (versus
the 267 KB games parquet) and re-running evaluation/calibration code paths
inside the deployed app, duplicating logic already captured as static results
in `docs/experiments.md`. Static tables keep the deployed app's data
footprint at ~271 KB and its startup fast.

### GitHub Release asset + runtime download for snapshot data/model

Rejected. Adds a network dependency and download/cache logic for ~271 KB of
data, which is small enough to commit directly. Revisit only if a future
snapshot grows substantially larger.

### Calibration reliability curve instead of/in addition to the calibration selection table

Deferred. The brief's Model Performance page mentions a reliability/
calibration plot, but `docs/experiments.md` only contains tabular
calibration-selection results, not per-bin reliability data. Generating that
data would be new computation, which is out of scope. The calibration
selection table (including ECE) conveys the same decision narrative without
new computation.

### Theme alternatives (navy/orange accent, unmodified current theme)

Rejected via the visual companion. "Monochrome dark + teal accent" best fits
the existing high-contrast dark UI and avoids accent colors associated with
warning/risk (red) or specific team colors (orange).

## Testing Strategy

- `tests/application/test_model_performance.py`:
  `build_model_performance_report()` returns a `ModelPerformanceReport` whose
  four `DataFrame`s have the expected shapes and column names, and whose key
  cells match the documented values (final Brier Score `0.207254`, final
  ROC-AUC `0.732116`, Raw calibration-selection ECE `0.032448`, final ECE
  `0.039914`, etc.) — spot-checking representative cells per table rather than
  every cell.
- `tests/test_streamlit_app.py` (Streamlit `AppTest`):
  - the app renders four tabs with the expected labels
  - the Model Performance tab renders five `st.metric` widgets and three
    expanders with the expected headers
  - the Methodology tab renders four expanders with the expected headers
  - existing Historical Replay / Assumption Lab assertions continue to pass
    against the new `data/snapshots/2026-06-10/` paths
- `ruff check .`, `mypy src`, and `pytest` all pass.
- Manual local verification: `streamlit run streamlit_app.py` — all four tabs
  render without browser console errors, the dark/teal theme is applied
  consistently, and the Model Performance metrics/tables match
  `docs/experiments.md` and `docs/model_card.md` exactly.

## Documentation and Claims

Permitted claims:

> The Model Performance and Methodology tabs present the project's documented
> experiment results and frozen-model metrics (`docs/experiments.md`,
> `docs/model_card.md`); they do not compute new results.

> The deployed app uses a frozen data/model snapshot dated 2026-06-10/11 and
> does not reflect games played after that date until manually redeployed
> with a refreshed snapshot.

Prohibited claims:

- that the Model Performance tab performs live or on-demand evaluation
- that the deployed app's data is current or live
- any betting-related claims beyond what is already established for the
  fair-odds feature

## Success Criteria

1. `streamlit run streamlit_app.py` shows four tabs — Model-Backed Historical
   Replay, Assumption Lab, Model Performance, Methodology — all reading from
   `data/snapshots/2026-06-10/`.
2. The Model Performance tab shows the frozen model's five headline metrics
   as `st.metric` cards plus three expandable tables matching
   `docs/experiments.md` exactly.
3. The Methodology tab summarizes the research question, architecture/data
   flow, leakage prevention, and model limitations with links to the full
   docs.
4. The app-wide dark/teal theme is applied via `.streamlit/config.toml` and
   the existing injected CSS is updated to match, with no remaining
   navy/blue colors.
5. `data/snapshots/2026-06-10/` (~271 KB) is committed to git and documented
   via ADR 0004; `.gitignore` is unchanged.
6. `docs/runbook.md` documents the manual Streamlit Community Cloud deploy
   steps; `README.md` has a "Live Demo" placeholder section and a
   frozen-snapshot disclosure.
7. All tests (`ruff`, `mypy`, `pytest`) pass, including new tests for
   `model_performance.py` and the four-tab `AppTest`.
