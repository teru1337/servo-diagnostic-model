---
name: servo-config-driven-model
description: Use when implementing or changing limits, weights, thresholds, feature weights, normal profile loading, or default configuration behavior.
---

# Servo Config-Driven Model Skill

Use this skill when working with configs.

## Read

- `markdowns/11_CONFIGS_AND_CONSTANTS.md`

## Modify only if relevant

- `servo_diagnostic_model/config/`
- `servo_diagnostic_model/config_loader.py`
- config files
- relevant tests

## Required configs

- `limits.json`
- `weights.json`
- `thresholds.json`

Optional:

- `feature_weights.json`
- `normal_profile.json`

## Rules

- Do not hardcode model constants inside formulas.
- Use config values or defaults.
- Validate configs.
- Missing optional profile must not crash the model.
- Invalid config should produce clear errors or warnings.
