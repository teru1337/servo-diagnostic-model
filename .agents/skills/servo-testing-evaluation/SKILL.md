---
name: servo-testing-evaluation
description: Use when adding pytest tests, synthetic anomaly generators, metrics, plots, or evaluation scripts for servo_diagnostic_model.
---

# Servo Testing and Evaluation Skill

Use this skill for tests and evaluation utilities.

## Read

- `markdowns/12_TESTING_AND_EVALUATION.md`

## Modify only if relevant

- `tests/`
- `servo_diagnostic_model/evaluation/synthetic_anomalies.py`
- `servo_diagnostic_model/evaluation/metrics.py`
- `servo_diagnostic_model/evaluation/plots.py`

## Required tests

Cover:

- data pipeline
- feature extraction
- physical risks
- Health Score
- classifier
- recommendations
- diagnostic_service
- bad data handling

## Synthetic anomalies

Implement when requested:

- current overload
- temperature ramp
- voltage drop
- voltage spike
- error code injection
- data gap
- velocity oscillation

## Metrics

Implement when requested:

- accuracy
- precision
- recall
- F1
- false alarm rate
- detection delay
- calculation time

## Rules

- Tests must be deterministic.
- Do not use real hardware.
- Do not require external services.
- Do not make plots part of core model logic.
