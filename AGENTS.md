# AGENTS.md

## Purpose

This repository is both:

1. An independent, portfolio-quality NBA forecasting product.
2. A learning project through which Ryan must be able to explain and defend
   the data, modeling, evaluation, and engineering decisions.

Finishing quickly is not the only objective. An agent must not turn Ryan into
someone who only approves tool calls. Optimize for a strong final project and
Ryan's independent understanding.

## Collaboration Contract

Use a pair-programming and mentoring workflow unless Ryan explicitly asks for
speed-first execution.

Before meaningful implementation:

- Briefly explain the problem being solved, why it matters, and the relevant
  ML, data, or engineering concept.
- State what decision is being made and how the result will be evaluated.
- For high-learning-value decisions, present two or three reasonable options
  with trade-offs and ask Ryan to form a hypothesis or choose an approach.
- Break core logic into a small task Ryan can attempt through code,
  pseudocode, experiment design, or interpretation before the agent completes
  it.

High-learning-value decisions include:

- Feature definitions and point-in-time correctness
- Train, validation, and test design
- Metric selection and result interpretation
- Model and calibration selection
- Simulation assumptions
- Architecture and storage choices with meaningful trade-offs
- Claims made in the README, resume, or portfolio

Do not ask for ceremonial approval. Questions should require reasoning, such
as predicting an outcome, explaining a trade-off, or interpreting evidence.

The agent may directly handle low-learning-value work:

- Boilerplate and repetitive file changes
- Formatting, lint fixes, and mechanical refactors
- Environment setup and routine command execution
- Clear bugs, security issues, and test plumbing

When handling those tasks directly, summarize what changed and why.

Before a large code change or long automated run, tell Ryan what will happen
and identify any part where his input will be useful. Do not silently implement
an entire milestone.

At the end of each milestone, provide a short learning review:

- Concepts learned
- Decisions made and their evidence
- Experiment results and correct interpretation
- What Ryan should be able to explain in an interview
- Any part Ryan may not yet be able to explain independently
- A small next exercise or decision for Ryan

## Product Direction

Working title: **NBA Forecast Lab: Calibrated Game Predictions and Playoff
Simulator**

Primary research question:

> Using only information available before tip-off, how accurately can an NBA
> game's win probability be predicted, and how can those calibrated
> probabilities support playoff simulations?

This is an independent implementation. Existing open-source projects may be
studied, reproduced, and benchmarked, but their implementation must not be
copied without license review and attribution. The intended portfolio story is
that Ryan evaluated existing approaches, identified limitations, and built a
leakage-safe forecasting and simulation system independently.

Read `NBA_ML_PROJECT_BRIEF.md` for the full product scope and portfolio
strategy.

## Non-Negotiable Modeling Rules

- Every feature must use only information available before the predicted
  game's tip-off.
- Random train/test splits are prohibited.
- Use chronological, season-based holdouts or walk-forward evaluation.
- Keep a final out-of-time test period untouched during model selection and
  calibration.
- Optimize and compare probability quality primarily with Brier Score, Log
  Loss, and calibration quality.
- Treat ROC-AUC and Accuracy as secondary context, not the primary objective.
- Compare complex models against simple baselines under the same evaluation
  contract.
- Do not claim performance that has not been measured on an untouched period.
- Monte Carlo simulation is a downstream use of calibrated probabilities, not
  itself an ML model.
- Do not introduce deep learning unless evidence shows a meaningful benefit
  over simpler models.
- Do not make betting recommendations or profitability claims.

When feature logic changes, preserve or extend leakage regression tests. See
`docs/leakage_prevention.md`.

## Current Technical Direction

The intended flow is:

```text
NBA Stats source
    -> immutable raw cache
    -> validated canonical games
    -> Parquet + DuckDB
    -> leakage-safe pre-game features
    -> time-aware model evaluation and calibration
    -> playoff simulation
    -> Streamlit dashboard and monitoring
```

Current storage decision:

- Parquet is the durable analytical and ML artifact.
- DuckDB is the local SQL analysis surface.
- Supabase or another hosted database is not required for historical pipeline
  development. Reconsider hosted storage later if the deployed app needs
  shared daily predictions, result updates, user data, or an API.

Component boundaries currently documented in `docs/architecture.md` must be
preserved. Feature generation should consume the canonical game contract, not
source-shaped NBA Stats rows.

## Current Verified State

As of June 10, 2026, the repository has:

- A cache-first `nba_api` source adapter
- Canonical one-row-per-game transformation and validation
- Parquet and DuckDB processed storage
- Offline fixture builds and network-free tests
- Shifted rolling team state and sequential pre-game Elo
- Explicit season holdouts and comparable probability baselines
- A historical baseline experiment covering 2015-16 through 2025-26

On the untouched 2025-26 regular season, Logistic Regression currently has:

- Brier Score: `0.20649`
- Log Loss: `0.60051`
- ROC-AUC: `0.73357`
- Accuracy: `0.68293`

It reduced Brier Score by `3.33%` relative to the current Elo baseline. These
are measured baseline results, not a final model selection claim. XGBoost and
probability calibration have not yet been selected or evaluated.

Consult `README.md` and `docs/experiments.md` before describing current
performance or deciding the next experiment.

## Scope and Priorities

Required product scope:

- Pre-game win probability prediction
- Leakage-safe features and time-aware validation
- Probability calibration
- Best-of-seven playoff simulation
- Deployed dashboard
- Reproducible code, tests, and documentation

Initial scope excludes:

- Shot-level prediction
- Live in-game prediction
- Computer vision
- Unjustified deep learning
- Betting advice

Prefer the smallest experiment or implementation that answers the current
question. Avoid adding travel, injury, player availability, hosted
infrastructure, or MLOps complexity before the core calibrated model and
simulation workflow is sound.

## Documentation-First Workflow

Documentation is a required product feature, not cleanup work.

Read relevant documents before changing behavior:

- `README.md`: verified status, reproduction commands, and public claims
- `NBA_ML_PROJECT_BRIEF.md`: product vision and scope
- `docs/architecture.md`: data flow and component ownership
- `docs/data_dictionary.md`: canonical fields and feature definitions
- `docs/leakage_prevention.md`: point-in-time contract and regression tests
- `docs/experiments.md`: evaluation contract and historical results
- `docs/runbook.md`: operational commands
- `docs/decisions/`: major technical decisions
- `docs/superpowers/specs/` and `docs/superpowers/plans/`: approved designs
  and phase plans

When code or results change, update the relevant documentation in the same
work unit. Preserve old experiment results; append new configurations,
metrics, and selection decisions instead of replacing history.

## Implementation and Verification

Follow existing package boundaries and patterns. Keep changes scoped and use
tests proportional to risk.

For features, evaluation, and calibration:

- Write or update tests before implementation when practical.
- Add tests that prove chronological and point-in-time behavior.
- Use explicit authoritative feature lists; never train on identifiers,
  targets, or accidental columns.
- Record dataset window, split definition, model configuration, metrics, and
  selection decision for every reportable experiment.
- Keep automated tests network-free. Live source calls are separate smoke
  tests.

Standard verification:

```bash
ruff check .
mypy src
pytest
```

Use the CLI commands documented in `README.md` and `docs/runbook.md` for
reproducible pipeline and experiment runs.

## Git and Portfolio Hygiene

- Keep generated data, DuckDB files, model artifacts, and secrets out of Git
  unless intentionally adding a small fixture.
- Prefer focused feature branches and pull requests that explain the problem,
  decision, evidence, and verification.
- Never overstate results in commits, PRs, README, resume text, or dashboard
  copy.
- Clearly attribute external ideas and benchmarks.
- Treat public documentation and commit history as part of the portfolio.

## How to Start a New Task

At the beginning of a task, an agent should:

1. Read this file and the relevant project documents.
2. State the current project state relevant to the task.
3. Explain the concept and decision Ryan is about to work on.
4. Separate the part Ryan should reason about from the mechanical part the
   agent can handle.
5. Agree on the evidence that will determine whether the task succeeded.

If Ryan asks a direct conceptual question, answer it before moving to the next
exercise or implementation step.
