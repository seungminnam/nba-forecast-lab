# Next-Game Probability and Fair Odds Display Design

## Goal

Make the next scheduled playoff game's model probability directly visible
inside Historical Replay and provide clearly labeled model-implied fair odds.

This is an application and presentation feature. It does not change the
frozen model, feature set, calibration, or measured performance.

## User Question

Given an observed active series such as `SAS 1-3 NYK` before Game 5:

- which team hosts the next game?
- what probability does the frozen model assign to each team winning that
  game?
- what are the corresponding no-margin model-implied fair odds?

## Chosen Approach

Historical Replay already scores both possible venue directions at the same
cutoff. The application will select the prediction whose home team matches the
reconstructed `next_home_team_id` and expose it as a focused
`NextGameForecast`.

The forecast includes:

- next game number and date
- home and away team IDs and abbreviations
- home and away win probabilities
- decimal fair odds for both teams
- American fair odds for both teams

The CLI JSON report and Streamlit UI consume the same application object.

## Fair Odds Contract

Fair odds are a deterministic display transform of model probability. They
are not observed sportsbook prices and do not include bookmaker margin.

For probability `p` where `0 < p < 1`:

```text
decimal_odds = 1 / p

american_odds =
    -100 * p / (1 - p), when p > 0.5
     100 * (1 - p) / p, when p <= 0.5
```

American odds are rounded to the nearest integer for display. Decimal odds are
stored at full precision and formatted to two decimals in the UI.

Probabilities equal to zero or one are rejected because they do not have
finite two-sided fair odds.

## Product Language

Use the label **Model-Implied Fair Odds**.

Every UI and report representation must make these boundaries explicit:

- `market_odds = false`
- `includes_bookmaker_margin = false`
- `betting_recommendation = false`

The UI states:

> Model-implied fair odds are a no-margin transformation of the displayed
> probabilities, not sportsbook prices or betting advice.

## Completed-Series Behavior

If the reconstructed series is complete:

- `next_game_forecast` is absent
- no next-game win probabilities or fair odds are displayed
- the observed winner remains available through Historical Replay

## Alternatives Considered

### Calculate Odds Only in Streamlit

Rejected because CLI reports and other consumers would not share the same
contract, and presentation code would own domain logic.

### Add a Separate Next-Game Model Call

Rejected because Historical Replay already scores both venue directions. A
third call would duplicate inference and could create inconsistent timestamps.

### Integrate Live Sportsbook Odds

Deferred. It requires a licensed external source, precise collection
timestamps, margin removal, and a separate comparison design. It would also
change the product from probability communication toward market analysis.

## Testing Strategy

- known probabilities produce expected decimal and American fair odds
- zero and one probabilities are rejected
- pre-Game-5 replay selects the Team A-home direction when Team A hosts
- a replay where Team B hosts selects the Team B-home direction
- completed series returns no next-game forecast
- JSON includes explicit non-market and non-betting flags
- Streamlit renders next-game team probabilities and fair-odds labels

## Documentation and Claims

Permitted claim:

> Displays the frozen model's next-game win probabilities and their
> model-implied no-margin fair-odds equivalents.

Prohibited claims:

- actual market or sportsbook odds
- profitable betting signal
- betting recommendation
- improved predictive performance from the odds transform

## Success Criteria

1. Historical Replay automatically selects the actual next game's venue
   prediction.
2. Both teams' next-game probabilities and fair odds are available in the
   shared application output and JSON report.
3. The UI clearly separates next-game probability from remaining-series
   probability.
4. Completed series display no next-game forecast.
5. Documentation states that this is a probability display transform, not a
   model improvement or betting product.
