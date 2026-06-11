# Data Dictionary

## Data Layers

| Layer | Purpose | Mutability |
|---|---|---|
| Raw | Source-shaped NBA Stats extracts and metadata | Immutable per fetch |
| Processed | Canonical one-row-per-game table | Rebuildable |
| Features | Point-in-time model rows | Rebuildable and versioned |
| Predictions | Timestamped model output and later outcome | Append-oriented |

## Raw Team-Game Contract

The Phase 0/1 source is expected to provide two rows per completed game: one
home-team row and one away-team row.

| Source column | Meaning |
|---|---|
| `GAME_ID` | NBA game identifier |
| `GAME_DATE` | Game date |
| `SEASON_ID` | NBA season identifier |
| `TEAM_ID` | Team identifier for this row |
| `TEAM_ABBREVIATION` | Team abbreviation for this row |
| `MATCHUP` | Contains `vs.` for home or `@` for away |
| `WL` | Team result, `W` or `L` |
| `PTS` | Team final points |
| `FGA` | Team field-goal attempts |
| `FGM` | Team made field goals |
| `FTA` | Team free-throw attempts |
| `OREB` | Team offensive rebounds |
| `TOV` | Team turnovers |

## Canonical Completed Game Contract

| Column | Type | Meaning | Available before tip-off? |
|---|---|---|---|
| `game_id` | string | Unique NBA game identifier | Yes |
| `game_date` | date | Scheduled game date | Yes |
| `season_id` | string | Source season identifier | Yes |
| `home_team_id` | integer | Home team identifier | Yes |
| `away_team_id` | integer | Away team identifier | Yes |
| `home_team_abbreviation` | string | Home team abbreviation | Yes |
| `away_team_abbreviation` | string | Away team abbreviation | Yes |
| `home_points` | integer | Home final score | No |
| `away_points` | integer | Away final score | No |
| `home_fga`, `away_fga` | integer | Team field-goal attempts | No |
| `home_fgm`, `away_fgm` | integer | Team made field goals | No |
| `home_fta`, `away_fta` | integer | Team free-throw attempts | No |
| `home_oreb`, `away_oreb` | integer | Team offensive rebounds | No |
| `home_tov`, `away_tov` | integer | Team turnovers | No |
| `home_win` | integer | `1` when home team won, else `0` | No |

Final scores and outcomes are labels or historical feature inputs only after
their game is complete. They must never appear in that game's pre-game feature
row.

## Canonical Transformation Rules

- Each `GAME_ID` must contain exactly two source rows.
- A `MATCHUP` shaped as `HOME vs. AWAY` identifies the left abbreviation as
  home.
- A `MATCHUP` shaped as `AWAY @ HOME` identifies the right abbreviation as
  home.
- The home row is selected by comparing the parsed home abbreviation with the
  row's `TEAM_ABBREVIATION`. This handles known source anomalies where both
  team rows contain the same `AWAY @ HOME` matchup string.
- Home and away rows must have different team identifiers and matching game
  dates and season identifiers.
- Canonical games are sorted by game date and game identifier.

## Canonical Validation Rules

- `game_id` is unique.
- Home and away team identifiers differ.
- Completed games contain both final scores.
- `home_win` contains only `0` or `1`.
- Validation reports all detected rule failures in one actionable error.

## Pre-Game Team State

Each completed game creates one team-perspective row for the home team and one
for the away team. Completed-game ratings are historical inputs only for later
games.

| Feature | Meaning |
|---|---|
| `games_played` | Earlier games played by this team in the season |
| `season_win_pct` | Shifted expanding season win percentage; neutral `0.5` before game one |
| `rest_days` | Days since the team's previous game |
| `is_back_to_back` | `1` when `rest_days == 1` |
| `win_pct_5/10/20` | Shifted rolling win percentage |
| `offensive_rating_5/10/20` | Shifted rolling points per 100 estimated possessions |
| `defensive_rating_5/10/20` | Shifted rolling opponent points per 100 estimated possessions |
| `net_rating_5/10/20` | Shifted rolling offensive minus defensive rating |

Estimated possessions use `FGA + 0.44 * FTA - OREB + TOV`.

## Pre-Game Model Rows

Each model row contains game identifiers, the `home_win` target, pre-game Elo,
and home-minus-away differences for games played, win percentage, rest days,
and rolling ratings. Home and away back-to-back indicators remain separate
binary features.

`MODEL_FEATURE_COLUMNS` is the authoritative list supplied to trained models.
It excludes identifiers, current-game scores, and the `home_win` target.

## Scheduled Matchup Snapshot

A `ScheduledMatchup` contains only information known before tip-off:

| Field | Meaning |
|---|---|
| `game_id` | Stable scheduled-game identifier |
| `game_date` | Scheduled calendar date |
| `season_id` | NBA season identifier |
| `home_team_id`, `away_team_id` | Team identifiers |
| `home_team_abbreviation`, `away_team_abbreviation` | Display abbreviations |

The as-of builder includes completed history only where
`game_date < as_of_date`. It returns one row containing identifiers,
`as_of_date`, an empty target, and the same `MODEL_FEATURE_COLUMNS` used during
training.

Stored matchup prediction reports include a UTC prediction timestamp,
`as_of_date`, game identifier, model version, feature version, home and away
probabilities, the exact feature values used, and a nullable final outcome.

## Series Simulation Contract

`team_a` is the home-court owner and `team_b` is the opponent.

Each probability request receives a `SeriesGameContext`:

| Field | Meaning |
|---|---|
| `game_number` | One-based scheduled series game number |
| `home_team` | Team hosting the current game |
| `away_team` | Visiting team |
| `team_a`, `team_b` | Stable series team identifiers |
| `team_a_wins`, `team_b_wins` | Sampled series score before the current game |

The provider returns the current game's home-team win probability between
`0.0` and `1.0`.

`SeriesSimulationResult` reports:

| Field | Meaning |
|---|---|
| `team_a_series_win_probability` | Fraction of simulations won by Team A |
| `team_b_series_win_probability` | Fraction of simulations won by Team B |
| `outcome_probabilities` | Winner-in-4/5/6/7 probability distribution |
| `length_probabilities` | Probability the series lasts 4, 5, 6, or 7 games |
| `expected_games` | Probability-weighted expected series length |
| `simulations`, `seed` | Reproduction metadata |
