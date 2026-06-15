# Finals Retrospective and Reusable Playoff Backtest Design

Proposed on 2026-06-15.

## Context

The frozen pre-Game-5 workflow estimated:

- SAS Game 5 win probability: `54.57%`
- NYK Game 5 win probability: `45.43%`
- NYK series win probability: `86.21%`
- expected final series length: `5.80` games

On June 13, 2026, NYK won Game 5 `94-90` and completed a `4-1` Finals
victory. The committed forecasting snapshot ends on June 10, 2026, so the
actual Game 5 result must not be inserted into the pre-game feature snapshot.

The project now needs to:

1. present the completed Finals as an honest forecast retrospective;
2. preserve the original pre-Game-5 prediction as reproducible evidence; and
3. define a reusable playoff evaluation workflow that can forecast and
   evaluate the 2026-27 playoffs and later seasons.

## Decision

Build the Finals retrospective and the reusable playoff backtest as separate
layers.

- The retrospective joins one frozen forecast record to one verified outcome
  record for presentation.
- The playoff backtest will generate a forecast independently at every
  historical pre-game cutoff, then join outcomes only after prediction.
- Historical Replay remains the interactive single-series reconstruction
  workflow.

This separation prevents observed results from contaminating pre-game
features and avoids turning the UI into a one-off 2026 Finals artifact.

## Alternatives Considered

### Replace the Forecast Card with a Static Championship Result

Rejected. This hides the original forecast and removes the most useful
probability-interpretation lesson.

### Refresh the Snapshot Through Game 5 and Recompute the Same Forecast

Rejected. A snapshot containing Game 5 cannot be used to reproduce a
pre-Game-5 forecast. That would violate the point-in-time contract.

### Build the Full Playoff Backtest in the Same Work Unit

Rejected for this PR. A season-wide backtest requires a refreshed canonical
dataset, prediction persistence, chronological evaluation, and new reports.
It is a separate reviewable experiment. This design defines its contract now,
but implementation follows in the next PR.

## Retrospective Data Contract

Add a presentation-focused application module:

```python
@dataclass(frozen=True)
class ForecastOutcome:
    game_id: str
    game_date: pd.Timestamp
    home_team_abbreviation: str
    away_team_abbreviation: str
    home_points: int
    away_points: int
    final_team_a_wins: int
    final_team_b_wins: int


@dataclass(frozen=True)
class ForecastRetrospective:
    forecast: SeriesReplayOutput
    outcome: ForecastOutcome
    predicted_game_winner: str
    actual_game_winner: str
    predicted_series_winner: str
    actual_series_winner: str
    game_brier_score: float
```

The outcome is a small explicit verified record, not a replacement for the
canonical games dataset. The retrospective builder validates:

- forecast and outcome team abbreviations match;
- outcome date equals the forecasted next-game date;
- final series score has exactly one four-win team;
- actual Game 5 winner agrees with the final series winner when the series
  ends in Game 5.

Game Brier Score uses the forecasted home-win probability and actual home-win
indicator:

```text
(0.5457 - 0)^2 = approximately 0.2978
```

This is one forecast's score, not a claim about playoff model accuracy.

## Dashboard Design

Keep the existing four-tab layout and Historical Replay defaults. Replace the
hero's featured historical forecast card with:

```text
2026 FINALS FORECAST RETROSPECTIVE

Frozen pre-Game 5 forecast      Actual outcome
SAS win 54.57%                  NYK won 94-90
NYK win 45.43%                  NYK won series 4-1
NYK series win 86.21%           Series ended in 5 games

Interpretation:
The game-level favorite lost, while the strongly favored series winner won.
```

The card must explicitly state:

- forecast cutoff: June 11, 2026;
- outcome date: June 13, 2026;
- the single-game Brier result is descriptive, not a playoff-accuracy claim;
- the frozen prediction was not modified after observing the result.

If the frozen snapshot or model is unavailable, render the existing
non-retrospective hero without broken state or fabricated forecast values.

## Reusable Playoff Forecast Contract

The next implementation milestone will add a generic playoff backtest service
that accepts a season rather than hard-coded Finals teams:

```python
@dataclass(frozen=True)
class PlayoffBacktestInput:
    season_key: str
    season_id: str
    model_bundle_path: Path
    simulations: int = 10_000
    seed: int = 2026
```

For every completed playoff game in the requested season:

1. set `as_of_date` to the game's date;
2. build features using only games with `game_date < as_of_date`;
3. score the actual scheduled home-away matchup;
4. persist the probability before reading the result;
5. join the observed result for evaluation;
6. calculate game-level probability metrics.

For every playoff series:

1. reconstruct the series before each game;
2. produce the remaining-series win distribution;
3. preserve the probability assigned to the eventual series winner;
4. evaluate series forecasts separately from game forecasts.

The service must not contain team abbreviations, dates, or bracket structure
specific to 2026. The 2026 playoffs become the first measured replay, while
2026-27 and later playoffs use the same interface.

## Future Season Operation

The reusable workflow has two modes.

### Historical Backtest Mode

Uses a completed season and produces a fully measured report. This mode is for
research, model comparison, and portfolio evidence.

### Forward Forecast Mode

During a future playoff season:

1. ingest completed games through the previous day;
2. create predictions for scheduled games;
3. write immutable timestamped prediction records;
4. update series simulations;
5. attach outcomes only after games finish.

Forward predictions must be stored before outcomes are available. This
provides auditable evidence that forecasts were genuinely made pre-game.

## Evaluation Contract

Game-level primary metrics:

- Brier Score
- Log Loss
- Expected Calibration Error

Secondary metrics:

- ROC-AUC
- Accuracy

Slices:

- playoff round;
- home and away;
- probability bucket;
- elimination and non-elimination games;
- series game number.

Series-level reporting:

- probability assigned to the eventual winner before each game;
- series winner accuracy at defined cutoffs;
- predicted and observed series length;
- championship probability path when a complete bracket simulator exists.

The 2026 playoff backtest is a new evaluation dataset. It must not be used to
modify the frozen model and then reported as unbiased evaluation. Any feature
or model selection inspired by its results must be evaluated on later
walk-forward seasons.

## Testing

Retrospective tests must verify:

- the frozen Game 5 forecast remains unchanged;
- the verified outcome yields NYK as Game 5 and series winner;
- game Brier Score is calculated from the SAS home-win probability;
- mismatched teams, dates, and invalid final series scores are rejected;
- dashboard copy distinguishes forecast, outcome, and interpretation;
- snapshot-missing fallback remains functional.

Future backtest tests must verify:

- each prediction excludes the game being predicted and all later games;
- predictions are emitted in chronological order;
- outcomes are joined only after prediction creation;
- arbitrary season and team inputs work without 2026-specific constants;
- game-level and series-level metrics are calculated separately.

## Documentation

This work unit updates:

- `README.md` with the completed Finals retrospective and careful
  interpretation;
- `docs/experiments.md` with the pre-registered playoff backtest hypothesis
  and evaluation contract;
- `docs/runbook.md` with retrospective reproduction instructions;
- the dashboard with the retrospective presentation.

The next playoff-backtest implementation appends measured results rather than
replacing the original forecast record.

## Success Criteria

- The first dashboard screen explains both the pre-Game-5 forecast and actual
  outcome without presenting either as live.
- The original forecast remains reproducible from the June 10-11 snapshot.
- Actual Game 5 data cannot enter the forecast feature snapshot.
- Documentation explains why a `45.43%` NYK game probability and an `86.21%`
  NYK series probability are not contradictory.
- The next milestone has a season-agnostic contract suitable for the 2026-27
  playoffs and later seasons.
