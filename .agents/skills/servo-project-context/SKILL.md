---
name: servo-project-context
description: Use for any task in the ServoAI diagnostic model repository. Provides the core project context, constraints, architecture boundaries, and expected diagnostic output contract.
---

# Servo Project Context Skill

Use this skill when working on any task related to `servo_diagnostic_model`.

## Read first

Read only these files unless the task requires more:

- `markdowns/00_PROJECT_OVERVIEW.md`
- `markdowns/01_DOMAIN_CONTEXT.md`
- `markdowns/03_MODEL_REQUIREMENTS.md`

## Project goal

Implement a physical-statistical diagnostic model for servo-drive telemetry.

The model must process telemetry windows and produce:

- `health_score`
- `anomaly_score`
- `state`
- `risk_level`
- `motion_phase`
- `risks`
- `main_causes`
- `explanation`
- `recommendations`

## Core constraints

Do not use:

- sklearn
- tensorflow
- pytorch
- keras
- xgboost
- lightgbm
- catboost

Allowed:

- Python standard library
- numpy
- pandas
- pytest
- matplotlib only for evaluation and plots

## Diagnostic invariants

- All risks must be in range 0..1.
- Health Score must be in range 0..100.
- `error_code != 0` must lead to `critical`.
- `fault_flag == True` must lead to `critical`.
- Missing optional telemetry fields must not crash the model.
- Bad telemetry must affect `data_quality` risk.

## Do not

- Do not implement a neural network.
- Do not implement LLM recommendations.
- Do not put all code into one file.
- Do not hardcode physical limits directly in model formulas.
