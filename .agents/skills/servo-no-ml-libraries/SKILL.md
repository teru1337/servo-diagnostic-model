---
name: servo-no-ml-libraries
description: Use when implementing anomaly detection, statistical logic, diagnostic model logic, or any model-like behavior. Prevents use of sklearn, tensorflow, pytorch, keras, xgboost, lightgbm, and catboost.
---

# Servo No ML Libraries Skill

Use this skill whenever implementing anything called model, anomaly detection, prediction, scoring, or classification.

## Forbidden

Do not import or use:

- sklearn
- tensorflow
- pytorch
- torch
- keras
- xgboost
- lightgbm
- catboost

## Allowed

Allowed for math and data processing:

- math
- statistics
- json
- dataclasses
- typing
- pathlib
- datetime
- csv
- sqlite3
- numpy
- pandas

## Rules

- Statistical anomaly detection must be implemented manually.
- Use median, MAD, robust z-score, simple weighted scores.
- Do not use ready-made IsolationForest, OneClassSVM, PCA, RandomForest, neural networks, or regressors.
