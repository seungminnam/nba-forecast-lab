# Season-Agnostic Playoff Backtest Design

Proposed on 2026-06-15.

## Goal

Evaluate the frozen game-probability model across every completed playoff game
in an arbitrary season using only information available before each game.

The first measured run targets the completed 2025-26 playoffs. The same
application interface must support 2026-27 and later playoff seasons without
team or date constants.

## Scope

This work unit implements the game-level chronological backtest:

- select all completed playoff games for one `season_key`;
- reconstruct and score each actual matchup at its game-date cutoff;
- attach the observed result only after prediction creation;
- calculate aggregate probability metrics;
- expose a CLI report and document the measured 2025-26 result.

Series-path and full-bracket evaluation remain separate follow-up layers. They
depend on the immutable game-level prediction table produced here.

## Input and Output Contract

```python
@dataclass(frozen=True)
class PlayoffBacktestInput:
    season_key: str
    season_id: str


@dataclass(frozen=True)
class PlayoffBacktestOutput:
    inputs: PlayoffBacktestInput
    model_version: str
    feature_version: str
    predictions: pd.DataFrame
    metrics: dict[str, float]
```

Each prediction row contains:

- game identity and date;
- season identity;
- home and away team identity;
- model and feature version;
- home and away win probability;
- observed `home_win`;
- Brier contribution;
- whether the predicted winner was correct.

The output table is sorted by `game_date`, then `game_id`.

## Temporal Contract

For every target game:

1. copy only the target game's schedule identifiers into `ScheduledMatchup`;
2. call `predict_scheduled_matchup` with `as_of_date = game_date`;
3. allow the existing snapshot builder to retain only
   `history.game_date < as_of_date`;
4. create the prediction record;
5. then attach the target game's `home_win`.

The target row and all future games may exist in the input canonical frame,
but they cannot enter the generated feature row. Same-day games remain
conservatively excluded because the canonical contract does not preserve
tip-off timestamps.

## Validation

Reject:

- empty canonical input;
- missing canonical columns;
- seasons with no playoff games;
- inconsistent `season_id` / `season_key`;
- duplicate game IDs;
- incomplete target outcomes;
- target probabilities outside `[0, 1]`.

The backtest must not accept a different model per game. One frozen bundle is
used for the entire requested season.

## Evaluation

Aggregate game-level metrics reuse `probability_metrics`:

- Brier Score;
- Log Loss;
- Expected Calibration Error;
- ROC-AUC;
- Accuracy.

The prediction table also stores each game's Brier contribution, allowing
later dashboard slices and error analysis without rerunning the model.

The first 2025-26 playoff result evaluates the already-frozen model. It must
not be used to modify that model and then be reported again as unbiased
performance.

## CLI

Add:

```text
nba-forecast backtest-playoffs \
  --games-parquet data/processed/games.parquet \
  --model-bundle artifacts/models/2026-06-11-recent5-raw.joblib \
  --season-key 2025-26 \
  --season-id 42025 \
  --output-dir .
```

Write:

- `artifacts/reports/playoff_backtest_predictions.csv`
- `artifacts/reports/playoff_backtest_metrics.json`

## Data Refresh Requirement

The current processed dataset ends on June 10, 2026 and contains 84 playoff
games. Before publishing the final measured 2025-26 result, refresh the
2025-26 playoff source and rebuild canonical games so Finals Game 5 is
included.

Refreshing the processed evaluation dataset does not replace the committed
June 10 frozen deployment snapshot, which must continue to reproduce the
pre-Game-5 forecast.

## Testing

Tests must prove:

- an arbitrary season is selected without 2026 team constants;
- target and future result mutations cannot change earlier predictions;
- predictions are chronological;
- attached outcomes and per-game Brier contributions are correct;
- aggregate metrics match direct `probability_metrics` calculation;
- missing season, duplicate IDs, and incomplete outcomes are rejected;
- CLI reports are written with the expected schema.

## Success Criteria

- One command evaluates every completed playoff game in an arbitrary season.
- Every prediction is leakage-safe under the existing date-level contract.
- The 2025-26 completed playoff report is reproducible and documented.
- The prediction table can later power series-path analysis, daily monitoring,
  and a season-aware dashboard.
