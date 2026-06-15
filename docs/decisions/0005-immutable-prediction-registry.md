# ADR 0005: Local-First Immutable Prediction Registry

## Status

Accepted on 2026-06-15.

## Context

Forward predictions must be preserved before outcomes are known so operating
performance can be measured honestly. Overwriting one latest prediction per
game would erase earlier model versions, feature snapshots, and forecast
timestamps. Daily automation is also difficult to debug before a reliable
manual operating workflow exists.

## Decision

- Preserve one immutable event for each
  `game_id + model_version + prediction_timestamp`.
- Treat identical event reprocessing as idempotent and reject a conflicting
  payload with the same identity.
- Permit only outcome-derived settlement fields to change after registration.
- Use Parquet as the durable registry and rebuildable DuckDB as the SQL query
  surface.
- Implement and verify manual register, settle, and report commands before
  adding daily automation or hosted storage.

## Alternatives Considered

### Overwrite the latest prediction for each game

Rejected because it destroys point-in-time evidence and prevents forecast-
horizon and model-version comparisons.

### Start with Supabase or another hosted database

Deferred because authentication, migrations, and network-dependent operations
would precede proof of the core registry contract.

### Add GitHub Actions in the same work unit

Deferred so schedule ingestion, artifact persistence, and failure recovery do
not obscure registry correctness.

## Consequences

- Multiple legitimate prediction events may exist for one game.
- Registry size grows append-first, but each forecast remains auditable.
- Exact forecast-horizon analysis remains deferred until tip-off timestamps
  are available.
- The current workflow is local and manual, not a live automated service.
- A hosted adapter can later reuse the application-level identity, settlement,
  and reporting rules.
