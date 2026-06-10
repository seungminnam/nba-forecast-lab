# NBA Forecast Lab: Project Brief and Implementation Prompt

## 1. Project Overview

Build an independent, end-to-end machine learning project that predicts NBA
game win probabilities and uses those probabilities to simulate playoff series
and championship outcomes.

The project is intended to be a strong portfolio piece for internships in:

- Data Science
- Machine Learning Engineering
- Data Engineering
- Applied AI

Existing open-source NBA prediction repositories may be studied, reproduced,
and used as benchmarks. However, the final project must be implemented in an
independent repository rather than presented as a simple fork.

### Working Title

**NBA Forecast Lab: Calibrated Game Predictions and Playoff Simulator**

### Primary Research Question

> Using only information available before tip-off, how accurately can an NBA
> game's win probability be predicted, and how can those calibrated
> probabilities be used to simulate playoff series and championship outcomes?

---

## 2. Core Product

The final system should:

1. Automatically collect and validate NBA game data.
2. Create leakage-safe, pre-game features.
3. Train and compare multiple prediction models.
4. Produce calibrated win probabilities for upcoming games.
5. Simulate playoff series and full playoff brackets.
6. Display predictions, explanations, and historical performance in a deployed
   dashboard.
7. Automatically evaluate predictions after games finish.

### High-Level Pipeline

```text
NBA data ingestion
    -> data validation and storage
    -> leakage-safe feature generation
    -> model training and calibration
    -> daily game predictions
    -> playoff Monte Carlo simulations
    -> dashboard and performance monitoring
```

---

## 3. Portfolio Strategy

Do not copy an existing repository and only add a small feature.

Instead:

1. Study and reproduce selected open-source projects.
2. Document their data, features, validation methods, and limitations.
3. Use their results as benchmarks when reproducible.
4. Independently design and implement the final system.
5. Quantify improvements using appropriate probability metrics.
6. Clearly document which ideas were inspired by external projects.
7. Optionally contribute a separate bug fix or improvement upstream.

The portfolio story should be:

> I reproduced and evaluated existing NBA prediction approaches, identified
> limitations such as weak temporal validation or probability calibration, and
> independently built a leakage-safe forecasting and playoff simulation system.

### Primary Benchmark

- [cmunch1/nba-prediction](https://github.com/cmunch1/nba-prediction)

Use it as a reference for end-to-end ML design, automation, modeling, and
deployment. Do not copy its implementation without checking its license and
providing attribution.

---

## 4. Scope

### Required Scope

- Pre-game NBA win probability prediction
- Time-aware model validation
- Probability calibration
- Playoff series Monte Carlo simulation
- Deployed dashboard
- Automated data updates and prediction evaluation
- Reproducible code, tests, and documentation

### Optional Scope

- Full playoff bracket and championship simulations
- Player availability or projected lineup features
- Team travel distance and fatigue features
- Comparison against market-implied probabilities
- Model drift and data quality monitoring
- Public prediction API

### Explicitly Out of Scope for the Initial Version

- Computer vision from game footage
- Shot-level success prediction
- Live, in-game win probability prediction
- Betting recommendations or claims of profitability
- Deep learning without a demonstrated reason it improves the project

These may become separate future projects after the core system is complete.

---

## 5. Data Requirements

Collect enough historical seasons to support robust temporal evaluation.
Prefer official or well-documented data sources.

Potential sources:

- `nba_api`
- Basketball Reference, subject to its usage policies
- Kaggle historical datasets for initial backfills
- Manually maintained public injury or lineup datasets, if legally usable

### Minimum Data Entities

- Games and schedules
- Final scores and results
- Team box scores
- Team advanced statistics
- Home and away teams
- Game dates and season identifiers

### Useful Additional Entities

- Player game logs
- Player minutes
- Starting lineups
- Injury or availability status
- Arena locations

### Data Storage

Start with DuckDB or Parquet for a simple local analytical workflow. Use
PostgreSQL only if it creates a meaningful portfolio benefit or is needed for
deployment.

Maintain separate layers where practical:

```text
raw data -> cleaned data -> feature tables -> predictions -> evaluation results
```

---

## 6. Leakage-Safe Feature Engineering

The most important modeling rule is:

> Every feature for a game must be calculated using only information that was
> available before that game started.

Do not calculate rolling statistics that include the target game. Apply a
one-game shift before rolling or expanding calculations.

### Initial Features

- Home-court indicator
- Team and opponent Elo ratings
- Season-to-date win percentage
- Rolling win percentage over the previous 5, 10, and 20 games
- Rolling offensive rating
- Rolling defensive rating
- Rolling net rating
- Rolling pace
- Days of rest
- Back-to-back indicator
- Recent home and away performance
- Head-to-head history available before the game
- Season progress

### Later Features

- Travel distance
- Time-zone changes
- Estimated player availability
- Rolling player minutes and team-strength estimates
- Strength of schedule

Every feature must have a documented definition and a test that guards against
future information leakage where practical.

---

## 7. Modeling Plan

### Baselines

Implement simple baselines before complex models:

1. Always predict the home team.
2. Season-to-date win percentage.
3. Elo rating model.
4. Logistic regression using engineered features.

### Candidate Models

- Regularized Logistic Regression
- XGBoost or LightGBM
- Optional Bayesian Logistic Regression

Do not add neural networks unless they outperform simpler models under the same
time-aware validation setup and offer a clear benefit.

### Probability Calibration

Compare raw and calibrated probabilities using:

- Platt scaling
- Isotonic regression
- Calibration curves

Calibration must be trained only on data that occurs before the final test
period.

---

## 8. Validation and Evaluation

Random train/test splits are prohibited because they allow future seasons or
games to influence past predictions.

### Required Validation Strategy

- Season-based holdout testing
- Walk-forward or expanding-window validation
- A final untouched out-of-time test season

Example:

```text
Train: 2012-13 through 2021-22
Validation: 2022-23
Test: 2023-24
Final forward evaluation: subsequent games
```

Adjust exact seasons based on data availability.

### Primary Metrics

1. Log Loss
2. Brier Score
3. Calibration Error and Calibration Curve
4. ROC-AUC
5. Accuracy

Accuracy must not be the primary optimization target. The system's core output
is a probability, so probability quality matters more than classification
accuracy.

### Required Comparisons

- Home-team baseline
- Win-percentage baseline
- Elo baseline
- Logistic Regression
- Tree-boosting model
- Calibrated versus uncalibrated probabilities
- Open-source benchmark results when reproducible

If market odds are added, compare predictive quality against market-implied
probabilities without presenting the project as betting advice.

---

## 9. Playoff Simulation

Use the calibrated per-game win probabilities as inputs to a Monte Carlo
playoff simulator.

### Series Simulator Requirements

- Support best-of-seven series
- Respect the NBA home-court schedule
- Recalculate game probabilities based on the game's home team
- Run at least 10,000 simulations
- Report:
  - Series win probability
  - Probability of winning in 4, 5, 6, or 7 games
  - Expected series length

### Full Bracket Simulator

If implemented, simulate each round while advancing sampled winners and report:

- Conference Finals probability
- Finals probability
- Championship probability

Monte Carlo simulation should be described as the decision and simulation layer
built on top of the ML probability model, not as the ML model itself.

---

## 10. Dashboard Requirements

Build and deploy a clean dashboard, initially using Streamlit unless another
framework provides a clear advantage.

### Page 1: Today's Games

- Today's matchups
- Calibrated win probabilities
- Model confidence or uncertainty
- Top factors influencing each prediction

### Page 2: Playoff Simulator

- Select two teams or use the current playoff bracket
- Simulate a series
- Display series win probability and outcome distribution

### Page 3: Model Performance

- Model comparison table
- Historical Brier Score and Log Loss
- Calibration curve
- Prediction results by season
- Performance over time

### Page 4: Methodology

- Problem definition
- Data sources
- Leakage prevention
- Validation design
- Model limitations
- System architecture diagram

---

## 11. Engineering and MLOps Requirements

### Repository Quality

- Use a clear Python package structure rather than placing all logic in
  notebooks.
- Keep notebooks for exploration and presentation only.
- Add type hints to important interfaces.
- Add focused tests for feature calculations, temporal splits, and simulations.
- Pin or lock dependencies.
- Provide reproducible commands for setup, training, evaluation, and serving.

### Automation

Use GitHub Actions or another scheduler to:

- Fetch completed games
- Update feature tables
- Generate predictions for upcoming games
- Evaluate previous predictions
- Optionally retrain models on a defined schedule

### Monitoring

Store each prediction with:

- Prediction timestamp
- Game identifier
- Model version
- Feature version
- Predicted probability
- Final result when available

Track:

- Recent Log Loss and Brier Score
- Calibration changes
- Missing or stale data
- Pipeline failures

---

## 12. Suggested Repository Structure

```text
nba-forecast-lab/
├── README.md
├── pyproject.toml
├── configs/
├── data/
│   ├── raw/
│   ├── processed/
│   └── features/
├── notebooks/
├── src/
│   └── nba_forecast/
│       ├── data/
│       ├── features/
│       ├── models/
│       ├── evaluation/
│       ├── simulation/
│       └── app/
├── tests/
├── artifacts/
├── scripts/
└── .github/
    └── workflows/
```

Large generated datasets and model artifacts should not be committed directly
unless intentionally using a suitable artifact storage solution.

---

## 13. Implementation Roadmap

### Phase 0: Benchmark and Design

- Review selected open-source NBA prediction repositories.
- Document their features, models, validation, metrics, and limitations.
- Define the project's data source and schema.
- Write an architecture and experiment plan.

**Deliverable:** benchmark report and project design.

### Phase 1: Reproducible Data Pipeline

- Collect historical game and team data.
- Store raw and processed data.
- Add validation and deduplication.
- Build a reproducible dataset command.

**Deliverable:** tested historical dataset pipeline.

### Phase 2: Leakage-Safe Baselines

- Implement home-team, win-percentage, Elo, and Logistic Regression baselines.
- Add walk-forward evaluation.
- Produce the first benchmark table.

**Deliverable:** trustworthy baseline results.

### Phase 3: Model Improvement and Calibration

- Add XGBoost or LightGBM.
- Tune important hyperparameters without contaminating the test set.
- Calibrate probabilities.
- Add feature importance and SHAP analysis.

**Deliverable:** selected calibrated model and model card.

### Phase 4: Playoff Simulator

- Implement best-of-seven simulation.
- Add full bracket simulation if time allows.
- Test home-court scheduling and simulation outputs.

**Deliverable:** tested playoff simulation engine.

### Phase 5: Dashboard and Deployment

- Build the dashboard pages.
- Deploy the application.
- Add a short demo and screenshots.

**Deliverable:** publicly accessible portfolio application.

### Phase 6: Automation and Monitoring

- Automate daily data updates and predictions.
- Store prediction history.
- Evaluate completed predictions.
- Display performance trends.

**Deliverable:** continuously operating end-to-end ML system.

---

## 14. Definition of Done

The initial portfolio version is complete when:

- A new user can reproduce the historical dataset and model evaluation.
- All features are generated without future information leakage.
- Models are compared using an out-of-time evaluation.
- The selected model produces calibrated win probabilities.
- The playoff simulator uses those calibrated probabilities.
- A deployed dashboard shows current predictions and historical performance.
- Daily predictions are stored and evaluated after games finish.
- Tests cover the highest-risk data and simulation logic.
- The README clearly explains the problem, architecture, results, limitations,
  and attribution.
- A short demo video is available.

---

## 15. Resume and Interview Positioning

Do not describe the project only as an NBA winner predictor.

Emphasize:

- Leakage-safe time-series feature engineering
- Walk-forward model validation
- Probability calibration
- Automated data and inference pipelines
- Reproducibility and testing
- Monte Carlo decision simulation
- Deployed model monitoring

### Example Resume Bullet Template

> Built an end-to-end NBA forecasting system using Python, XGBoost, and
> time-aware validation; improved Brier Score by **X%** over an Elo baseline,
> calibrated daily win probabilities, and powered a **10,000-run** playoff
> Monte Carlo simulator deployed with Streamlit and GitHub Actions.

Only insert measured values after they have been verified.

---

## 16. Instructions for an AI Coding Agent

When implementing this project:

1. Inspect the existing repository before proposing changes.
2. Prefer small, testable milestones that produce measurable results.
3. Implement the data pipeline and leakage-safe evaluation before building the
   dashboard.
4. Do not optimize for accuracy alone.
5. Never use random splits for final model evaluation.
6. Verify that each feature was available before the predicted game.
7. Establish simple baselines before adding complex models.
8. Keep external code usage minimal, licensed, attributed, and clearly
   separated from original work.
9. Record experiment results and important design decisions.
10. Do not claim improvements without running and reporting the relevant
    evaluation.
11. Do not expand into shot prediction or live-game prediction until the core
    definition of done is satisfied.

### Immediate First Task

Inspect the current repository, summarize its state, and create a concrete Phase
0 and Phase 1 implementation plan. Then begin with the smallest reproducible
historical game-data pipeline and its tests.
