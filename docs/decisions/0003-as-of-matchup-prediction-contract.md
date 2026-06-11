# ADR 0003: As-of Matchup Prediction Contract

## Status

Accepted on 2026-06-11.

## Context

Historical model rows are built from completed games, but an upcoming matchup
has no result or box score. The application needs to reproduce the same
pre-game feature definitions for a scheduled matchup without persisting an
incomplete row as a canonical completed game.

The current canonical data records dates, not exact tip-off and completion
timestamps. Including games from the same calendar date could therefore leak a
result that was not known when a prediction was made.

## Decision

- A scheduled matchup is represented by known identifiers, teams, season, and
  game date.
- Prediction history includes only completed games where
  `game_date < as_of_date`.
- The feature builder appends one ephemeral scheduled row only while computing
  features. It is never validated or persisted as a canonical completed game.
- Training and scheduled inference reuse the same shifted team-state, Elo, and
  game-feature builders.
- The prediction report records a UTC prediction timestamp, `as_of_date`,
  model version, feature version, matchup identity, probabilities, the exact
  authoritative feature values used, and an initially empty final outcome.

## Alternatives Considered

### Include games on `as_of_date`

This could use fresher information after an earlier game finishes, but it is
unsafe without exact timestamps. It was rejected until the source contract
records tip-off and prediction timestamps.

### Reimplement inference features separately

This avoids an ephemeral scheduled row but creates a second feature definition
that can drift from training. It was rejected in favor of historical-parity
tests and shared builders.

### Build all future series games at once

Future rest days can be known, but future rolling ratings depend on games that
have not happened. It was rejected for the initial prediction workflow.

## Consequences

- Same-day completed games are conservatively excluded.
- Historical-parity and future-mutation tests protect the point-in-time
  contract.
- A current 2026 Finals prediction still requires the processed history to be
  refreshed with 2025-26 playoff games.
