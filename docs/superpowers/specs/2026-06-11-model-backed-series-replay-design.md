# Model-Backed Series Historical Replay Design

## Goal

Connect the frozen game-probability model to the best-of-seven simulator so a
user can reconstruct and simulate a real playoff series from any declared
historical `as_of_date`.

The primary product workflow is Historical Replay. The existing Assumption Lab
remains available for hypothetical probability experiments.

## Core Question

At a declared point before a playoff game, what was the observed series state,
what venue-specific probabilities did the frozen model assign using only
information then available, and what remaining-series outcome distribution did
those probabilities imply?

For example, replaying the 2026 Finals before Game 4 uses:

```text
as_of_date: 2026-06-10
completed series games: Games 1-3
observed series score: SAS 1-2 NYK
next game: Game 4, NYK home
excluded information: Game 4 and all later results and box scores
```

## Chosen Approach

### Historical Replay

The user supplies:

- two playoff teams
- the home-court owner
- an `as_of_date`
- season context
- simulation count and random seed

The application reconstructs the current series score from canonical playoff
games strictly before `as_of_date`. The user cannot override that observed
score in Historical Replay.

### Frozen Venue Probabilities

The application constructs two scheduled matchup snapshots at the same
`as_of_date`:

1. home-court owner hosting the opponent
2. opponent hosting the home-court owner

It scores each snapshot once with the frozen model bundle. The resulting two
venue-specific probabilities remain fixed throughout Monte Carlo simulation.

This is the smallest defensible integration because sampled wins do not
provide the future box scores needed to update rolling offensive, defensive,
or net-rating features. Dynamically changing only Elo or win percentage would
mix incompatible feature timestamps.

### Hypothetical Scenarios

The existing Assumption Lab remains the place for user-entered probabilities
and imagined scenarios. Historical Replay never labels a manually entered
series score as observed history.

## Evidence and Assumptions

### Observed Evidence

- Completed series games before `as_of_date`
- Reconstructed current series score
- Home-court order
- Canonical game and box-score history available before the cutoff
- Frozen-model probabilities computed from that history

### Explicit Assumptions

- Future simulated games are conditionally independent given the two frozen
  venue probabilities.
- Venue probabilities do not update after sampled future games.
- Elimination-game pressure, momentum, injuries, rotations, and psychological
  effects receive no manual adjustment.

The observed current score is always conditioned on. Psychological or
elimination-game adjustments require a separate historical feature experiment
before they may alter game probabilities.

## Series Reconstruction Contract

Canonical games currently do not contain a source `series_id`. The replay
application therefore identifies completed series games using:

- `season_key` equal to the requested season
- `season_type == "Playoffs"`
- the unordered pair of requested team IDs
- `game_date < as_of_date`

Games are sorted by `game_date` and `game_id`.

The reconstruction validates:

- no more than seven matching games
- neither team has more than four wins
- no matching game occurs after either team reached four wins
- the number of completed games equals the sum of reconstructed wins
- each observed game's home team matches the NBA `A, A, B, B, A, B, A`
  schedule for the declared home-court owner
- the next game number is between one and seven when the series is active

If the selected teams have no matching playoff game before the cutoff, replay
starts at `0-0` before Game 1. If the selected series is already complete,
the application reports the observed winner and final length, leaves the
remaining-series simulation empty, and does not score future matchup
probabilities.

The lack of a canonical `series_id` is an explicit limitation. If future data
supports multiple postseason series between the same teams in one season, the
contract must add a stable series identifier instead of guessing.

## Alternatives Considered

### Fix the Product to the Current `3-1` Finals State

Rejected because it cannot replay Game 1, Game 4, or another playoff series.
The observed score must be derived from the requested cutoff rather than
hard-coded around the current day.

### Let Users Enter the Historical Replay Score

Rejected because a manual score can contradict canonical history and the
cutoff. User-entered scores remain appropriate only in the explicitly
hypothetical Assumption Lab.

### Dynamically Update Features After Simulated Games

Rejected for this milestone because sampled wins do not include the box scores
required to update rolling offensive, defensive, and net ratings. Updating
only some features would mix incompatible time states.

### Add an Elimination-Game Probability Adjustment

Rejected until a separate historical experiment measures whether an
elimination-game feature improves validation probability quality. Current
series score is observed evidence; psychological effects are unmeasured.

## Remaining-Series Simulation Contract

The simulation engine accepts initial observed wins for Team A and Team B.
Team A remains the home-court owner.

The next simulated game uses index:

```text
initial_team_a_wins + initial_team_b_wins + 1
```

The engine skips already completed schedule positions and stops when either
team reaches four total wins.

The remaining-series simulator accepts active scores only. It rejects an
initial score where either team already has four wins; completed-series
reporting belongs to the reconstruction application rather than Monte Carlo.

Outcome labels always describe the final series result, including observed
games. From `Team A 1-3 Team B`, valid outcomes are:

```text
Team B in 5
Team B in 6
Team B in 7
Team A in 7
```

Impossible outcomes retain zero probability in the normalized report.

## Model-Backed Application Workflow

Create a focused `application.series_replay` module responsible for:

1. validating replay inputs
2. reconstructing observed series state
3. building the two venue-direction scheduled matchups
4. scoring both matchups with the frozen model
5. supplying fixed probabilities to the model-independent simulator
6. returning chart-ready tables and an auditable report

The simulator remains unaware of pandas, canonical games, feature generation,
or model bundles.

```text
canonical games + replay inputs + frozen model
        |
        v
observed series reconstruction at as_of_date
        |
        v
two scheduled matchup snapshots at same cutoff
        |
        v
frozen home-direction probabilities
        |
        v
remaining best-of-seven Monte Carlo simulation
        |
        v
auditable replay report + UI tables
```

## Scheduled Matchup Dates

The feature snapshot requires a scheduled game date to calculate rest days.
Historical Replay uses the next known NBA home-court schedule position but
does not yet have an automated schedule source.

The user therefore supplies:

- the next game's scheduled date

Both venue-direction probability snapshots use that same date and cutoff.
This intentionally answers: “With the state available at this cutoff and the
rest interval before the next game, how would either venue affect the
probability?”

Future games after the next game reuse these frozen probabilities; their
specific future rest days are not modeled.

## CLI Contract

Add a `replay-series` command that accepts:

- games Parquet path
- model bundle path
- `as_of_date`
- next game date
- season ID, season type, and season key
- Team A and Team B IDs and abbreviations
- home-court owner as Team A
- simulations, seed, and output directory

It writes `artifacts/reports/model_backed_series_replay.json`.

The report includes:

- replay timestamp and cutoff
- model and feature versions
- reconstructed observed games and score
- next game number and venue
- both frozen venue probabilities
- exact feature values used for both probability directions
- Monte Carlo result and assumptions

## Streamlit Contract

Keep one Streamlit app with two clearly labeled tabs:

### Model-Backed Historical Replay

- defaults to the current 2026 Finals context when local artifacts exist
- lets users select `as_of_date` and next-game date
- reconstructs and displays observed series games and current score
- displays both frozen venue probabilities
- displays remaining-series win, outcome, and length distributions
- states that psychological effects and future feature updates are not modeled

### Assumption Lab

- preserves the existing manual probability controls and outputs
- remains explicitly hypothetical

If local data or model artifacts are missing, the model-backed tab shows an
actionable message while the Assumption Lab remains usable.

## Point-in-Time and Leakage Rules

- Observed series reconstruction uses only playoff games with
  `game_date < as_of_date`.
- Both venue-direction model snapshots use the same strict cutoff.
- Changing the result or box score of a game on or after `as_of_date` cannot
  change reconstructed state, frozen probabilities, or simulation output.
- The observed current score is derived from data, never user-entered.
- Historical Replay cannot use a next game date before `as_of_date`.

## Testing Strategy

### Simulation Engine

- starts at an arbitrary valid score such as `1-3`
- skips completed schedule positions
- rejects a supplied score that is already complete
- reports only reachable winner-in-N outcomes with nonzero probability
- rejects impossible scores and completed-game counts

### Series Reconstruction

- reconstructs `0-0`, mid-series, and completed-series states
- excludes games on and after the cutoff
- rejects invalid or post-completion histories

### Model-Backed Workflow

- scores exactly two venue directions at one cutoff
- uses reconstructed score rather than a user-supplied score
- preserves historical parity with standalone matchup predictions
- proves future-result mutation cannot change output
- records model, feature, cutoff, probability, and simulation assumptions

### CLI and UI

- CLI report matches the shared application workflow
- Streamlit renders both tabs
- missing local artifacts do not break the Assumption Lab
- current Finals replay renders without application exceptions

Automated tests remain network-free. Live local artifacts support a separate
2026 Finals smoke verification.

## Documentation and Claims

Update the README, architecture, runbook, simulation decision record, model
card, and leakage-prevention documentation in the same work unit.

Permitted claim:

> Reconstructs an NBA playoff series at a declared historical cutoff, scores
> frozen model probabilities using only information then available, and
> simulates the remaining series from the observed score.

Prohibited claims:

- measured playoff predictive accuracy
- modeled momentum or psychological pressure
- dynamic future team-state updates
- injury-aware probabilities

## Success Criteria

1. Any valid active-series cutoff can be reconstructed from canonical playoff
   games.
2. Game 4 replay excludes Game 4 and later results.
3. Remaining simulation begins at the correct observed score and schedule
   position.
4. Exactly two auditable frozen venue probabilities power the simulation.
5. Historical Replay and Assumption Lab are clearly separated in CLI/UI copy.
6. Current Finals replay works from local refreshed artifacts.
