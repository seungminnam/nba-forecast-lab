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

## Mutation-Based Regression Test

The test suite changes a completed game's outcome and points, rebuilds team
state, and verifies:

1. The changed game's own pre-game features are unchanged.
2. Earlier feature rows are unchanged.
3. Later feature rows reflect the changed history.

This test protects the point-in-time contract as feature logic evolves.
