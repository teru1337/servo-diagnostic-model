# 15_CURRENT_PROJECT_STATE.md

## 1. Purpose of this document

This file is a handoff snapshot for future Codex sessions working on
`servo_diagnostic_model`. It records the current repository architecture,
implemented behavior, test status, known limitations, and recommended next
steps as verified on June 11, 2026.

This snapshot is intended to reduce repeated repository exploration. Future
sessions should still inspect the relevant source files and documentation
before making changes, because this file may become stale.

## 2. Current project goal

The project implements a physical-statistical diagnostic model for
servo-drive telemetry. It analyzes telemetry windows and produces:

- Health Score
- Anomaly Score
- state
- risk_level
- risks
- main_causes
- explanation
- recommendations

The implementation combines configured physical risk rules with a
median/MAD-based statistical anomaly model. It does not use ready-made machine
learning frameworks.

## 3. Current repository architecture

The current major repository structure is:

```text
AGENTS.md
.agents/skills/
markdowns/
servo_diagnostic_model/
  api/
  config/
  data/
  evaluation/
  features/
  model/
  recommendations/
tests/
```

Purpose of each major area:

- `AGENTS.md`: active project-wide instructions, invariants, architecture
  boundaries, testing expectations, and output contract.
- `.agents/skills/`: repository-specific Codex workflows and constraints.
- `markdowns/`: project requirements, architecture, formulas, implementation
  roadmap, and handoff documentation.
- `servo_diagnostic_model/data/`: CSV loading, schema objects, preprocessing,
  validation, sampling-rate estimation, and windowing.
- `servo_diagnostic_model/features/`: deterministic telemetry-window feature
  extraction.
- `servo_diagnostic_model/model/`: physical risks, statistical anomaly score,
  Health Score, classifier, causes, and explanations.
- `servo_diagnostic_model/api/`: diagnostic orchestration, JSON contract, and
  normal-profile fitting service.
- `servo_diagnostic_model/recommendations/`: deterministic rule-based
  recommendations.
- `servo_diagnostic_model/config/`: starter physical limits, risk weights, and
  thresholds.
- `servo_diagnostic_model/evaluation/`: currently contains only
  `__init__.py`; evaluation utilities are not implemented.
- `tests/`: pytest coverage for the implemented pipeline and services.

No root `main.py` CLI entry point is currently present.

## 4. Repo instructions and skills

`AGENTS.md` is active and defines the project-wide rules. Important rules
include modular architecture, JSON-compatible diagnostic results, clamped
risks and Health Score, critical-state behavior for errors and faults, safe
handling of missing optional telemetry, and prohibition of ready-made ML
frameworks.

Repository skills are stored in `.agents/skills/`. Important available skills
are:

- `servo-project-context`
- `servo-implementation-planner`
- `servo-python-architecture`
- `servo-data-pipeline`
- `servo-feature-engineering`
- `servo-physical-risk-model`
- `servo-health-classifier`
- `servo-recommendations`
- `servo-statistical-anomaly`
- `servo-config-driven-model`
- `servo-json-contract`
- `servo-testing-evaluation`
- `servo-no-ml-libraries`

Future tasks should explicitly use the relevant skills and inspect the
smallest necessary documentation subset before implementation.

## 5. Implemented pipeline overview

The currently implemented diagnostic flow is:

```text
CSV
  |
  v
load / preprocess / validate
  |
  v
TelemetryDataset
  |
  v
TelemetryWindow[]
  |
  v
extract_features
  |
  v
calculate_physical_risks
  |
  v
calculate_anomaly_score if normal_profile is supplied
  |
  v
calculate_health_score
  |
  v
classify_state
  |
  v
main_causes
  |
  v
explanation
  |
  v
recommendations
  |
  v
JSON-compatible diagnostic result
```

`servo_diagnostic_model/api/diagnostic_service.py` is the main diagnostic
orchestrator.

## 6. Implemented data pipeline

### `servo_diagnostic_model/data/schemas.py`

Implemented dataclasses:

- `TelemetrySample`
- `TelemetryDataset`
- `TelemetryWindow`

The schema supports required time data and optional diagnostic telemetry such
as velocity, position, current, torque, voltage, temperature, statusword,
error code, mode display, and device ID.

### `servo_diagnostic_model/data/loader.py`

Implemented:

- `load_csv`
- `load_telemetry`

CSV loading is supported. `load_telemetry` performs loading, normalization,
time parsing, numeric coercion, sorting, validation, sample conversion,
sampling-rate estimation, and duration calculation.

### `servo_diagnostic_model/data/preprocessing.py`

Implemented:

- `normalize_column_names`
- `parse_time_columns`
- `coerce_numeric_columns`
- `sort_by_time`
- `dataframe_to_samples`

`preprocess_dataframe` is not currently implemented as a public function.
Equivalent preprocessing steps are orchestrated directly by `load_telemetry`.

Column aliases are normalized. Time can be supplied through `t` or parsed
from timestamp aliases such as `ts`. Mixed ISO timestamps with and without
fractional seconds are supported and directly covered by tests.

### `servo_diagnostic_model/data/validator.py`

Implemented:

- `validate_dataframe`
- `check_time_column`
- `check_required_columns`
- `check_missing_columns`
- `check_numeric_quality`
- `check_duration`

Missing time is treated as a critical validation problem. Missing optional
telemetry fields are reported but should not crash the pipeline.

### `servo_diagnostic_model/data/windowing.py`

Implemented:

- `estimate_sampling_rate`
- `calculate_duration`
- `make_windows`

Windows use configured duration, step, and minimum sample count. Undersized
windows may be skipped. Short-data behavior, sampling-rate estimation, and
duration calculation are covered by tests.

## 7. Implemented feature engineering

Feature functions are designed to tolerate `None`, NaN, empty values, and
missing optional telemetry. Unavailable diagnostic values are represented as
`None` rather than silently replaced with zero.

### `servo_diagnostic_model/features/basic_features.py`

Implemented:

- `is_valid_number`
- `clean_values`
- `safe_mean`
- `safe_min`
- `safe_max`
- `safe_std`
- `rms`
- `slope`
- `safe_abs_max`

### `servo_diagnostic_model/features/motion_features.py`

Implemented:

- `calculate_velocity_features`
- `calculate_acceleration_features`
- `calculate_position_features`
- `detect_motion_phase`

### `servo_diagnostic_model/features/electrical_features.py`

Implemented:

- `calculate_current_features`
- `calculate_torque_features`
- `calculate_voltage_features`
- `calculate_load_relation_features`

`calculate_load_relation_features` provides low-speed load-related features
when the required inputs are available.

### `servo_diagnostic_model/features/thermal_features.py`

Implemented:

- `calculate_temperature_features`

Temperature features include `temp_slope`.

### `servo_diagnostic_model/features/status_features.py`

Implemented:

- `decode_statusword`
- `calculate_status_features`

Status features include:

- `error_flag`
- `fault_flag`
- `warning_flag`
- operation-enabled ratio

### `servo_diagnostic_model/features/feature_extractor.py`

Implemented:

- `extract_features`
- `calculate_data_quality_features`

`extract_features` returns a dictionary suitable for physical risk
calculation, statistical profiling, diagnostic orchestration, and
JSON-compatible output.

## 8. Implemented physical risk model

### `servo_diagnostic_model/model/physical_risks.py`

Implemented:

- `clamp`
- `safe_divide`
- `linear_risk`
- `inverse_linear_risk`
- `calculate_current_risk`
- `calculate_torque_risk`
- `calculate_velocity_risk`
- `calculate_voltage_risk`
- `calculate_temperature_risk`
- `calculate_error_risk`
- `calculate_statusword_risk`
- `calculate_data_quality_risk`
- `calculate_physical_risks`

Required risk keys returned by `calculate_physical_risks`:

- `current`
- `torque`
- `velocity`
- `voltage`
- `temperature`
- `statusword`
- `error`
- `data_quality`
- `statistical_anomaly`

All returned risks are clamped to `0..1`. `error_flag=True` produces error
risk `1.0`, and `fault_flag=True` produces statusword risk `1.0`. Missing
critical values are reflected through data-quality behavior rather than fake
physical risk values.

Temperature slope risk is gated while `temp_max < temp_safe`. The configured
safe-temperature ceiling prevents slope alone from becoming critical, and a
stricter ceiling applies when `temp_max - temp_min` is within the configured
quantized temperature range. Absolute temperature risk is unchanged, and
temperature slope risk remains unrestricted at or above `temp_safe`.

Starter limits are stored in `servo_diagnostic_model/config/limits.json`.
They have not been calibrated against verified real hardware parameters.

## 9. Implemented Health Score, classifier, causes, and explanations

### `servo_diagnostic_model/model/health_score.py`

Implemented:

- `calculate_health_score`
- `apply_hard_limits`

Health Score is clamped to `0..100`. Hard limits reduce the maximum score for:

- error or fault: maximum `40`
- critical temperature risk: maximum `50`
- critical voltage risk: maximum `50`
- fully bad data-quality risk: maximum `60`

### `servo_diagnostic_model/model/classifier.py`

Implemented:

- `classify_state`
- `risk_level_from_state`
- `has_risk_above`

Classifier states are limited to:

- `normal`
- `observation`
- `warning`
- `critical`
- `unknown`

`error_flag=True` and `fault_flag=True` force `critical`. Fully critical error
or statusword risk also forces `critical`.

### `servo_diagnostic_model/model/explanation.py`

Implemented:

- `severity_from_risk`
- `get_main_causes`
- `generate_explanation`

Main causes are selected from the highest relevant risks. Explanations are
deterministic English templates.

## 10. Implemented diagnostic service

### `servo_diagnostic_model/api/schemas.py`

Implemented:

- `DiagnosticResult` typed JSON contract

### `servo_diagnostic_model/api/diagnostic_service.py`

Implemented:

- `load_json_config`
- `diagnose_window`
- `diagnose_dataset`
- `diagnose_csv`

`diagnostic_service` is the main orchestrator. Required diagnostic result
fields are:

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

The result is JSON-compatible and tested with `json.dumps`.

When `normal_profile` is supplied, `diagnose_window` calculates and integrates
the statistical anomaly score. Without a normal profile, `anomaly_score`
remains `0.0`, `risks["statistical_anomaly"]` remains `0.0`, and anomaly
availability is reported as false in debug information.

## 11. Implemented rule-based recommendations

### `servo_diagnostic_model/recommendations/rule_based.py`

Implemented:

- `generate_recommendations`
- `make_recommendation`
- `sort_recommendations`
- `deduplicate_recommendations`
- `limit_recommendations`

Implemented recommendation scenarios include:

- normal monitoring
- unknown state / data quality
- error
- fault
- warning flag
- voltage
- temperature
- current / torque
- velocity
- statistical anomaly

Recommendations are deterministic English templates. No LLM is used.
Recommendations are prioritized, deduplicated by category when possible,
limited to a configured or default maximum, and integrated into
`diagnose_window`.

## 12. Implemented statistical anomaly model

### `servo_diagnostic_model/model/statistical_profile.py`

Implemented:

- `calculate_mad`
- `calculate_feature_stats`
- `infer_numeric_feature_names`
- `fit_normal_profile`
- `save_profile`
- `load_profile`
- `filter_normal_feature_rows`

### `servo_diagnostic_model/model/anomaly_score.py`

Implemented:

- `robust_feature_score`
- `select_profile_for_phase`
- `calculate_anomaly_score`

The statistical model uses median/MAD statistics and robust feature scores.
It supports:

- a global normal profile
- profiles grouped by `motion_phase`
- preference for a matching phase-specific profile
- fallback to the global profile
- safe handling when MAD is zero
- anomaly score clamping to `0..1`

No sklearn, deep-learning framework, or other forbidden ML library is used.
Profile drift detection and automatic retraining are not implemented.

## 13. Implemented normal-profile fitting service

### `servo_diagnostic_model/api/profile_service.py`

Implemented:

- `extract_feature_rows_from_csv`
- `fit_normal_profile_from_csv`
- command-line entry point under `if __name__ == "__main__"`

The service pipeline is:

```text
normal laboratory CSV
  |
  v
data pipeline
  |
  v
windowing
  |
  v
feature extraction
  |
  v
normal-row filtering
  |
  v
fit_normal_profile
  |
  v
save normal_profile.json
```

Current PowerShell command for use after laboratory data collection:

```powershell
.\.venv\Scripts\python.exe -m servo_diagnostic_model.api.profile_service `
  laboratory_normal.csv `
  servo_diagnostic_model/config/normal_profile.json `
  --thresholds servo_diagnostic_model/config/thresholds.json `
  --min-count 5
```

The CSV must contain enough duration and samples to create valid windows.
Recordings containing only error, fault, short, or poor-quality windows are
rejected because no valid normal feature rows remain. The supplied recording
is assumed to represent normal operation; the service does not independently
prove that the recording is healthy.

A real `servo_diagnostic_model/config/normal_profile.json` does not currently
exist. No real normal profile has been trained or verified.

## 14. Config files

Current configuration files:

- `servo_diagnostic_model/config/limits.json`
- `servo_diagnostic_model/config/weights.json`
- `servo_diagnostic_model/config/thresholds.json`

Configuration roles:

- `limits.json` contains starter physical limits used by physical risk
  formulas. These limits must be calibrated for the actual motor, drive,
  power supply, load, cooling, and operating conditions.
- `weights.json` controls the contribution of risk categories to Health
  Score.
- `thresholds.json` controls window duration and step, minimum samples,
  classifier thresholds, anomaly thresholds, risk thresholds, and related
  behavior.
- `normal_profile.json` is generated after laboratory data collection and
  should usually not be manually edited.

At snapshot time, `thresholds.json` does not contain
`max_recommendations` or `robust_z_limit`; the implementation uses its code
defaults for those settings.

## 15. Test status

The exact requested command was run:

```powershell
python -m pytest -q
```

Result:

```text
C:\Program Files\Python312\python.exe: No module named pytest
```

Therefore, the exact system-Python command did not run the suite successfully.

The full suite was then run successfully using the repository virtual
environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .test-tmp-state -p no:cacheprovider
```

Verified result:

```text
149 passed in 0.76s
```

There were no test failures in the full repository-venv run.

Major test files:

- `tests/test_loader.py`
- `tests/test_preprocessing.py`
- `tests/test_windowing.py`
- `tests/test_features.py`
- `tests/test_physical_risks.py`
- `tests/test_health_classifier.py`
- `tests/test_diagnostic_service.py`
- `tests/test_recommendations.py`
- `tests/test_statistical_anomaly.py`
- `tests/test_profile_service.py`

The tests cover normal telemetry, missing optional fields, bad data, errors,
risk ranges, Health Score range, classifier output, recommendations, anomaly
profiles, profile fitting, and JSON serialization.

## 16. Current limitations

- A real `normal_profile.json` has not been trained.
- Real servo-drive physical limits have not been calibrated.
- Hardware validation has not been verified.
- The statistical profile requires real normal telemetry.
- Profile drift detection and automatic retraining are not implemented.
- Synthetic anomaly generation is not implemented.
- Recommendations use deterministic English templates.
- Backend/PWA integration is not implemented.
- Real-time streaming is not implemented.
- Real hardware acquisition code is not implemented in this package.
- Evaluation and plotting utilities are not implemented.
- `preprocess_dataframe` is not currently exposed as a public preprocessing
  helper.
- The system Python environment does not currently have pytest installed;
  use the repository virtual environment for tests.

## 17. What is needed from the laboratory

The next practical requirement is real telemetry from the target laboratory
setup.

Recommended recordings:

1. `normal_lab_session.csv`

   - normal operation
   - no errors or drive faults
   - enough duration for multiple windows
   - include holding, movement, acceleration, and braking if possible
   - cover representative normal loads and duty cycles

2. `test_lab_session.csv`

   - separate data for testing diagnostics
   - should not be the same file used to fit `normal_profile.json`
   - should include representative normal and abnormal operating cases when
     safe and practical

Required or desired columns:

- `t` or `ts`
- `velocity`
- `current_A`
- `torque_Nm`
- `dc_bus_voltage`
- `drive_temp`
- `statusword`
- `error_code`
- `position` if available
- `mode_display` if available

The actual units, sample rate, timestamp quality, drive statusword semantics,
and error-code meanings should be recorded with the data.

## 18. Recommended next steps

1. Commit the current statistical anomaly, profile service, and snapshot work.
2. Collect real normal telemetry in the laboratory.
3. Build `normal_profile.json` using `profile_service`.
4. Run `diagnose_csv` with `normal_profile_path`.
5. Inspect Health Score, Anomaly Score, state, causes, and recommendations.
6. Calibrate `limits.json` using real hardware parameters and observed data.
7. Add synthetic anomaly generation only if needed for demonstration or
   emergency testing.
8. Add reporting and plotting utilities if needed for the article.
9. Prepare reproducible examples and results for the conference article.

## 19. Suggested prompts for future Codex sessions

### Prompt: fit profile after lab data

```text
Use $servo-statistical-anomaly, $servo-data-pipeline, and $servo-testing-evaluation.

I have collected a normal laboratory telemetry CSV. Use the existing
profile_service to build normal_profile.json and verify it can be loaded.

Do not modify model logic unless a bug is found.

Run:
python -m servo_diagnostic_model.api.profile_service <normal_csv_path> servo_diagnostic_model/config/normal_profile.json --thresholds servo_diagnostic_model/config/thresholds.json --min-count 5

Then run tests:
python -m pytest -q

Report:

* whether profile was created
* profile meta summary
* number of global features
* available motion-phase profiles
* any warnings or limitations
```

### Prompt: diagnose data with profile

```text
Use $servo-json-contract and $servo-statistical-anomaly.

Use the existing diagnostic_service to diagnose a telemetry CSV with
normal_profile.json.

Do not modify code unless a bug is found.

Verify:

* anomaly_score is not always 0.0 when profile is supplied
* risks["statistical_anomaly"] is populated
* result remains JSON-compatible
* recommendations are present
```

### Prompt: calibrate limits

```text
Use $servo-config-driven-model and $servo-physical-risk-model.

Update limits.json based on actual servo-drive and motor parameters from the
laboratory setup.

Do not change formulas unless required.

Validate:

* all physical risks remain 0..1
* Health Score remains 0..100
* tests pass
```

## 20. Git status at snapshot time

Before creating this snapshot, the requested `git status` command returned:

```text
On branch main
nothing to commit, working tree clean
```

After creating this snapshot and removing the temporary pytest directory,
`git status --short` returned:

```text
?? markdowns/15_CURRENT_PROJECT_STATE.md
```

This snapshot file should be committed if it is intended to serve as the
handoff for the next Codex session. No Python source, tests, configs,
`AGENTS.md`, skills, or existing Markdown documentation were modified while
creating it.

## 21. Handoff summary

The repository currently contains an end-to-end, deterministic
physical-statistical diagnostic pipeline: CSV loading and validation,
windowing, feature extraction, physical risks, optional median/MAD anomaly
scoring, Health Score, classification, causes, explanations,
recommendations, diagnostic orchestration, and normal-profile fitting.

The repository virtual-environment test suite is verified with `149 passed`.
The system-Python `python -m pytest -q` command is not usable until pytest is
installed in that environment.

What remains is primarily laboratory validation: collect real telemetry, fit
a real normal profile, calibrate physical limits, diagnose separate test
recordings, and evaluate whether the resulting scores and recommendations
match the actual servo-drive behavior.

The next Codex session should first confirm the current git status, then use
the normal-profile fitting service on a verified normal laboratory recording.
