"""Motion-related telemetry features."""

from typing import Any

from servo_diagnostic_model.data.schemas import TelemetryWindow

from .basic_features import (
    clean_values,
    is_valid_number,
    rms,
    safe_abs_max,
    safe_max,
    safe_mean,
    safe_min,
    safe_std,
)


def calculate_velocity_features(
    window: TelemetryWindow, thresholds: dict[str, Any] | None = None
) -> dict[str, float | None]:
    values = [sample.velocity for sample in window.samples]
    cleaned = clean_values(values)
    threshold = float((thresholds or {}).get("velocity_motion_threshold_rpm", 10.0))
    motion_ratio = (
        sum(abs(value) > threshold for value in cleaned) / len(window.samples)
        if cleaned and window.samples
        else None
    )
    return {
        "velocity_mean": safe_mean(cleaned),
        "velocity_min": safe_min(cleaned),
        "velocity_max": safe_max(cleaned),
        "velocity_std": safe_std(cleaned),
        "velocity_rms": rms(cleaned),
        "abs_velocity_max": safe_abs_max(cleaned),
        "motion_ratio": motion_ratio,
        "hold_ratio": None if motion_ratio is None else 1.0 - motion_ratio,
    }


def calculate_acceleration_features(window: TelemetryWindow) -> dict[str, float | None]:
    accelerations: list[float] = []
    ordered = sorted(
        (sample for sample in window.samples if is_valid_number(sample.t)),
        key=lambda sample: float(sample.t),
    )
    for previous, current in zip(ordered, ordered[1:]):
        if not is_valid_number(previous.velocity) or not is_valid_number(current.velocity):
            continue
        dt = current.t - previous.t
        if not is_valid_number(dt) or dt <= 0:
            continue
        accelerations.append((float(current.velocity) - float(previous.velocity)) / dt)
    return {
        "accel_mean": safe_mean(accelerations),
        "accel_min": safe_min(accelerations),
        "accel_max": safe_max(accelerations),
        "accel_std": safe_std(accelerations),
        "abs_accel_max": safe_abs_max(accelerations),
    }


def calculate_position_features(window: TelemetryWindow) -> dict[str, float | None]:
    values = clean_values(sample.position for sample in window.samples)
    position_min = safe_min(values)
    position_max = safe_max(values)
    return {
        "position_min": position_min,
        "position_max": position_max,
        "position_delta": (
            position_max - position_min
            if position_min is not None and position_max is not None
            else None
        ),
        "position_std": safe_std(values),
    }


def detect_motion_phase(
    features: dict[str, Any], thresholds: dict[str, Any] | None = None
) -> str:
    config = thresholds or {}
    min_samples = int(config.get("min_samples_per_window", 2))
    stop_threshold = float(config.get("velocity_stop_threshold_rpm", 1.0))
    motion_threshold = float(config.get("velocity_motion_threshold_rpm", 10.0))
    accel_threshold = float(config.get("accel_threshold_rpm_s", 10.0))
    stability_threshold = float(config.get("velocity_stability_threshold_rpm", 10.0))

    if int(features.get("sample_count") or 0) < min_samples:
        return "unknown"
    abs_velocity_max = features.get("abs_velocity_max")
    motion_ratio = features.get("motion_ratio")
    if abs_velocity_max is None or motion_ratio is None:
        return "unknown"
    if abs_velocity_max < stop_threshold:
        return "stopped"
    if motion_ratio < 0.2:
        return "holding"

    accel_mean = features.get("accel_mean")
    velocity_mean = features.get("velocity_mean")
    if accel_mean is not None and velocity_mean is not None:
        if accel_mean > accel_threshold and abs(velocity_mean) > motion_threshold:
            return "acceleration"
        if accel_mean < -accel_threshold and abs(velocity_mean) > motion_threshold:
            return "braking"

    velocity_std = features.get("velocity_std")
    if velocity_std is not None and velocity_std < stability_threshold and motion_ratio >= 0.5:
        return "moving"
    return "mixed"
