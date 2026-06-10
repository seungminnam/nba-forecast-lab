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
| `home_win` | integer | `1` when home team won, else `0` | No |

Final scores and outcomes are labels or historical feature inputs only after
their game is complete. They must never appear in that game's pre-game feature
row.

## Canonical Transformation Rules

- Each `GAME_ID` must contain exactly two source rows.
- A `MATCHUP` containing `vs.` identifies the home-team row.
- A `MATCHUP` containing `@` identifies the away-team row.
- Home and away rows must have different team identifiers and matching game
  dates and season identifiers.
- Canonical games are sorted by game date and game identifier.

## Canonical Validation Rules

- `game_id` is unique.
- Home and away team identifiers differ.
- Completed games contain both final scores.
- `home_win` contains only `0` or `1`.
- Validation reports all detected rule failures in one actionable error.
