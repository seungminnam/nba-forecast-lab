# Simulator Lab UI Design

## Goal

Provide the first directly inspectable product surface for NBA Forecast Lab.
Users can change explicit game-probability assumptions and immediately inspect
best-of-seven Monte Carlo outcomes.

This first UI is an assumption-based simulator demonstration. It must not
present synthetic inputs as frozen-model NBA predictions.

## Chosen Approach

Build one Streamlit page backed by a reusable Python view-model function and a
matching CLI JSON-report command.

This approach is preferred over a multi-page Streamlit shell because only the
simulator has a complete interactive workflow today. It is preferred over a
Next.js frontend because it connects directly to the existing Python engine
with less deployment and API complexity.

## User Flow

1. Enter Team A and Team B names.
2. Treat Team A as the home-court owner.
3. Set Team A's win probability when Team A hosts.
4. Set Team A's win probability when Team B hosts.
5. Set simulation count and random seed.
6. Run the simulation.
7. Inspect:
   - team series-win probabilities
   - expected games
   - outcome probabilities by winner and series length
   - series-length distribution

## Components

- `nba_forecast.application.simulator_lab`
  - validates user inputs
  - converts Team A venue-specific probabilities into the simulator's required
    home-team probability provider
  - returns normalized tables used by both CLI and UI
- `nba-forecast simulate-series`
  - accepts explicit assumption inputs
  - writes a machine-readable JSON report
- `streamlit_app.py`
  - renders the single-page Simulator Lab
  - clearly labels the result as assumption-based
  - calls the application function without training or loading a model

## Visual Design

- Dark navy page background with high-contrast white text
- Blue and orange accents for Team A and Team B
- Compact assumption panel at the top
- Three headline result cards
- Horizontal bar charts for series outcomes and length distribution
- Methodology and current-limitations expander below the results

## Error Handling

- Team names must be non-empty and distinct.
- Probabilities must be between 0 and 1.
- Simulation count must be positive.
- UI errors are shown without crashing the application.
- CLI errors fail with actionable messages.

## Testing and Verification

- Unit-test input validation and probability-provider conversion.
- Test that CLI output matches the shared application result.
- Start Streamlit against local code and verify controls, labels, result cards,
  charts, and absence of console errors in the in-app browser.
- Run `ruff check .`, `mypy src`, and `pytest`.

## Deferred Work

- Scheduled-game feature generation
- Frozen-model matchup probabilities
- Today's Games, Performance, and Methodology pages
- Hosted deployment
