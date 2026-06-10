---
name: servo-data-pipeline
description: Use when implementing CSV loading, telemetry schema normalization, validation, preprocessing, sampling-rate estimation, or time-window creation for servo_diagnostic_model.
---

# Servo Data Pipeline Skill

Use this skill for tasks related to telemetry input and windowing.

## Read

- `markdowns/02_TELEMETRY_SCHEMA.md`
- `markdowns/05_DATA_PIPELINE.md`

## Modify only if relevant

- `servo_diagnostic_model/data/schemas.py`
- `servo_diagnostic_model/data/loader.py`
- `servo_diagnostic_model/data/preprocessing.py`
- `servo_diagnostic_model/data/validator.py`
- `servo_diagnostic_model/data/windowing.py`
- relevant tests in `tests/`

## Required outputs

Implement or maintain:

- `TelemetrySample`
- `TelemetryDataset`
- `TelemetryWindow`
- `load_csv`
- `load_telemetry`
- `normalize_column_names`
- `parse_time_columns`
- `coerce_numeric_columns`
- `validate_dataframe`
- `dataframe_to_samples`
- `estimate_sampling_rate`
- `make_windows`

## Rules

- Do not calculate features here.
- Do not calculate physical risks here.
- Do not calculate Health Score here.
- Do not generate recommendations here.
- Never silently replace missing diagnostic values with zero.
- Missing or invalid values must become validation warnings or data-quality metadata.
- The pipeline must tolerate optional missing fields.
- The pipeline must fail clearly if time is missing or the file is unusable.

## Tests

Add or update tests for:

- CSV loading
- missing file
- column alias normalization
- timestamp parsing
- missing time validation
- sampling rate estimation
- window creation
- short data handling
