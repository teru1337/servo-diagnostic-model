---
name: servo-python-architecture
description: Use when creating, reviewing, or refactoring the Python package architecture for servo_diagnostic_model. Enforces modular structure, dataclasses, type hints, configs, and separation of concerns.
---

# Servo Python Architecture Skill

Use this skill when working on package structure, imports, module responsibilities, or service orchestration.

## Read

- `markdowns/04_CODE_ARCHITECTURE.md`
- `markdowns/13_IMPLEMENTATION_ROADMAP.md`

## Expected package layout

The project should use this structure:

- `servo_diagnostic_model/data/`
- `servo_diagnostic_model/features/`
- `servo_diagnostic_model/model/`
- `servo_diagnostic_model/recommendations/`
- `servo_diagnostic_model/evaluation/`
- `servo_diagnostic_model/api/`
- `servo_diagnostic_model/config/`
- `tests/`

## Responsibilities

`data/`:

- loading
- validation
- preprocessing
- windowing
- telemetry dataclasses

`features/`:

- RMS
- slopes
- velocity/current/torque/voltage/temp/status features
- motion phase
- data quality features

`model/`:

- physical risks
- statistical profile
- anomaly score
- Health Score
- classifier
- explanation

`recommendations/`:

- rule-based recommendations only

`evaluation/`:

- synthetic anomalies
- metrics
- plots

`api/`:

- JSON-compatible service layer
- `diagnose_window`
- `diagnose_dataset`
- `diagnose_csv`

## Rules

- `main.py` must not contain business logic.
- `diagnostic_service.py` orchestrates the pipeline.
- Use dataclasses for internal schemas.
- Use type hints.
- Keep functions small and testable.
- Do not create circular imports.
