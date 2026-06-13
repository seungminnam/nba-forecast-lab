# Decision 0002: Best-of-Seven Simulation Contract

## Status

Accepted for the initial playoff series simulator.

## Context

The forecasting model emits a probability for one scheduled game's home team.
A playoff product must convert those game-level probabilities into a
distribution over best-of-seven series outcomes without coupling the
simulation engine to a specific model implementation.

## Decision

- Treat `team_a` as the home-court owner.
- Use NBA best-of-seven home order `A, A, B, B, A, B, A`.
- Accept a probability-provider callable that receives the current game
  number, home team, away team, and pre-game series score, then returns the
  home team's win probability.
- Accept an active observed series score and simulate only remaining schedule
  positions.
- Stop each sampled series immediately when either team reaches four wins.
- Use 10,000 simulations by default and support a supplied random seed.
- Report:
  - each team's series win probability
  - winner-in-4/5/6/7 outcome probabilities
  - series-length probabilities
  - expected series length

The provider boundary keeps the engine model-independent. Tests and examples
may use fixed probabilities; the application layer will later provide
probabilities from prepared model features and the frozen model bundle.

## Assumptions and Limitations

- Sampled game outcomes are conditionally independent given the probability
  supplied for each game context.
- The engine itself does not update team features, injuries, rotations, or
  fatigue after a sampled game.
- Historical Replay freezes two model-derived venue probabilities at the
  declared cutoff. Observed score is conditioned on, but psychological or
  elimination-game adjustments are not applied without measured evidence.
- A context-aware provider may vary probability by venue, game number, or
  current series score, but those adjustments require evidence outside the
  simulator.
- Monte Carlo simulation is a downstream decision layer, not another machine
  learning model.

## Alternatives Considered

- **Pass one constant series probability:** rejected because it cannot
  represent the NBA home-court schedule.
- **Embed model inference inside the simulator:** rejected because it couples
  simulation tests and reuse to one model artifact.
- **Enumerate every possible series path exactly:** mathematically possible
  for a single series, but Monte Carlo is retained because the same interface
  can later extend to brackets and context-dependent probabilities.
