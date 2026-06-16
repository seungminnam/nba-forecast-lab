"""Monte Carlo season win projection using Elo ratings."""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

_PLAYOFF_SEATS = 10  # top 10 per conference (auto + play-in)
_SEASON_GAMES = 82

_EAST_TEAMS: frozenset[str] = frozenset(
    ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DET", "IND", "MIA", "MIL",
     "NYK", "ORL", "PHI", "TOR", "WAS"]
)
_WEST_TEAMS: frozenset[str] = frozenset(
    ["DAL", "DEN", "GSW", "HOU", "LAC", "LAL", "MEM", "MIN", "NOP", "OKC",
     "PHX", "POR", "SAC", "SAS", "UTA"]
)


@dataclass(frozen=True)
class TeamProjection:
    team_abbreviation: str
    conference: str
    median_wins: float
    win_low: int   # 10th-percentile wins (82-game scale)
    win_high: int  # 90th-percentile wins (82-game scale)
    playoff_probability: float  # P(top 10 in conference)


@dataclass(frozen=True)
class SeasonOutlookResult:
    projections: list[TeamProjection]  # sorted by median_wins desc
    simulations: int
    season: str


def simulate_season(
    team_elos: dict[str, float],
    *,
    simulations: int = 10_000,
    home_advantage: float = 100.0,
    seed: int | None = None,
) -> SeasonOutlookResult:
    """Monte Carlo 82-game season projection from end-of-season Elo ratings.

    Uses a round-robin schedule (each pair plays home + away = 58 games per team)
    and scales the resulting win totals to 82-game equivalents.
    """
    teams = sorted(team_elos.keys())

    # Round-robin: each ordered pair (home, away) plays once → 29×2 = 58 games/team
    schedule = [(h, a) for h in teams for a in teams if h != a]
    games_per_team = (len(teams) - 1) * 2  # 58 for a 30-team league
    scale = _SEASON_GAMES / games_per_team  # ≈ 1.414

    east = [t for t in teams if t in _EAST_TEAMS]
    west = [t for t in teams if t in _WEST_TEAMS]

    win_lists: dict[str, list[float]] = {t: [] for t in teams}
    playoff_counts: dict[str, int] = {t: 0 for t in teams}
    rng = random.Random(seed)

    for _ in range(simulations):
        raw_wins: dict[str, int] = {t: 0 for t in teams}

        for home, away in schedule:
            p = _elo_win_prob(team_elos[home] + home_advantage, team_elos[away])
            if rng.random() < p:
                raw_wins[home] += 1
            else:
                raw_wins[away] += 1

        # Playoff seeding uses raw wins (schedule is symmetric, so ranking is valid)
        for conf_teams in (east, west):
            ranked = sorted(conf_teams, key=lambda t: raw_wins[t], reverse=True)
            for rank, team in enumerate(ranked):
                if rank < _PLAYOFF_SEATS:
                    playoff_counts[team] += 1

        for t in teams:
            win_lists[t].append(raw_wins[t] * scale)

    projections = []
    for team in teams:
        wl = sorted(win_lists[team])
        n = len(wl)
        conf = "East" if team in _EAST_TEAMS else "West"
        projections.append(
            TeamProjection(
                team_abbreviation=team,
                conference=conf,
                median_wins=statistics.median(wl),
                win_low=round(wl[max(0, int(n * 0.10))]),
                win_high=round(wl[min(n - 1, int(n * 0.90))]),
                playoff_probability=playoff_counts[team] / simulations,
            )
        )

    projections.sort(key=lambda p: p.median_wins, reverse=True)
    return SeasonOutlookResult(
        projections=projections,
        simulations=simulations,
        season="2026-27",
    )


def _elo_win_prob(adjusted_home_elo: float, away_elo: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-(adjusted_home_elo - away_elo) / 400.0))
