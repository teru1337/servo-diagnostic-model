# AGENTS.md

## Project identity

This repository contains the `servo_diagnostic_model` project.

The goal is to implement a physical-statistical diagnostic model for servo-drive telemetry. The model must analyze telemetry windows and produce:

- Health Score
- Anomaly Score
- state: normal / observation / warning / critical / unknown
- risks
- main causes
- explanation
- recommendations

## Mandatory documentation

Before implementing or refactoring any project module, inspect the relevant files in `markdowns/`.

Do not read all Markdown files by default. Use the relevant skill to select the smallest necessary subset.

## Architecture rules

Use the architecture described in:

- `markdowns/04_CODE_ARCHITECTURE.md`
- `markdowns/13_IMPLEMENTATION_ROADMAP.md`

The code must be modular.

Expected package structure:

- `servo_diagnostic_model/data/`
- `servo_diagnostic_model/features/`
- `servo_diagnostic_model/model/`
- `servo_diagnostic_model/recommendations/`
- `servo_diagnostic_model/evaluation/`
- `servo_diagnostic_model/api/`
- `servo_diagnostic_model/config/`
- `tests/`

Do not put all logic into `main.py`.

`main.py` is only a CLI entry point.

`api/diagnostic_service.py` is the main orchestrator.

## Forbidden libraries

Do not use ready-made ML frameworks or model libraries:

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
- matplotlib only for evaluation/plots

## Diagnostic invariants

All risks must be clamped to range 0..1.

Health Score must be clamped to range 0..100.

If `error_code != 0` or `error_flag == True`, final state must be `critical`.

If `fault_flag == True`, final state must be `critical`.

Missing optional telemetry fields must not crash the model.

Never silently replace missing diagnostic values with zero unless the documentation explicitly says so.

Bad or incomplete telemetry must affect `data_quality` risk.

## Testing expectations

After changing code, add or update pytest tests.

At minimum, test:

- normal telemetry
- missing optional fields
- bad data
- `error_code != 0`
- risk ranges
- Health Score range
- classifier output
- recommendations output

## Output contract

The diagnostic result must remain JSON-compatible and include:

- window_start
- window_end
- device_id
- health_score
- anomaly_score
- state
- risk_level
- motion_phase
- features
- risks
- main_causes
- explanation
- recommendations
- data_quality
- debug
