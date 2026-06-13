"""Model-implied no-margin fair-odds conversion."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FairOdds:
    """Probability and equivalent no-margin odds formats."""

    probability: float
    decimal: float
    american: int


def fair_odds_from_probability(probability: float) -> FairOdds:
    """Convert one finite two-sided probability into model-implied fair odds."""
    if not math.isfinite(probability) or not 0.0 < probability < 1.0:
        raise ValueError("probability must be strictly between zero and one")

    decimal = 1.0 / probability
    if probability > 0.5:
        american = round(-100.0 * probability / (1.0 - probability))
    else:
        american = round(100.0 * (1.0 - probability) / probability)
    return FairOdds(
        probability=probability,
        decimal=decimal,
        american=american,
    )
