"""Interactive product surface for NBA Forecast Lab."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from nba_forecast.application.forecast_retrospective import (
    ForecastOutcome,
    build_forecast_retrospective,
)
from nba_forecast.application.model_performance import build_model_performance_report
from nba_forecast.application.series_replay import (
    SeriesReplayInput,
    SeriesReplayOutput,
    run_series_replay,
)
from nba_forecast.application.simulator_lab import SimulatorLabInput, run_simulator_lab
from nba_forecast.models.artifacts import ModelBundle, load_model_bundle

GAMES_PATH = Path("data/snapshots/2026-06-10/games.parquet")
MODEL_PATH = Path("data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib")
SNAPSHOT_DATE = "2026-06-10"
GITHUB_URL = "https://github.com/seungminnam/nba-forecast-lab"
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
FEATURED_OUTCOME = ForecastOutcome(
    game_id="2026-finals-game-5",
    game_date=pd.Timestamp("2026-06-13"),
    home_team_abbreviation="SAS",
    away_team_abbreviation="NYK",
    home_points=90,
    away_points=94,
    final_team_a_wins=1,
    final_team_b_wins=4,
)


def _format_american_odds(odds: int) -> str:
    return f"+{odds}" if odds > 0 else str(odds)


@st.cache_data
def _load_games(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


@st.cache_resource
def _load_model(path: str) -> ModelBundle:
    return load_model_bundle(Path(path))


@st.cache_resource
def _build_featured_replay(games_path: str, model_path: str) -> SeriesReplayOutput:
    return run_series_replay(
        _load_games(games_path),
        FEATURED_SERIES,
        _load_model(model_path),
    )


def _dark_chart(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure(background="#0E1117")
        .configure_axis(
            domainColor="#4B5563",
            gridColor="#252B33",
            labelColor="#D1D5DB",
            tickColor="#4B5563",
            titleColor="#F7FAFC",
        )
        .configure_legend(
            labelColor="#D1D5DB",
            titleColor="#F7FAFC",
        )
        .configure_title(color="#F7FAFC")
        .configure_view(stroke="#2A3038")
    )

st.set_page_config(
    page_title="NBA Forecast Lab",
    page_icon="🏀",
    layout="wide",
)

st.markdown(
    """
    <style>
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
        background:
            radial-gradient(
                circle at 90% 20%, rgba(45, 212, 191, .14), transparent 36%
            ),
            linear-gradient(120deg, #1C2128, #0E1117 65%);
        border: 1px solid #2A3038;
        margin-bottom: 18px;
    }
    .hero h1 { margin: 6px 0 8px; }
    .hero p { color: #C3CAD3; margin: 0; max-width: 760px; }
    .eyebrow { color: #2DD4BF; font-weight: 700; letter-spacing: .12em; }
    .forecast-card {
        background: linear-gradient(
            145deg, rgba(24, 32, 38, .96), rgba(16, 23, 28, .96)
        );
        border: 1px solid #315C58;
        border-radius: 18px;
        padding: 20px 22px;
        margin: -4px 0 14px;
    }
    .forecast-label {
        color: #5EEAD4;
        font-size: .78rem;
        font-weight: 800;
        letter-spacing: .12em;
    }
    .forecast-context { color: #9CA3AF; font-size: .86rem; margin-top: 4px; }
    .forecast-matchup {
        color: #F7FAFC;
        font-size: 1.22rem;
        font-weight: 700;
        margin-top: 14px;
    }
    .forecast-probability {
        color: #F7FAFC;
        font-size: 1.72rem;
        font-weight: 800;
        margin-top: 2px;
    }
    .forecast-odds { color: #A7F3D0; margin-top: 5px; }
    .retrospective-grid {
        display: grid;
        gap: 12px;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        margin-top: 14px;
    }
    .retrospective-panel {
        background: rgba(14, 17, 23, .62);
        border: 1px solid #303842;
        border-radius: 12px;
        padding: 14px;
    }
    .retrospective-panel strong { color: #5EEAD4; }
    .retrospective-interpretation {
        color: #D1FAE5;
        margin-top: 14px;
    }
    .badge-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 22px; }
    .badge {
        background: #171C22;
        border: 1px solid #303842;
        border-radius: 999px;
        color: #D1D5DB;
        font-size: .82rem;
        padding: 7px 11px;
    }
    a.badge { color: #5EEAD4; text-decoration: none; }
    .notice {
        background: #261d0c;
        border: 1px solid #75561d;
        color: #ffd98a;
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 18px;
    }
    .footer {
        border-top: 1px solid #2A3038;
        color: #9CA3AF;
        font-size: .82rem;
        margin-top: 28px;
        padding: 18px 2px 8px;
    }
    .footer a { color: #5EEAD4; text-decoration: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">NBA FORECAST LAB</div>
      <h1>Leakage-Safe NBA Game Forecasting</h1>
      <p>Reconstruct historical playoff series at a declared cutoff, inspect
      calibrated game probabilities, and explore explicit best-of-seven
      assumptions.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

featured_retrospective = None
if GAMES_PATH.exists() and MODEL_PATH.exists():
    try:
        featured_replay = _build_featured_replay(str(GAMES_PATH), str(MODEL_PATH))
        featured_retrospective = build_forecast_retrospective(
            featured_replay,
            FEATURED_OUTCOME,
        )
    except ValueError:
        featured_retrospective = None

if featured_retrospective is not None:
    featured_game = featured_retrospective.forecast.next_game_forecast
    featured_result = featured_retrospective.forecast.result
    assert featured_game is not None
    assert featured_result is not None
    featured_interpretation = (
        "The game-level favorite lost, while the strongly favored series winner "
        "won. The frozen prediction was not modified after the result."
    )
    st.markdown(
        f"""
        <div class="forecast-card">
          <div class="forecast-label">2026 FINALS FORECAST RETROSPECTIVE</div>
          <div class="forecast-context">
            Frozen forecast cutoff · 2026-06-11 · Outcome · 2026-06-13
          </div>
          <div class="retrospective-grid">
            <div class="retrospective-panel">
              <strong>Frozen pre-Game 5 forecast</strong><br>
              SAS {featured_game.home_win_probability:.1%} ·
              NYK {featured_game.away_win_probability:.1%}<br>
              NYK series win
              {featured_result.team_b_series_win_probability:.1%}<br>
              Expected final length {featured_result.expected_games:.2f} games
            </div>
            <div class="retrospective-panel">
              <strong>Actual outcome</strong><br>
              NYK won 94–90<br>
              NYK won series 4–1<br>
              Series ended in 5 games
            </div>
          </div>
          <div class="retrospective-interpretation">
            {featured_interpretation}
          </div>
        </div>
        <div class="badge-row">
          <span class="badge">
            Single-game Brier {featured_retrospective.game_brier_score:.4f}
          </span>
          <span class="badge">Frozen model Brier 0.2073</span>
          <span class="badge">
            Baseline Logistic Regression vs Elo Brier improvement 3.33%
          </span>
          <span class="badge">Point-in-time features only</span>
          <a class="badge" href="{GITHUB_URL}">GitHub repository</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

replay_tab, assumption_tab, performance_tab, methodology_tab = st.tabs(
    [
        "Model-Backed Historical Replay",
        "Assumption Lab",
        "Model Performance",
        "Methodology",
    ]
)


def _render_charts(
    outcome_table: pd.DataFrame,
    length_table: pd.DataFrame,
    team_a: str,
    team_b: str,
) -> None:
    team_colors = alt.Scale(
        domain=[team_a, team_b],
        range=["#2DD4BF", "#A78BFA"],
    )
    charts = st.columns(2)
    with charts[0]:
        st.subheader("Series outcome distribution")
        outcome_chart = (
            alt.Chart(outcome_table)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X(
                    "probability:Q",
                    axis=alt.Axis(format="%"),
                    title="Probability",
                ),
                y=alt.Y("label:N", sort="-x", title=None),
                color=alt.Color("team:N", scale=team_colors, legend=None),
                tooltip=[
                    "team:N",
                    "games:Q",
                    alt.Tooltip("probability:Q", format=".1%"),
                ],
            )
        )
        st.altair_chart(_dark_chart(outcome_chart), use_container_width=True)

    with charts[1]:
        st.subheader("Series length distribution")
        length_chart = (
            alt.Chart(length_table)
            .mark_bar(color="#2DD4BF", cornerRadiusEnd=4)
            .encode(
                x=alt.X("games:O", title="Games"),
                y=alt.Y(
                    "probability:Q",
                    axis=alt.Axis(format="%"),
                    title="Probability",
                ),
                tooltip=["games:O", alt.Tooltip("probability:Q", format=".1%")],
            )
        )
        st.altair_chart(_dark_chart(length_chart), use_container_width=True)


with replay_tab:
    st.markdown(
        """
        <div class="notice">ℹ️ <strong>Historical Replay.</strong> The observed
        series score is reconstructed from completed playoff games strictly
        before the cutoff. Venue probabilities are frozen at that cutoff;
        psychological effects and future team-state updates are not modeled.
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.subheader("Replay context")
        dates = st.columns(2)
        as_of_date = dates[0].date_input(
            "As-of date",
            value=FEATURED_SERIES.as_of_date.date(),
            key="replay_as_of",
        )
        next_game_date = dates[1].date_input(
            "Next game date",
            value=FEATURED_SERIES.next_game_date.date(),
            key="replay_next_game",
        )
        teams = st.columns(2)
        team_a_abbreviation = teams[0].text_input(
            "Team A · home-court owner",
            value=FEATURED_SERIES.team_a_abbreviation,
            key="replay_team_a",
        )
        team_b_abbreviation = teams[1].text_input(
            "Team B",
            value=FEATURED_SERIES.team_b_abbreviation,
            key="replay_team_b",
        )
        team_ids = st.columns(2)
        team_a_id = int(
            team_ids[0].number_input(
                "Team A ID",
                value=FEATURED_SERIES.team_a_id,
                step=1,
                key="replay_team_a_id",
            )
        )
        team_b_id = int(
            team_ids[1].number_input(
                "Team B ID",
                value=FEATURED_SERIES.team_b_id,
                step=1,
                key="replay_team_b_id",
            )
        )
        replay_settings = st.columns(2)
        replay_simulations = replay_settings[0].select_slider(
            "Replay Monte Carlo simulations",
            options=[1_000, 5_000, 10_000, 25_000, 50_000],
            value=FEATURED_SERIES.simulations,
        )
        replay_seed = int(
            replay_settings[1].number_input(
                "Replay random seed",
                min_value=0,
                value=FEATURED_SERIES.seed,
                step=1,
            )
        )
        run_replay = st.button("Run historical replay", type="primary")

    if run_replay:
        if not GAMES_PATH.exists() or not MODEL_PATH.exists():
            st.warning(
                "Historical Replay requires local processed games and the frozen "
                "model bundle. Rebuild the data pipeline and model artifact first."
            )
        else:
            try:
                replay_output = run_series_replay(
                    _load_games(str(GAMES_PATH)),
                    SeriesReplayInput(
                        as_of_date=pd.Timestamp(as_of_date),
                        next_game_date=pd.Timestamp(next_game_date),
                        season_id="42025",
                        season_type="Playoffs",
                        season_key="2025-26",
                        team_a_id=team_a_id,
                        team_a_abbreviation=team_a_abbreviation,
                        team_b_id=team_b_id,
                        team_b_abbreviation=team_b_abbreviation,
                        simulations=replay_simulations,
                        seed=replay_seed,
                    ),
                    _load_model(str(MODEL_PATH)),
                )
            except ValueError as error:
                st.error(str(error))
            else:
                state = replay_output.state
                st.subheader(
                    f"Observed score: {team_a_abbreviation} {state.team_a_wins}"
                    f"–{state.team_b_wins} {team_b_abbreviation}"
                )
                if not state.observed_games.empty:
                    st.caption("Completed playoff games strictly before the cutoff")
                    st.dataframe(
                        state.observed_games[
                            [
                                "game_date",
                                "home_team_abbreviation",
                                "away_team_abbreviation",
                                "home_points",
                                "away_points",
                            ]
                        ],
                        hide_index=True,
                        width="stretch",
                    )
                if state.is_complete:
                    st.info("The selected series was already complete at this cutoff.")
                elif (
                    replay_output.result is not None
                    and replay_output.next_game_forecast is not None
                ):
                    next_game = replay_output.next_game_forecast
                    st.subheader(
                        f"Next Game Forecast · Game {next_game.game_number}"
                    )
                    st.caption(
                        f"{pd.Timestamp(next_game.game_date).date().isoformat()} · "
                        f"{next_game.home_team_abbreviation} home"
                    )
                    next_game_columns = st.columns(2)
                    next_game_columns[0].metric(
                        f"{next_game.home_team_abbreviation} next-game win",
                        f"{next_game.home_win_probability:.1%}",
                    )
                    next_game_columns[0].caption(
                        "Model-implied fair odds: "
                        f"Decimal {next_game.home_fair_odds.decimal:.2f} · "
                        "American "
                        f"{_format_american_odds(next_game.home_fair_odds.american)}"
                    )
                    next_game_columns[1].metric(
                        f"{next_game.away_team_abbreviation} next-game win",
                        f"{next_game.away_win_probability:.1%}",
                    )
                    next_game_columns[1].caption(
                        "Model-implied fair odds: "
                        f"Decimal {next_game.away_fair_odds.decimal:.2f} · "
                        "American "
                        f"{_format_american_odds(next_game.away_fair_odds.american)}"
                    )
                    st.info(
                        "Model-implied fair odds are a no-margin transformation "
                        "of the displayed probabilities, not sportsbook prices or "
                        "betting advice."
                    )
                    st.subheader("Remaining Series Forecast")
                    replay_metrics = st.columns(3)
                    replay_metrics[0].metric(
                        f"{team_a_abbreviation} series win",
                        f"{replay_output.result.team_a_series_win_probability:.1%}",
                    )
                    replay_metrics[1].metric(
                        f"{team_b_abbreviation} series win",
                        f"{replay_output.result.team_b_series_win_probability:.1%}",
                    )
                    replay_metrics[2].metric(
                        "Expected final series length",
                        f"{replay_output.result.expected_games:.2f}",
                    )
                    _render_charts(
                        replay_output.outcome_table,
                        replay_output.length_table,
                        team_a_abbreviation,
                        team_b_abbreviation,
                    )

with assumption_tab:
    st.markdown(
        """
        <div class="notice">⚠️ <strong>Assumption-based demo.</strong> These inputs
        are hypothetical and are not current frozen-model NBA predictions.</div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.subheader("Series assumptions")
        names = st.columns(2)
        team_a = names[0].text_input("Team A · home-court owner", value="Knicks")
        team_b = names[1].text_input("Team B", value="Spurs")

        probabilities = st.columns(2)
        team_a_home = probabilities[0].slider(
            f"{team_a or 'Team A'} win probability at home",
            min_value=0.0,
            max_value=1.0,
            value=0.62,
            step=0.01,
        )
        team_a_away = probabilities[1].slider(
            f"{team_a or 'Team A'} win probability away",
            min_value=0.0,
            max_value=1.0,
            value=0.47,
            step=0.01,
        )

        settings = st.columns(2)
        simulations = settings[0].select_slider(
            "Monte Carlo simulations",
            options=[1_000, 5_000, 10_000, 25_000, 50_000],
            value=10_000,
        )
        seed = settings[1].number_input(
            "Random seed",
            min_value=0,
            value=2026,
            step=1,
        )

    try:
        output = run_simulator_lab(
            SimulatorLabInput(
                team_a=team_a,
                team_b=team_b,
                team_a_home_win_probability=team_a_home,
                team_a_away_win_probability=team_a_away,
                simulations=simulations,
                seed=int(seed),
            )
        )
    except ValueError as error:
        st.error(str(error))
        st.stop()

    metrics = st.columns(3)
    metrics[0].metric(
        f"{team_a} series win",
        f"{output.result.team_a_series_win_probability:.1%}",
    )
    metrics[1].metric(
        f"{team_b} series win",
        f"{output.result.team_b_series_win_probability:.1%}",
    )
    metrics[2].metric("Expected games", f"{output.result.expected_games:.2f}")
    _render_charts(output.outcome_table, output.length_table, team_a, team_b)

    with st.expander("Methodology and current limitation"):
        st.markdown(
            """
            The engine follows `A, A, B, B, A, B, A`, stops when a team reaches
            four wins, and repeats the series using the displayed seed.

            This tab uses your explicit probability assumptions and does not
            reconstruct observed history.
            """
        )

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

st.markdown(
    f"""
    <div class="footer">
      <a href="{GITHUB_URL}">GitHub repository</a> · Data snapshot: {SNAPSHOT_DATE}
    </div>
    """,
    unsafe_allow_html=True,
)
