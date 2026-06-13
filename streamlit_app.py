"""Interactive product surface for NBA Forecast Lab."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from nba_forecast.application.series_replay import SeriesReplayInput, run_series_replay
from nba_forecast.application.simulator_lab import SimulatorLabInput, run_simulator_lab
from nba_forecast.models.artifacts import load_model_bundle

GAMES_PATH = Path("data/processed/games.parquet")
MODEL_PATH = Path("artifacts/models/2026-06-11-recent5-raw.joblib")

st.set_page_config(
    page_title="NBA Forecast Lab",
    page_icon="🏀",
    layout="wide",
)

st.markdown(
    """
    <style>
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

replay_tab, assumption_tab = st.tabs(
    ["Model-Backed Historical Replay", "Assumption Lab"]
)


def _render_charts(
    outcome_table: pd.DataFrame,
    length_table: pd.DataFrame,
    team_a: str,
    team_b: str,
) -> None:
    team_colors = alt.Scale(
        domain=[team_a, team_b],
        range=["#4ba3ff", "#ff9f43"],
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
            .mark_bar(color="#70b7ff", cornerRadiusEnd=4)
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
