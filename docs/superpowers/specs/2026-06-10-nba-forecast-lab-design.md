# NBA Forecast Lab: Product Requirements and System Design

**Status:** Approved design  
**Date:** 2026-06-10  
**Delivery window:** Four weeks, approximately 15 hours per week  
**Working title:** NBA Forecast Lab: Calibrated Game Predictions and Playoff Simulator

## 1. Product Summary

NBA Forecast Lab is an independent, end-to-end machine learning portfolio
project that predicts pre-game NBA win probabilities and uses those calibrated
probabilities to simulate best-of-seven playoff series.

The project must demonstrate balanced Data Science, ML Engineering, and Data
Engineering skills while producing a public, visible result. The primary
delivery is a deployed Streamlit application. A Vercel landing page is a
stretch goal after the working Streamlit product is complete.

The central research question is:

> Using only information available before tip-off, how accurately can NBA game
> win probabilities be predicted, and how can those probabilities support
> playoff series simulations?

## 2. Product Principles

1. **Probability quality over winner-picking accuracy.** Brier Score, Log Loss,
   and calibration are primary. Accuracy is supporting context only.
2. **No future-information leakage.** Every feature must be reproducible as of
   the predicted game's tip-off.
3. **Simple baselines before complex models.** Elo and Logistic Regression must
   be credible before XGBoost is selected.
4. **Visible and reproducible.** A reviewer must be able to see the product and
   understand how to reproduce the important results.
5. **Documentation is part of the product.** Documentation changes accompany
   implementation and experiment changes.
6. **Measured claims only.** No performance improvement is claimed until it is
   reproduced on an untouched out-of-time evaluation period.

## 3. Intended Audience and Portfolio Story

The primary audience is internship recruiters and technical interviewers for
Data Science, ML Engineering, and Data Engineering roles.

The project story is:

> I independently built a leakage-safe NBA forecasting system, compared
> interpretable and boosted models under time-aware validation, calibrated the
> selected model's probabilities, and deployed those probabilities through a
> tested playoff simulation product.

## 4. Scope

### 4.1 Required MVP

- Historical NBA game and team-stat ingestion for 2015-16 through 2025-26
- Reproducible raw, cleaned, feature, prediction, and evaluation data layers
- Leakage-safe pre-game team features
- Home-team, win-percentage, and Elo baselines
- Logistic Regression and XGBoost model comparison
- Comparison of recent 3-season, recent 5-season, and decayed full-history
  training windows
- Walk-forward evaluation and an untouched final test period
- Platt and Isotonic probability calibration comparison
- `as_of_date` historical replay and prediction support
- Best-of-seven Monte Carlo series simulator with NBA home-court order
- Streamlit pages for Predictions, Simulator, Performance, and Methodology
- A manual or weekly refresh workflow
- Focused automated tests and complete project documentation

### 4.2 Stretch Goals

These are attempted only after all MVP acceptance criteria pass:

- Full playoff bracket simulation
- Daily GitHub Actions prediction refresh
- SHAP-based prediction explanations
- Vercel portfolio landing page linking to the Streamlit application
- Player availability features

### 4.3 Explicitly Deferred

- Live in-game win probability
- Shot prediction
- Betting recommendations or profitability claims
- Deep learning
- Coach-change features
- Next-season standings predictions
- Scoring, rebounding, assist, or award-leader predictions

## 5. Historical Evaluation and Current Predictions

The product separates three different claims:

### 5.1 Core Performance Evidence

Historical games are replayed in chronological order. Each prediction uses only
data available before that game. This evaluation provides the trustworthy
comparison between baselines, Logistic Regression, XGBoost, and calibration
methods.

### 5.2 2026 Playoff Historical Replay

The system can set an `as_of_date` before the 2026 playoffs and simulate the
bracket or selected series using only information available at that time.
Results are clearly labeled as historical replay, not a prediction published
before the real event.

### 5.3 Forward Predictions

Any game still in the future when the system becomes operational may receive a
timestamped prediction. The prediction is stored unchanged and later evaluated
after the result is known. These predictions demonstrate operational behavior,
but a small sample is not used as the main performance claim.

## 6. Future Expansion Boundary

The architecture should make future forecasting projects easier without adding
their requirements to the MVP.

### Reusable Components

- Historical game ingestion and canonical identifiers
- Team and season identifiers
- Point-in-time data contracts
- Feature registry conventions
- Walk-forward validation utilities
- Prediction and evaluation storage
- Dashboard design language and documentation standards

### Separate Future Models

Next-season standings require season-level team-strength projections and a full
schedule simulation. Scoring, rebounding, and other player leader predictions
require player-level opportunity, availability, age, roster, and minutes
models. They must be treated as separate projects with separate targets,
features, evaluation methods, and model cards.

The current package should permit future sibling modules such as
`season_forecasting` and `player_forecasting`, but no code for them is required
in this delivery.

## 7. System Architecture

```text
NBA historical/current game data
        |
        v
raw Parquet -> cleaned Parquet/DuckDB -> point-in-time feature tables
                                            |
                                            v
                            Elo / Logistic Regression / XGBoost
                                            |
                                            v
                             calibration + time-aware evaluation
                                            |
                       +--------------------+--------------------+
                       |                                         |
                       v                                         v
              as_of_date predictions                    best-of-seven simulator
                       |                                         |
                       +--------------------+--------------------+
                                            |
                                            v
                                  Streamlit portfolio app
```

### 7.1 Component Responsibilities

- **Data ingestion:** Fetch and persist source records without applying model
  assumptions.
- **Data processing:** Normalize identifiers, deduplicate games, validate
  schemas, and create canonical team-game records.
- **Feature generation:** Produce strictly pre-game team-state features and
  home-minus-away model rows.
- **Models:** Implement a consistent probability-prediction interface for
  baselines and trained models.
- **Evaluation:** Run temporal splits, calculate metrics, and save comparable
  experiment results.
- **Simulation:** Consume a game-probability interface; it must not depend on a
  specific model implementation.
- **Application:** Read prepared prediction and evaluation artifacts rather
  than training models inside the user request path.

## 8. Data Design

### 8.1 Storage

DuckDB is the local analytical query layer and Parquet is the durable tabular
artifact format. Large source data and trained artifacts are excluded from Git.

```text
data/raw/          immutable source-shaped extracts
data/processed/    normalized games and team-game statistics
data/features/     point-in-time model tables
artifacts/models/  fitted models and metadata
artifacts/reports/ evaluation tables and charts
data/predictions/  timestamped predictions and outcomes
```

### 8.2 Initial Source Strategy

The primary source is the NBA Stats API through the Python `nba_api` package.
Raw endpoint responses are cached as immutable extracts to reduce repeated
requests and make downstream builds reproducible. Source documentation records
endpoint names, access dates, coverage, field definitions, and refresh
limitations. If the primary source cannot provide a required historical field,
a documented secondary dataset may supply that field only after its license,
lineage, and compatibility are recorded. The data layer isolates source-specific
code so a source can be replaced without changing feature or model interfaces.

### 8.3 Minimum Canonical Game Fields

- `game_id`
- `game_date`
- `season`
- `season_type`
- `home_team_id`
- `away_team_id`
- `home_points`
- `away_points`
- `home_win`
- team box-score and advanced-stat inputs needed for rolling features

### 8.4 Data Validation

- Unique `game_id`
- One home and one away team per game
- Valid final score for completed games
- Valid season and date ordering
- No duplicated team-game rows
- Expected null rules by game status
- Stable row counts across repeated ingestion

## 9. Feature Design

Each model row represents one scheduled game. Elo, win percentage, rolling
ratings, and rest days are transformed to home-minus-away differences.
Home-court and team-specific back-to-back indicators remain separate fields.

### Required Initial Features

- Home-court indicator
- Pre-game Elo difference
- Season-to-date win-percentage difference
- Previous 5-, 10-, and 20-game win-percentage differences
- Previous 5-, 10-, and 20-game offensive-rating differences
- Previous 5-, 10-, and 20-game defensive-rating differences
- Previous 5-, 10-, and 20-game net-rating differences
- Rest-day difference
- Home and away back-to-back indicators
- Season progress

All rolling and expanding statistics must apply a one-game shift before
aggregation. Leakage tests must prove that changing a game's result does not
change its own feature row or any earlier feature row.

## 10. Modeling and Evaluation

### 10.1 Models

1. Constant home-win-rate probability baseline
2. Season-to-date win-percentage baseline
3. Elo probability baseline
4. Regularized Logistic Regression
5. XGBoost classifier

### 10.2 Training Window Experiment

The evaluation compares:

- Previous three seasons
- Previous five seasons
- All available history with older-game sample-weight decay

The final strategy is selected using validation-period Brier Score and Log
Loss, not intuition about how much history should matter.

### 10.3 Temporal Evaluation

- Random train/test splits are prohibited.
- Model selection and calibration occur before the untouched final test period.
- Walk-forward results are reported by season.
- The 2025-26 season is reserved as the intended final out-of-time test period,
  subject to confirmed data completeness.

### 10.4 Metrics

Primary:

- Brier Score
- Log Loss
- Calibration curve and Expected Calibration Error

Secondary:

- ROC-AUC
- Accuracy

### 10.5 Calibration

Platt scaling and Isotonic Regression are compared on temporally valid
calibration data. Calibration never sees the final test period.

## 11. Playoff Series Simulation

The simulator consumes a function that returns the home team's win probability
for a matchup and game context.

Required behavior:

- Best-of-seven format
- Home-court order `H, H, A, A, H, A, H`
- Stop when either team reaches four wins
- At least 10,000 simulations per displayed result
- Deterministic testability through a supplied random seed
- Report series win probability, win-in-4/5/6/7 distribution, and expected
  series length

Simulation is described as a decision layer powered by the calibrated model,
not as a separate ML model.

## 12. Streamlit Product

### Predictions

- Display stored upcoming or historical replay predictions
- Show calibrated home and away win probabilities
- Clearly display prediction timestamp and `as_of_date`
- Label historical replay separately from forward predictions

### Simulator

- Select two teams and home-court owner
- Run a best-of-seven simulation
- Display series-win probability and series-length distribution

### Performance

- Model comparison table
- Brier Score and Log Loss by model and season
- Calibration curve
- Calibrated versus uncalibrated comparison

### Methodology

- Research question and scope
- Data sources and limitations
- Leakage-prevention rules
- Temporal validation design
- Architecture diagram
- Links to repository documentation

## 13. Documentation Requirements

Documentation is a required product surface and must be updated in the same
change as the relevant code or result.

- `README.md`: product overview, screenshots, verified headline results,
  architecture, quickstart, reproducibility commands, limitations, attribution
- `docs/architecture.md`: data flow, component contracts, and deployment shape
- `docs/data_dictionary.md`: canonical columns, feature definitions, and
  point-in-time availability
- `docs/leakage_prevention.md`: leakage risks, rules, and corresponding tests
- `docs/experiments.md`: experiment configurations, results, and decisions
- `docs/model_card.md`: intended use, evaluation, limitations, and ethics
- `docs/runbook.md`: refresh, train, evaluate, deploy, and failure recovery
- `docs/decisions/`: concise architecture decision records

The README must remain concise enough for a recruiter to understand the project
within several minutes, while detailed evidence lives in linked documents.

## 14. Testing and Quality Strategy

Highest-risk logic receives focused automated tests:

- Canonical game transformation and deduplication
- Rolling features use only earlier games
- Temporal splits never overlap or reverse time
- Elo updates occur only after a game
- Metrics match known examples
- Calibration excludes the final test set
- Series schedule and stopping rules are correct
- Seeded simulations are reproducible
- Streamlit application starts against prepared sample artifacts

Formatting, linting, type checks for important interfaces, and unit tests run in
CI. Expensive data downloads and full training runs are separate reproducible
commands rather than required for every pull request.

## 15. Operational Workflow

MVP operation uses explicit commands:

```text
fetch data -> validate/process -> build features -> train/evaluate
-> generate predictions -> run Streamlit app
```

A weekly or manual refresh is sufficient for MVP acceptance. Daily GitHub
Actions automation is implemented only after the manual workflow is reliable.

Every stored prediction includes:

- Prediction timestamp
- `as_of_date`
- Game identifier
- Model version
- Feature version
- Predicted probability
- Final outcome when available

## 16. Four-Week Delivery Plan

### Week 1: Foundation and Trustworthy Data

- Repository tooling, documentation skeleton, and architecture records
- Historical data source selection and source report
- Reproducible ingestion, canonical games, validation, and tests
- Initial README quickstart and data dictionary

**Exit criterion:** a clean historical game table can be rebuilt and validated
with documented commands.

### Week 2: Leakage-Safe Baselines

- Point-in-time features and leakage tests
- Home-rate, win-percentage, Elo, and Logistic Regression baselines
- Walk-forward evaluation and first benchmark report
- Leakage-prevention and experiment documentation

**Exit criterion:** baseline probabilities and honest temporal metrics are
reproducible.

### Week 3: Selected Model, Calibration, and Simulation

- XGBoost and training-window comparison
- Platt versus Isotonic calibration
- Final model selection and model card
- Tested best-of-seven simulator

**Exit criterion:** the selected calibrated model and simulator have saved,
documented results.

### Week 4: Visible Product and Polish

- Streamlit Predictions, Simulator, Performance, and Methodology pages
- Historical replay and timestamped prediction display
- Deployment, screenshots, runbook, and README refinement
- CI and final reproducibility check
- Stretch goals only if all acceptance criteria pass

**Exit criterion:** a reviewer can open the deployed product, understand the
method, inspect verified results, and reproduce the core workflow.

## 17. Acceptance Criteria

The MVP is complete only when:

- Historical data can be rebuilt using documented commands.
- Feature tests demonstrate point-in-time correctness.
- Baselines, Logistic Regression, and XGBoost are compared out of time.
- The selected probability model is calibrated without test-set contamination.
- A best-of-seven series can be simulated reproducibly.
- The Streamlit product is deployed and displays prepared predictions,
  simulation results, performance, and methodology.
- Prediction timestamps and historical replay labels prevent misleading claims.
- CI passes focused tests and quality checks.
- The README and all required detailed documentation reflect the implemented
  system and measured results.

## 18. Key Risks and Mitigations

- **Unstable or rate-limited data source:** cache immutable raw extracts and
  isolate source adapters.
- **Incomplete advanced statistics:** begin with reliable box-score-derived
  features and document omissions.
- **Future-information leakage:** enforce shifted rolling calculations and
  mutation-based leakage tests.
- **Overly broad scope:** stretch goals cannot begin before MVP acceptance
  criteria pass.
- **Misleading 2026 Finals claims:** clearly separate historical replay,
  forward predictions, and historical evaluation.
- **Deployment complexity:** deploy Streamlit first; Vercel remains optional.
- **Documentation drift:** require docs updates in task acceptance criteria and
  pull-request templates.
