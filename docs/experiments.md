# Experiments

## Evaluation Contract

- Random train/test splits are prohibited.
- Callers explicitly provide train, validation, and test season identifiers.
- Season groups must be disjoint and chronological.
- Model selection and calibration must not use the final test period.

## Primary Metrics

1. Brier Score
2. Log Loss
3. Calibration quality

ROC-AUC and Accuracy are secondary context. Accuracy is not the optimization
target because the product emits probabilities for simulation.

## Current Results

No historical model comparison has been completed yet. This document will
record each reproducible configuration, data window, metrics, and selection
decision without replacing earlier results.

