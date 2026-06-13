"""Interactive product surface for NBA Forecast Lab."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from nba_forecast.application.model_performance import build_model_performance_report
from nba_forecast.application.series_replay import SeriesReplayInput, run_series_replay
from nba_forecast.application.simulator_lab import SimulatorLabInput, run_simulator_lab
from nba_forecast.models.artifacts import load_model_bundle

GAMES_PATH = Path("data/snapshots/2026-06-10/games.parquet")
MODEL_PATH = Path("data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib")

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
        background: linear-gradient(120deg, #1C2128, #0E1117 65%);
        border: 1px solid #2A3038;
        margin-bottom: 18px;
    }
    .eyebrow { color: #2DD4BF; font-weight: 700; letter-spacing: .12em; }
    .notice {
        background: #261d0c;
        border: 1px solid #75561d;
        color: #ffd98a;
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">NBA FORECAST LAB</div>
      <h1>Historical Replay & Best-of-7 Simulator</h1>
      <p>Reconstruct a real playoff series at a declared cutoff or explore
      explicit hypothetical assumptions.</p>
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
        st.altair_chart(outcome_chart, use_container_width=True)

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
        st.altair_chart(length_chart, use_container_width=True)


def _format_american_odds(odds: int) -> str:
    return f"+{odds}" if odds > 0 else str(odds)


with replay_tab:
    st.markdown(
        """
        <div class="notice"><strong>Historical Replay.</strong> The observed
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
            value=pd.Timestamp("2026-06-11").date(),
            key="replay_as_of",
        )
        next_game_date = dates[1].date_input(
            "Next game date",
            value=pd.Timestamp("2026-06-13").date(),
            key="replay_next_game",
        )
        teams = st.columns(2)
        team_a_abbreviation = teams[0].text_input(
            "Team A · home-court owner",
            value="SAS",
            key="replay_team_a",
        )
        team_b_abbreviation = teams[1].text_input(
            "Team B",
            value="NYK",
            key="replay_team_b",
        )
        team_ids = st.columns(2)
        team_a_id = int(
            team_ids[0].number_input(
                "Team A ID",
                value=1610612759,
                step=1,
                key="replay_team_a_id",
            )
        )
        team_b_id = int(
            team_ids[1].number_input(
                "Team B ID",
                value=1610612752,
                step=1,
                key="replay_team_b_id",
            )
        )
        replay_settings = st.columns(2)
        replay_simulations = replay_settings[0].select_slider(
            "Replay Monte Carlo simulations",
            options=[1_000, 5_000, 10_000, 25_000, 50_000],
            value=10_000,
        )
        replay_seed = int(
            replay_settings[1].number_input(
                "Replay random seed",
                min_value=0,
                value=2026,
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
                    pd.read_parquet(GAMES_PATH),
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
                    load_model_bundle(MODEL_PATH),
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
        <div class="notice"><strong>Assumption-based demo.</strong> These inputs
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
