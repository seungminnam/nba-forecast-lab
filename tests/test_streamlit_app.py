from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[1] / "streamlit_app.py"


def test_streamlit_app_renders_simulator_results() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()

    assert not app.exception
    assert "Best-of-7 Simulator Lab" in app.markdown[1].value
    assert "Assumption-based demo" in app.markdown[1].value
    assert len(app.metric) == 3
    assert app.metric[0].label == "Knicks series win"
    assert [subheader.value for subheader in app.subheader] == [
        "Series assumptions",
        "Series outcome distribution",
        "Series length distribution",
    ]


def test_streamlit_app_shows_distinct_team_validation_error() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()

    app.text_input[1].input("Knicks").run()

    assert not app.exception
    assert app.error[0].value == "Team names must be distinct"
