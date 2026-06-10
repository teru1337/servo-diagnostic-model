"""Orchestration for Version 0.1 feature extraction."""

from statistics import median
from typing import Any

from servo_diagnostic_model.data.schemas import TelemetryWindow

from .basic_features import is_valid_number
from .electrical_features import (
    calculate_current_features,
    calculate_load_relation_features,
    calculate_torque_features,
    calculate_voltage_features,
)
from .motion_features import (
    calculate_acceleration_features,
    calculate_position_features,
    calculate_velocity_features,
    detect_motion_phase,
)
from .status_features import calculate_status_features
from .thermal_features import calculate_temperature_features


QUALITY_FIELDS = (
    "velocity",
    "current_A",
    "torque_Nm",
    "dc_bus_voltage",
    "drive_temp",
    "statusword",
    "error_code",
)


def extract_features(
    window: TelemetryWindow, thresholds: dict[str, Any] | None = None
) -> dict[str, Any]:
    features: dict[str, Any] = {
        "window_start": window.start_t,
        "window_end": window.end_t,
        "sample_count": len(window.samples),
        "device_id": window.device_id,
        "sampling_rate_hz": window.sampling_rate_hz,
    }
    features.update(calculate_velocity_features(window, thresholds))
    features.update(calculate_acceleration_features(window))
    features.update(calculate_position_features(window))
    features.update(calculate_current_features(window))
    features.update(calculate_torque_features(window))
    features.update(calculate_voltage_features(window))
    features.update(calculate_load_relation_features(window, features))
    features.update(calculate_temperature_features(window))
    features.update(calculate_status_features(window))
    features.update(calculate_data_quality_features(window, thresholds))
    features["motion_phase"] = detect_motion_phase(features, thresholds)
    return features


def calculate_data_quality_features(
    window: TelemetryWindow, thresholds: dict[str, Any] | None = None
) -> dict[str, Any]:
    sample_count = len(window.samples)
    total_values = sample_count * len(QUALITY_FIELDS)
    missing_count = 0
    invalid_count = 0
    for sample in window.samples:
        for field in QUALITY_FIELDS:
            value = getattr(sample, field, None)
            if value is None:
                missing_count += 1
            elif not is_valid_number(value):
                invalid_count += 1

    times = sorted(sample.t for sample in window.samples if is_valid_number(sample.t))
    positive_deltas = [
        current - previous
        for previous, current in zip(times, times[1:])
        if current - previous > 0
    ]
    expected_dt = None
    if window.sampling_rate_hz is not None and window.sampling_rate_hz > 0:
        expected_dt = 1.0 / window.sampling_rate_hz
    elif positive_deltas:
        expected_dt = median(positive_deltas)
    gap_multiplier = float((thresholds or {}).get("time_gap_multiplier", 3.0))
    time_gap_count = (
        sum(delta > expected_dt * gap_multiplier for delta in positive_deltas)
        if expected_dt is not None
        else 0
    )
    min_samples = int((thresholds or {}).get("min_samples_per_window", 10))
    return {
        "missing_ratio": missing_count / total_values if total_values else None,
        "invalid_ratio": invalid_count / total_values if total_values else None,
        "time_gap_count": time_gap_count,
        "is_too_short": sample_count < min_samples,
    }
