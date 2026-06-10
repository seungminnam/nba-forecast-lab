# ADR 0001: Use Parquet and DuckDB for Analytical Storage

**Status:** Accepted  
**Date:** 2026-06-10

## Context

The MVP needs reproducible local analytics, portable artifacts, SQL inspection,
and low operational overhead. A hosted transactional database would add
deployment work before it provides portfolio value.

## Decision

Use Parquet as the durable processed-table format and DuckDB as the local SQL
query layer. Preserve source responses as immutable raw CSV extracts with
metadata.

## Consequences

- Historical builds and tests can run locally without a database service.
- Processed tables remain portable and easy to inspect.
- DuckDB can query Parquet directly and support dashboard preparation.
- Concurrent writes and hosted application persistence are intentionally
  deferred. A managed database can be reconsidered if daily operation requires
  it.

## Implemented Paths

Given a configured data output directory, Phase 0/1 writes:

```text
processed/games.parquet
nba_forecast.duckdb
```

The processed writer validates the canonical table before either artifact is
updated.

## Runtime Compatibility Note

The project pins NumPy below version 2 for compatibility with the local macOS
Python 3.9 analytical stack. NumPy 2.0.2 emitted incorrect matrix-multiplication
RuntimeWarnings despite finite, bounded inputs and coefficients during
Logistic Regression prediction.
