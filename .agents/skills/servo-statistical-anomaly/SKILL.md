---
name: servo-statistical-anomaly
description: Use when implementing normal profiles, median/MAD statistics, robust z-score, phase-specific profiles, and Anomaly Score without sklearn or deep learning.
---

# Servo Statistical Anomaly Skill

Use this skill for statistical anomaly detection.

## Read

- `markdowns/08_STATISTICAL_ANOMALY_MODEL.md`
- `markdowns/06_FEATURE_ENGINEERING.md`

## Modify only if relevant

- `servo_diagnostic_model/model/statistical_profile.py`
- `servo_diagnostic_model/model/anomaly_score.py`
- `servo_diagnostic_model/config/feature_weights.json`
- relevant tests in `tests/`

## Required outputs

Implement:

- `fit_normal_profile(feature_rows)`
- `save_profile(profile, path)`
- `load_profile(path)`
- `robust_feature_score(value, stats, z_limit)`
- `calculate_anomaly_score(features, profile, thresholds=None)`

## Rules

- Do not use sklearn.
- Do not use deep learning.
- Use median and MAD.
- Support global profile and by-motion-phase profile.
- If no profile exists, return `anomaly_score = 0.0` and `available = False`.
- Anomaly Score must be in range 0..1.
- MAD=0 must not crash the model.

## Tests

Add tests for:

- MAD
- robust score = 0
- robust score clamping
- no profile
- fit normal profile
- phase profile
- global fallback
- save/load profile
