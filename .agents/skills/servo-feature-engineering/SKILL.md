---
name: servo-feature-engineering
description: 'Use when implementing diagnostic feature extraction from telemetry windows: RMS, slope, motion phase, current, torque, voltage, temperature, statusword, and data-quality features.'
---

# Servo Feature Engineering Skill

Use this skill for transforming `TelemetryWindow` into a feature dictionary.

## Read

- `markdowns/06_FEATURE_ENGINEERING.md`

## Modify only if relevant

- `servo_diagnostic_model/features/basic_features.py`
- `servo_diagnostic_model/features/motion_features.py`
- `servo_diagnostic_model/features/electrical_features.py`
- `servo_diagnostic_model/features/thermal_features.py`
- `servo_diagnostic_model/features/status_features.py`
- `servo_diagnostic_model/features/feature_extractor.py`
- relevant tests in `tests/`

## Required output

Implement:

- `extract_features(window, thresholds=None) -> dict`

The returned dict must include:

- velocity features
- acceleration features
- position features where available
- current features
- torque features
- voltage features
- temperature features
- status/error features
- motion phase
- data quality features

## Rules

- Feature functions must be safe for `None`, `NaN`, empty lists, missing optional fields.
- Do not calculate risks here.
- Do not calculate Health Score here.
- Do not classify state here.
- Do not generate recommendations here.
- If a feature cannot be calculated, return `None` rather than inventing a value.
- Do not hide data-quality problems.

## Required basic functions

- `is_valid_number`
- `clean_values`
- `safe_mean`
- `safe_min`
- `safe_max`
- `safe_std`
- `rms`
- `slope`
- `safe_abs_max`

## Tests

Add tests for:

- RMS
- negative RMS values
- empty input
- slope
- velocity features
- temperature slope
- error flag
- fault flag
- motion phase
