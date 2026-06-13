from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[1] / "streamlit_app.py"


def test_streamlit_app_renders_simulator_results() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Model-Backed Historical Replay",
        "Assumption Lab",
    ]
    assert any("NBA FORECAST LAB" in markdown.value for markdown in app.markdown)
    assert any("Assumption-based demo" in markdown.value for markdown in app.markdown)
    assert len(app.metric) == 3
    assert app.metric[0].label == "Knicks series win"
    assert [subheader.value for subheader in app.subheader] == [
        "Replay context",
        "Series assumptions",
        "Series outcome distribution",
        "Series length distribution",
    ]


def test_streamlit_app_shows_distinct_team_validation_error() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()

    app.text_input[3].input("Knicks").run()

    assert not app.exception
    assert app.error[0].value == "Team names must be distinct"
