---
name: servo-health-classifier
description: Use when implementing Health Score, hard limits, state classification, risk levels, main causes, and human-readable explanations for servo diagnostics.
---

# Servo Health Classifier Skill

Use this skill for Health Score, state classification, and explanations.

## Read

- `markdowns/09_HEALTH_SCORE_AND_CLASSIFIER.md`
- `markdowns/03_MODEL_REQUIREMENTS.md`

## Modify only if relevant

- `servo_diagnostic_model/model/health_score.py`
- `servo_diagnostic_model/model/classifier.py`
- `servo_diagnostic_model/model/explanation.py`
- relevant tests in `tests/`

## Required outputs

Implement:

- `calculate_health_score(risks, weights, features=None) -> float`
- `apply_hard_limits(health_score, risks, features) -> float`
- `classify_state(health_score, anomaly_score, risks, thresholds, features) -> str`
- `risk_level_from_state(state) -> str`
- `get_main_causes(risks, features, top_n=3) -> list[dict]`
- `generate_explanation(...) -> list[str]`

## Rules

- Health Score must be in range 0..100.
- Risks must be interpreted in range 0..1.
- `error_flag == True` must produce `critical`.
- `fault_flag == True` must produce `critical`.
- If `error_flag == True`, Health Score must not exceed 40.
- If `fault_flag == True`, Health Score must not exceed 40.
- Classifier may only return:
  - `normal`
  - `observation`
  - `warning`
  - `critical`
  - `unknown`

## Tests

Add tests for:

- all-zero risks
- all-one risks
- Health Score range
- hard limit by error
- normal classification
- observation classification
- warning classification
- critical by Health Score
- critical by error
- critical by fault
- main causes selection
