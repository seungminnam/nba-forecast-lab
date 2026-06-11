# NBA Stats Source Report

**Source:** NBA Stats API through `nba_api`  
**Endpoint:** `LeagueGameFinder`  
**Initial live verification date:** 2026-06-10

## Purpose

Phase 0/1 uses `LeagueGameFinder` to retrieve source-shaped team-game records.
Each completed game should normally produce two records, one for each team.
The raw response is cached before transformation.

## Verified Request

```text
Season: 2025-26
Season type: Regular Season
Source team-game rows: 2,460
Canonical completed games: 1,230
Canonical date range: 2025-10-21 through 2026-04-12
```

The live extract was used only as a smoke test and was written outside the Git
repository. Generated raw and processed data remain excluded from version
control.

## Historical Backfill

On 2026-06-10, the cache-first history workflow fetched all regular seasons
from 2015-16 through 2025-26:

```text
Raw files: 11
Source team-game rows: 26,418
Canonical games: 13,209
Canonical date range: 2015-10-27 through 2026-04-12
```

Season game counts:

| Season ID | Games |
|---|---:|
| 22015 | 1,230 |
| 22016 | 1,230 |
| 22017 | 1,230 |
| 22018 | 1,230 |
| 22019 | 1,059 |
| 22020 | 1,080 |
| 22021 | 1,230 |
| 22022 | 1,230 |
| 22023 | 1,230 |
| 22024 | 1,230 |
| 22025 | 1,230 |

The shortened 2019-20 and 2020-21 seasons reflect the real NBA schedules.

## 2025-26 Playoff Refresh

On 2026-06-11, the cache-first source workflow fetched completed 2025-26
playoff games:

```text
Season type: Playoffs
Source team-game rows: 168
Canonical completed games: 84
Canonical date range: 2026-04-18 through 2026-06-10
Source season ID: 42025
Shared season key: 2025-26
```

Combining the playoff cache with the 11 regular-season caches produced:

```text
Canonical games: 13,293
Unique game IDs: 13,293
Canonical date range: 2015-10-27 through 2026-06-10
```

All four April 18 first-round games showed `games_played=82` for both teams
before tip-off. This verifies that rolling team state continued from the
regular season rather than resetting at the `22025` to `42025` source-ID
boundary.

## Observed Source Anomaly

For `GAME_ID 0022500602`, both source rows contained the same matchup string:

```text
ORL @ MEM
```

The home team cannot therefore be identified by assuming only the home team's
row contains `vs.`. The canonical transformation parses the home abbreviation
from either `HOME vs. AWAY` or `AWAY @ HOME`, then compares that abbreviation
with each row's team abbreviation. A regression test preserves this behavior.

## Limitations and Operational Notes

- NBA Stats availability and response time can vary.
- The API may rate-limit or reject requests, so normal builds should reuse raw
  cache files rather than repeatedly fetching.
- Source fields and historical coverage must be rechecked before adding
  advanced-stat features.
- A successful fetch does not imply valid canonical data; transformation and
  validation must complete before processed artifacts are accepted.
- Player availability and injury data are not provided by this Phase 0/1
  source contract.
- The current refresh combines `Regular Season` and `Playoffs`; it does not
  yet ingest Play-In tournament games.
- The current measured model comparison and final model evaluation use
  regular-season games only. The playoff cache supports current inference but
  does not establish playoff predictive accuracy.
