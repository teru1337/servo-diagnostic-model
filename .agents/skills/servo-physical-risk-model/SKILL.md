---
name: servo-physical-risk-model
description: Use when implementing physical risk calculations for current, torque, velocity, DC-bus voltage, temperature, statusword, error_code, and data quality. Outputs risks in range 0..1.
---

# Servo Physical Risk Model Skill

Use this skill for `model/physical_risks.py`.

## Read

- `markdowns/07_PHYSICAL_RISK_MODEL.md`
- `markdowns/11_CONFIGS_AND_CONSTANTS.md`

## Modify only if relevant

- `servo_diagnostic_model/model/physical_risks.py`
- `servo_diagnostic_model/config/limits.json`
- relevant tests in `tests/`

## Required output

Implement:

- `calculate_physical_risks(features, limits) -> dict`

The returned dict must contain:

- `current`
- `torque`
- `velocity`
- `voltage`
- `temperature`
- `statusword`
- `error`
- `data_quality`
- `statistical_anomaly`

## Rules

- Every risk must be clamped to 0..1.
- `error_flag == True` means `error` risk is 1.
- `fault_flag == True` means `statusword` risk is 1.
- Use limits from config, not hardcoded constants.
- Missing optional features must not crash the calculation.
- Missing critical values should be reflected through `data_quality`, not fake physical risk.

## Required helper functions

- `clamp`
- `safe_divide`
- `linear_risk`
- `inverse_linear_risk`

## Tests

Add tests for:

- current risk
- torque risk
- velocity risk
- voltage low/high/unstable risk
- temperature level/slope risk
- error risk
- statusword fault risk
- data quality risk
- missing feature safety
