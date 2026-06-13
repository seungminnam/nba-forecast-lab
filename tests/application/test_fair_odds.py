import pytest

from nba_forecast.application.fair_odds import fair_odds_from_probability


@pytest.mark.parametrize(
    ("probability", "decimal_odds", "american_odds"),
    [
        (0.60, 1.6666666666666667, -150),
        (0.40, 2.5, 150),
        (0.50, 2.0, 100),
        (0.5457, 1.832508704416346, -120),
    ],
)
def test_fair_odds_from_probability(
    probability: float,
    decimal_odds: float,
    american_odds: int,
) -> None:
    odds = fair_odds_from_probability(probability)

    assert odds.probability == probability
    assert odds.decimal == pytest.approx(decimal_odds)
    assert odds.american == american_odds


@pytest.mark.parametrize(
    "probability",
    [0.0, 1.0, -0.1, 1.1, float("nan"), float("inf")],
)
def test_fair_odds_rejects_non_finite_two_sided_probability(
    probability: float,
) -> None:
    with pytest.raises(ValueError, match="strictly between zero and one"):
        fair_odds_from_probability(probability)
