# Playoff Data Continuity Design

## Goal

Extend the canonical game pipeline through the 2025-26 playoffs without
resetting pre-game team state at the regular-season-to-playoffs boundary.

This milestone makes current playoff matchup prediction possible. It does not
retrain or reselect the frozen probability model.

## Problem

NBA Stats identifies the regular season and playoffs as separate source
season types. Their source `SEASON_ID` values also use different prefixes:

```text
2025-26 Regular Season -> 22025
2025-26 Playoffs       -> 42025
```

The current feature pipeline groups rolling team state by `season_id` and
applies Elo offseason reversion whenever `season_id` changes. Concatenating
playoff rows without changing that logic would therefore erase each team's
regular-season rolling history and apply offseason Elo reversion before the
first playoff game.

Those behaviors are incorrect. Recent form, rest, games played, and Elo should
continue from the end of the regular season into the playoffs.

## Chosen Approach

Preserve source identity and add a separate continuity key:

- `season_id` preserves the NBA Stats source identifier.
- `season_type` preserves whether the game came from `Regular Season` or
  `Playoffs`.
- `season_key` identifies the shared NBA season, such as `2025-26`.

Feature builders use `season_key` for state continuity. Public data artifacts
retain all three fields so source provenance and game type remain auditable.

This approach is preferred over rewriting playoff `season_id` values because
rewriting loses source meaning. It is preferred over treating the playoffs as
a new season because that creates an artificial state reset.

## Scope

### Included

- Pass `season_type` and `season_key` into canonical transformation.
- Preserve the raw source `season_id`.
- Validate supported season types and season-key consistency.
- Continue rolling team state across the regular-season-to-playoffs boundary.
- Apply Elo offseason reversion only when `season_key` changes.
- Fetch and combine 2025-26 regular-season and playoff raw caches.
- Rebuild canonical and feature artifacts with the expanded contract.
- Verify that the current as-of matchup workflow consumes playoff-updated
  history.
- Document source coverage, commands, contract changes, and limitations.

### Excluded

- Retraining, recalibrating, or reselecting the frozen model.
- Using playoff games in the untouched 2025-26 regular-season test result.
- Adding a playoff indicator to `MODEL_FEATURE_COLUMNS`.
- Adding playoff-specific coefficients or assumptions.
- Changing the definition of `season_win_pct`.
- Automating scheduled matchup discovery.
- Connecting matchup predictions to the series simulator or Streamlit UI.

## Data Contract

### Raw Cache

Raw cache paths remain separated by season and source season type:

```text
data/raw/nba_stats/league_game_finder/2025-26/regular-season.csv
data/raw/nba_stats/league_game_finder/2025-26/playoffs.csv
```

The metadata sidecar remains the authoritative record of the request's
`season` and `season_type`. The raw CSV remains an unmodified source extract.

### Canonical Completed Game

Each canonical row adds:

| Field | Example | Meaning |
|---|---|---|
| `season_id` | `42025` | Unmodified NBA Stats source identifier |
| `season_type` | `Playoffs` | Source request type |
| `season_key` | `2025-26` | Shared state-continuity season |

`season_type` must be either `Regular Season` or `Playoffs`. `season_key` must
be a non-empty NBA season label. Every source file is transformed with its
request context rather than attempting to infer `season_type` from a game ID.
Direct transformation calls receive `season_type` and `season_key`
explicitly. The multi-file build workflow reads each raw CSV's adjacent
metadata sidecar and uses its `season` as the canonical `season_key`.

Existing processed artifacts lack these required fields and must be rebuilt.
The pipeline must fail clearly rather than silently inventing continuity
metadata for old artifacts.

## Pipeline Flow

```text
Regular-season raw cache --\
                            -> contextual canonical transform
Playoff raw cache ---------/       |
                                    v
                    canonical games with source identity
                                    |
                                    v
                  rolling state and Elo by season_key
                                    |
                                    v
                  as-of matchup prediction with frozen model
```

The build workflow accepts multiple raw-cache inputs and requires a valid
metadata sidecar beside each one. It transforms each file with that context
before concatenating and validating the canonical games. Duplicate `game_id`
values remain invalid.

## Feature Behavior

### Rolling Team State

Rolling windows, rest days, games played, and `season_win_pct` group by
`season_key` and `team_id`.

For the first 2025-26 playoff game:

- `games_played` includes completed 2025-26 regular-season games.
- recent 5, 10, and 20-game windows include the latest regular-season games.
- rest days use the team's final regular-season game date.
- completed playoff games enter the history of later playoff games.

`season_win_pct` consequently remains a combined season-to-date value during
this milestone. Whether a separate playoff record improves probability quality
is deferred to a future validation-only feature experiment.

### Elo

Elo ratings update sequentially through regular-season and playoff games.
Offseason reversion occurs only when `season_key` changes. A change from
`season_id=22025` to `season_id=42025` within `season_key=2025-26` does not
trigger reversion.

### Frozen Model Compatibility

The expanded canonical identifiers do not change `MODEL_FEATURE_COLUMNS`.
The frozen recent-five Logistic Regression bundle therefore remains loadable
and scoreable. Its existing final-test metrics remain regular-season-only
evidence and must not be reinterpreted as playoff performance.

## Point-in-Time and Leakage Contract

- Only completed games before the requested `as_of_date` may affect a
  scheduled matchup row.
- A first-playoff-game snapshot may use completed regular-season history.
- A later-playoff-game snapshot may use only playoff games completed before
  its cutoff.
- Changing a current or future playoff result must not change an earlier
  pre-game feature row.
- Source type and continuity metadata are identifiers, not target information.

## Error Handling

- Reject unsupported or empty `season_type` values.
- Reject empty `season_key` values.
- Reject build inputs with missing or invalid raw-cache metadata sidecars.
- Reject canonical rows missing the expanded required contract.
- Retain existing duplicate-game, score, target, and home-away validation.
- If a live playoff fetch is unavailable or incomplete, retain the previous
  known-good processed artifacts and do not claim a current prediction.

## Testing Strategy

### Transformation and Validation

- Prove regular-season and playoff transformations preserve their source
  `season_id`, `season_type`, and shared `season_key`.
- Prove invalid season metadata is rejected.
- Prove processed storage persists the expanded contract.

### Feature Continuity

- Prove the first playoff game's rolling state includes the final
  regular-season games.
- Prove the first playoff game's Elo does not receive offseason reversion.
- Prove an actual new `season_key` still resets rolling state and applies Elo
  reversion.
- Preserve existing current-result and future-result leakage regression tests.

### End-to-End Refresh

- Fetch or reuse both 2025-26 raw caches.
- Rebuild canonical games and feature rows.
- Verify row counts, date ranges, season types, and duplicate-free game IDs.
- Run one frozen-bundle as-of matchup prediction from the refreshed history.
- Run `ruff check .`, `mypy src`, and `pytest`.

Live NBA Stats requests remain separate smoke tests. Automated tests remain
network-free.

## Documentation and Claims

Update the README, data dictionary, source report, architecture,
leakage-prevention notes, model card, and runbook in the same work unit.

The public claim after this milestone may state that the pipeline supports
regular-season-to-playoff state continuity and can produce an as-of playoff
matchup probability from refreshed completed-game history.

It must not claim measured playoff accuracy, improved model performance, or a
current Finals prediction unless the live source refresh and prediction are
successfully verified and timestamped.

## Success Criteria

1. Source `season_id` and `season_type` remain auditable in canonical data.
2. Regular-season and playoff games share a validated `season_key`.
3. The first playoff game receives continuous rolling state and Elo.
4. Actual new seasons still trigger the intended reset and reversion.
5. Point-in-time leakage tests cover the playoff boundary.
6. The refreshed 2025-26 history can score a scheduled playoff matchup with the
   frozen model bundle.
