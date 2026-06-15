# NBA Forecast Lab Dashboard — Portfolio Polish Design

## Status

Proposed on 2026-06-15.

## Context

The dashboard (`streamlit_app.py`) was prepared for Streamlit Community Cloud
deployment per `docs/superpowers/plans/2026-06-13-dashboard-deployment.md`,
adding the Model Performance and Methodology tabs and a dark/teal theme.

After viewing the live app, feedback identified three gaps, all relevant
because the primary use case is a portfolio/job-search artifact that should
also be genuinely usable by NBA fans (including the author):

1. **Hero lacks impact.** The first screen reads like a generic Streamlit
   template — it doesn't communicate "leakage-safe forecasting model with
   measured results" or show any real prediction.
2. **Information is scattered.** Four tabs plus many expanders mean there is
   no single "headline" takeaway visible without interaction.
3. **Visual finishing feels default.** Charts likely render with Altair's
   default light theme against the dark page background; notice boxes and
   the page have no footer/attribution.

## Goals

- Communicate "leakage-safe NBA forecasting model with measured results"
  within the first screen.
- Surface a real model prediction in the hero — not just abstract metrics —
  so the page has standalone value for NBA fans.
- Avoid generic "AI-dashboard" tropes: keep tone factual/technical, matching
  the existing methodology docs.

## Non-goals

- No restructuring of the four-tab layout (Historical Replay, Assumption Lab,
  Model Performance, Methodology).
- No new data pipeline, model, or snapshot changes.
- No mobile-specific redesign.

## Design

### 1. Hero "Headline Forecast"

**`FEATURED_SERIES` constant.** Extract the Replay tab's current default
scenario (currently hardcoded as widget `value=` literals) into a
module-level constant:

```python
FEATURED_SERIES = SeriesReplayInput(
    as_of_date=pd.Timestamp("2026-06-11"),
    next_game_date=pd.Timestamp("2026-06-13"),
    season_id="42025",
    season_type="Playoffs",
    season_key="2025-26",
    team_a_id=1610612759,
    team_a_abbreviation="SAS",
    team_b_id=1610612752,
    team_b_abbreviation="NYK",
    simulations=10_000,
    seed=2026,
)
```

The Replay tab's input widgets read their defaults from `FEATURED_SERIES`
fields instead of duplicated literals, so the hero and the tab's default
scenario can never drift apart.

**Data flow:**

```text
data/snapshots/2026-06-10/games.parquet  --+
data/snapshots/2026-06-10/*.joblib       --+--> run_series_replay(FEATURED_SERIES)
                                                       (cached: st.cache_data /
                                                        st.cache_resource)
                                                  |
                                                  v
                                       next_game_forecast
                                       (win probability, fair odds)
                                                  |
                                                  v
                              Hero "FEATURED HISTORICAL FORECAST" card
```

Computed once near the top of the script and cached so it does not re-run on
every Streamlit rerun (every widget interaction reruns the whole script):
- `st.cache_data` for reading `games.parquet` and for the
  `run_series_replay` result (keyed on the snapshot file paths).
- `st.cache_resource` for `load_model_bundle` (non-serializable sklearn
  pipeline object).

**Hero layout (approved direction — "Headline Forecast"):**

- Eyebrow: `NBA FORECAST LAB` (unchanged).
- H1: "Leakage-Safe NBA Game Forecasting" (revised from "Historical Replay &
  Best-of-7 Simulator" — more descriptive for a first-time visitor).
- Tagline: existing copy, lightly trimmed.
- **FEATURED HISTORICAL FORECAST card**: `FEATURED_SERIES` team
  abbreviations, the historical next game's home win probability, and
  model-implied fair odds (decimal + American via the existing
  `_format_american_odds`). It is explicitly labeled as a frozen historical
  snapshot, not a live/current prediction.
- **Badge row**: separate factual badges for the frozen model final-test
  Brier Score (`0.2073`) and the earlier baseline Logistic Regression's
  measured Brier improvement versus Elo (`3.33%`), plus a GitHub link badge.
  The two performance claims must not be combined as though the frozen model
  itself produced the `3.33%` improvement.

**Fallback (snapshot missing, e.g. local dev before the pipeline has run):**
if `GAMES_PATH` / `MODEL_PATH` do not exist, the hero renders without the
featured historical forecast card and badge row — same hero copy, no broken
state, no warning clutter in the hero itself (the existing Replay-tab warning
still covers that case when the user clicks "Run historical replay").

### 2. Visual polish

1. **Altair dark theme.** Register a custom Altair theme (`alt.themes.register`
   + `alt.themes.enable`) with dark background (`#0E1117`), light text
   (`#E6E6E6`), and gridlines (`#2A3038`) matching the page palette. Enabled
   once globally so both charts in `_render_charts` pick it up without
   per-chart changes.
2. **Notice box icons.** Prefix each existing `.notice` block with a semantic
   icon: ℹ️ for informational notices (Historical Replay, Model Performance,
   Methodology tabs) and ⚠️ for the Assumption Lab's "hypothetical, not a
   real prediction" warning.
3. **Footer.** A minimal footer after the tab block: GitHub repo link
   (`https://github.com/seungminnam/nba-forecast-lab`) and "Data snapshot:
   2026-06-10" (reinforces the disclosure required by ADR 0004). Plain
   text/link — no "Made with Streamlit" attribution.

### 3. Tone & style guideline (avoid "AI dashboard" feel)

- No marketing language ("Welcome to...", "Discover...", "Powered by AI").
- No decorative emoji in navigation or tab labels — existing tab text labels
  are unchanged.
- Icons only where they carry semantic meaning (ℹ️/⚠️ notices).
- Microcopy stays factual/technical, matching the existing methodology docs
  tone (e.g. "Reconstruct real playoff series and simulate best-of-7
  outcomes...").

## Testing

`tests/test_streamlit_app.py` gains `AppTest` coverage for:

- The hero renders a FEATURED HISTORICAL FORECAST card with `FEATURED_SERIES`
  team abbreviations and a probability value when the snapshot exists.
- The hero omits the forecast card and badge row when `GAMES_PATH` /
  `MODEL_PATH` are mocked missing (reusing the existing monkeypatch pattern).
- The footer renders the GitHub link and the "2026-06-10" snapshot date.
- The Replay tab's default widget values match `FEATURED_SERIES`.

Existing tests continue to pass unchanged where unaffected.
