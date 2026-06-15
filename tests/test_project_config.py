from pathlib import Path


def test_runtime_sklearn_matches_frozen_model_artifact() -> None:
    pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text()

    assert '"scikit-learn==1.6.1",' in pyproject


def test_local_prediction_registry_is_gitignored() -> None:
    gitignore = (Path(__file__).parents[1] / ".gitignore").read_text().splitlines()

    assert "data/registry/" in gitignore
