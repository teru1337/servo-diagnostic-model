---
name: servo-recommendations
description: Use when implementing rule-based diagnostic recommendations for normal, warning, critical, error, fault, voltage, temperature, current, torque, anomaly, and data-quality cases.
---

# Servo Recommendations Skill

Use this skill for rule-based recommendations.

## Read

- `markdowns/10_RECOMMENDATION_MODULE.md`

## Modify only if relevant

- `servo_diagnostic_model/recommendations/rule_based.py`
- relevant tests in `tests/`

## Required output

Implement:

- `generate_recommendations(state, risks, features, main_causes, thresholds=None) -> list[dict]`

Each recommendation must include:

- `priority`
- `category`
- `action`
- `reason`
- `source_risks`
- `target_role`

## Rules

- Do not use LLMs.
- Do not generate arbitrary advice.
- Use deterministic templates.
- Limit recommendation count.
- Merge duplicates.
- Sort by priority.

## Required scenarios

- normal
- unknown / bad data
- error_code
- statusword fault
- statusword warning
- voltage risk
- temperature risk
- current risk
- torque risk
- statistical anomaly
