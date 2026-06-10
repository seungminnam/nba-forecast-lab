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

