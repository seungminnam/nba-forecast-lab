# ADR 0006: Schedule Source and Daily Prediction Horizon

## Status

Accepted.

## Context

The project needs a forward-looking workflow that can discover scheduled NBA
games, score only games that are still eligible before tip-off, and preserve
the resulting predictions in the local registry. This workflow must remain
point-in-time safe and explainable before adding hosted persistence or
automation.

## Decision

Use `ScheduleLeagueV2` as the schedule discovery source and preserve each
fetch as an immutable timestamped snapshot. Transform supported `002` regular
season and `004` playoff rows into a canonical scheduled-matchup table.

The first operating horizon is one NBA calendar date at a time. A daily batch
selects rows for that date only when they are not started, not postponed, not
conditional, have confirmed teams, have a known UTC tip-off, and the tip-off
is still in the future at the prediction timestamp.

Incomplete schedule evidence is preserved in the canonical schedule but is not
predicted. Unknown teams, missing tip-offs, conditional games, and unknown
nonnegative statuses remain auditable source evidence for later inspection.

GitHub Actions scheduling and hosted persistence are intentionally deferred.
The current workflow is manual and local: Parquet is authoritative, DuckDB is
the query surface, and the local registry records prediction evidence.

## Rationale

`ScheduleLeagueV2` exposes full-season schedule context, including future and
conditional games. `ScoreboardV2` is useful for near-real-time scoreboard
views, but it is narrower and less suitable for building an auditable season
schedule artifact.

A once-daily horizon is easier to verify than a live or rolling intraday
system. It matches the model's pre-game feature contract and gives each
prediction batch one shared timestamp and one shared schedule snapshot.

Preserving incomplete rows avoids silently rewriting the source. Excluding
them at eligibility time keeps the prediction layer honest: the model only
scores matchups with enough pre-tipoff identity and timing information.

Hosted persistence and cron jobs require a separate reliability design because
GitHub Actions runners are ephemeral. Adding automation before the local
contract is proven would blur failure modes.

## Consequences

- Manual operators can fetch, build, predict, inspect, and recover locally.
- The batch report can disclose the exact schedule snapshot used.
- No-game days produce empty prediction reports rather than fake predictions.
- The project still needs a future PR for hosted storage, scheduled execution,
  and deployed daily views.
