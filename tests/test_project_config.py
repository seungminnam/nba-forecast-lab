from pathlib import Path


def test_runtime_sklearn_matches_frozen_model_artifact() -> None:
    pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text()

    assert '"scikit-learn==1.6.1",' in pyproject
