# Leakage Prevention

## Core Rule

Every model feature for a game must be reproducible using information available
before that game's tip-off.

## Implemented Controls

- Canonical completed-game outcomes and box scores remain historical inputs,
  not pre-game features for their own game.
- Team state is grouped by season and team, sorted by game date and game ID,
  then shifted by one game before expanding or rolling aggregation.
- Season win percentage defaults to a neutral `0.5` before a team's first game.
- Rolling windows 5, 10, and 20 require at least one prior game and remain null
  before one exists.
- Rest days compare the current game date with the team's previous game date.
- Back-to-back is true only when rest days equal one.
- Elo rows expose both teams' ratings and probability before the current
  result updates either rating.
- Home-minus-away model rows join only pre-game team state and pre-game Elo.
- Scheduled-matchup snapshots include only completed games with
  `game_date < as_of_date`.
- Scheduled inference reuses the historical feature builders through an
  ephemeral row that is never persisted as a completed canonical game.

## Mutation-Based Regression Test

The test suite changes a completed game's outcome and points, rebuilds team
state, and verifies:

1. The changed game's own pre-game features are unchanged.
2. Earlier feature rows are unchanged.
3. Later feature rows reflect the changed history.

This test protects the point-in-time contract as feature logic evolves.

## Scheduled-Matchup Regression Tests

The scheduled snapshot test suite verifies:

1. A reconstructed scheduled row matches the authoritative model features from
   that same game's historical pre-game row.
2. Changing outcomes and scores on or after `as_of_date` cannot change the
   scheduled feature row.
3. An `as_of_date` after the scheduled game date is rejected.

The strict date cutoff is conservative because exact tip-off and completion
timestamps are not yet present in the canonical contract.
