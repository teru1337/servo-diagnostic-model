"""Version 0.1 diagnostic service orchestration."""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any

from servo_diagnostic_model.data.schemas import TelemetryDataset, TelemetryWindow
from servo_diagnostic_model.data.windowing import (
    calculate_duration,
    estimate_sampling_rate,
    make_windows,
)
from servo_diagnostic_model.features.feature_extractor import extract_features
from servo_diagnostic_model.model.classifier import classify_state, risk_level_from_state
from servo_diagnostic_model.model.explanation import (
    generate_explanation,
    get_main_causes,
)
from servo_diagnostic_model.model.health_score import calculate_health_score
from servo_diagnostic_model.model.physical_risks import calculate_physical_risks

from .schemas import DiagnosticResult


def load_json_config(path: str) -> dict[str, Any]:
    """Load and validate a JSON object configuration."""

    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with config_path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration must contain a JSON object: {config_path}")
    return config


def diagnose_window(
    window: TelemetryWindow,
    limits: dict[str, Any],
    weights: dict[str, Any],
    thresholds: dict[str, Any],
    normal_profile: dict[str, Any] | None = None,
) -> DiagnosticResult:
    """Run the Version 0.1 diagnostic pipeline for one telemetry window."""

    features = extract_features(window, thresholds)
    risks = calculate_physical_risks(features, limits)

    anomaly_result = {
        "anomaly_score": 0.0,
        "feature_scores": {},
        "available": False,
    }
    anomaly_score = anomaly_result["anomaly_score"]
    risks["statistical_anomaly"] = anomaly_score

    health_score = calculate_health_score(risks, weights, features)
    state = classify_state(health_score, anomaly_score, risks, thresholds, features)
    main_causes = get_main_causes(
        risks,
        features,
        min_risk=float(thresholds.get("min_risk_for_main_cause", 0.3)),
    )
    result: DiagnosticResult = {
        "window_start": window.start_t,
        "window_end": window.end_t,
        "device_id": window.device_id,
        "health_score": health_score,
        "anomaly_score": anomaly_score,
        "state": state,
        "risk_level": risk_level_from_state(state),
        "motion_phase": features.get("motion_phase", "unknown"),
        "features": features,
        "risks": risks,
        "main_causes": main_causes,
        "explanation": generate_explanation(
            state,
            health_score,
            anomaly_score,
            risks,
            features,
            main_causes,
        ),
        "recommendations": [],
        "data_quality": _data_quality_summary(features, risks),
        "debug": {
            "anomaly": anomaly_result,
            "normal_profile_provided": normal_profile is not None,
            "statistical_anomaly_enabled": False,
        },
    }
    return _to_json_compatible(result)


def diagnose_dataset(
    dataset: TelemetryDataset,
    limits: dict[str, Any],
    weights: dict[str, Any],
    thresholds: dict[str, Any],
    normal_profile: dict[str, Any] | None = None,
) -> list[DiagnosticResult]:
    """Create windows and diagnose a validated telemetry dataset."""

    if dataset.validation_errors:
        return []
    windows = make_windows(
        dataset.samples,
        window_seconds=float(thresholds.get("window_seconds", 5.0)),
        step_seconds=float(thresholds.get("window_step_seconds", 1.0)),
        min_samples=int(thresholds.get("min_samples_per_window", 10)),
    )
    return [
        diagnose_window(window, limits, weights, thresholds, normal_profile)
        for window in windows
    ]


def diagnose_csv(
    csv_path: str,
    limits_path: str,
    weights_path: str,
    thresholds_path: str,
    normal_profile_path: str | None = None,
) -> list[DiagnosticResult]:
    """Load, validate, window, and diagnose a telemetry CSV."""

    from servo_diagnostic_model.data.loader import load_telemetry
    from servo_diagnostic_model.data.preprocessing import (
        coerce_numeric_columns,
        dataframe_to_samples,
        normalize_column_names,
        parse_time_columns,
        sort_by_time,
    )
    from servo_diagnostic_model.data.validator import validate_dataframe

    limits = load_json_config(limits_path)
    weights = load_json_config(weights_path)
    thresholds = load_json_config(thresholds_path)
    normal_profile = (
        load_json_config(normal_profile_path) if normal_profile_path is not None else None
    )

    dataframe = load_telemetry(csv_path)
    dataframe = normalize_column_names(dataframe)
    dataframe = parse_time_columns(dataframe)
    dataframe = coerce_numeric_columns(dataframe)
    dataframe = sort_by_time(dataframe)
    validation_errors, validation_warnings = validate_dataframe(dataframe)
    samples = dataframe_to_samples(dataframe)
    dataset = TelemetryDataset(
        samples=samples,
        columns_available={
            column: True for column in dataframe.columns
        },
        validation_errors=validation_errors,
        validation_warnings=validation_warnings,
        sampling_rate_hz=estimate_sampling_rate(samples),
        duration_s=calculate_duration(samples),
        device_id=_detect_device_id(samples),
    )
    return diagnose_dataset(dataset, limits, weights, thresholds, normal_profile)


def _data_quality_summary(
    features: dict[str, Any], risks: dict[str, float]
) -> dict[str, Any]:
    return {
        "risk": risks.get("data_quality"),
        "missing_ratio": features.get("missing_ratio"),
        "invalid_ratio": features.get("invalid_ratio"),
        "time_gap_count": features.get("time_gap_count"),
        "is_too_short": features.get("is_too_short"),
        "sample_count": features.get("sample_count"),
    }


def _detect_device_id(samples: list[Any]) -> str | None:
    device_ids = {
        sample.device_id for sample in samples if sample.device_id is not None
    }
    return next(iter(device_ids)) if len(device_ids) == 1 else None


def _to_json_compatible(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _to_json_compatible(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_to_json_compatible(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Real) and not isinstance(value, bool):
        numeric = float(value)
        if not math.isfinite(numeric):
            return None
        return int(value) if isinstance(value, int) else numeric
    if value is None or isinstance(value, (str, bool)):
        return value
    return str(value)
