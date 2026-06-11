"""Interactive Simulator Lab for NBA Forecast Lab."""

import altair as alt
import streamlit as st

from nba_forecast.application.simulator_lab import SimulatorLabInput, run_simulator_lab

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
      <h1>Best-of-7 Simulator Lab</h1>
      <p>Explore how venue-specific game probabilities become a full playoff
      series outcome distribution.</p>
    </div>
    <div class="notice"><strong>Assumption-based demo.</strong> These inputs
    are not current frozen-model NBA matchup predictions.</div>
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

team_colors = alt.Scale(
    domain=[team_a, team_b],
    range=["#4ba3ff", "#ff9f43"],
)
charts = st.columns(2)
with charts[0]:
    st.subheader("Series outcome distribution")
    outcome_chart = (
        alt.Chart(output.outcome_table)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("probability:Q", axis=alt.Axis(format="%"), title="Probability"),
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
        alt.Chart(output.length_table)
        .mark_bar(color="#70b7ff", cornerRadiusEnd=4)
        .encode(
            x=alt.X("games:O", title="Games"),
            y=alt.Y("probability:Q", axis=alt.Axis(format="%"), title="Probability"),
            tooltip=["games:O", alt.Tooltip("probability:Q", format=".1%")],
        )
    )
    st.altair_chart(length_chart, use_container_width=True)

with st.expander("Methodology and current limitation"):
    st.markdown(
        """
        The engine follows `A, A, B, B, A, B, A`, stops when a team reaches
        four wins, and repeats the series using the displayed seed.

        This page uses your explicit probability assumptions. Scheduled-game
        feature generation and frozen-model matchup probabilities are the next
        integration step.
        """
    )
