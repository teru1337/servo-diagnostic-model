---
name: servo-json-contract
description: Use when changing diagnostic output, API schemas, service orchestration, or backend/PWA-facing result structure. Preserves the JSON-compatible diagnostic result contract.
---

# Servo JSON Contract Skill

Use this skill when modifying output format or service layer.

## Read

- `markdowns/03_MODEL_REQUIREMENTS.md`
- `markdowns/04_CODE_ARCHITECTURE.md`
- `markdowns/09_HEALTH_SCORE_AND_CLASSIFIER.md`

## Required result fields

Every diagnostic result must include:

- `window_start`
- `window_end`
- `device_id`
- `health_score`
- `anomaly_score`
- `state`
- `risk_level`
- `motion_phase`
- `features`
- `risks`
- `main_causes`
- `explanation`
- `recommendations`
- `data_quality`
- `debug`

## Rules

- Output must be JSON-compatible.
- Do not return dataclasses directly from API functions.
- Do not break field names without updating documentation and tests.
- Keep result stable for backend/PWA integration.
