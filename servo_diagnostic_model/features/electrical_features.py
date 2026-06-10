"""Electrical and load-related telemetry features."""

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


def calculate_current_features(window: TelemetryWindow) -> dict[str, Any]:
    values, unit = _preferred_values(window, "current_A", "current", "A", "relative")
    return _summary("current", values) | {"current_unit": unit}


def calculate_torque_features(window: TelemetryWindow) -> dict[str, Any]:
    values, unit = _preferred_values(window, "torque_Nm", "torque", "Nm", "relative")
    return _summary("torque", values) | {"torque_unit": unit}


def calculate_voltage_features(window: TelemetryWindow) -> dict[str, float | None]:
    values = clean_values(sample.dc_bus_voltage for sample in window.samples)
    voltage_min = safe_min(values)
    voltage_max = safe_max(values)
    return {
        "voltage_mean": safe_mean(values),
        "voltage_min": voltage_min,
        "voltage_max": voltage_max,
        "voltage_std": safe_std(values),
        "voltage_range": (
            voltage_max - voltage_min
            if voltage_min is not None and voltage_max is not None
            else None
        ),
    }


def calculate_load_relation_features(
    window: TelemetryWindow, features: dict[str, Any] | None = None
) -> dict[str, float | None]:
    """Return simple low-speed load features feasible for Version 0.1."""

    low_speed_threshold = 10.0
    low_speed_current = [
        sample.current_A
        for sample in window.samples
        if is_valid_number(sample.velocity)
        and abs(float(sample.velocity)) < low_speed_threshold
    ]
    low_speed_torque = [
        sample.torque_Nm
        for sample in window.samples
        if is_valid_number(sample.velocity)
        and abs(float(sample.velocity)) < low_speed_threshold
    ]
    return {
        "current_at_low_speed": rms(low_speed_current),
        "torque_at_low_speed": rms(low_speed_torque),
    }


def _preferred_values(
    window: TelemetryWindow,
    primary_field: str,
    fallback_field: str,
    primary_unit: str,
    fallback_unit: str,
) -> tuple[list[float], str | None]:
    primary = clean_values(getattr(sample, primary_field, None) for sample in window.samples)
    if primary:
        return primary, primary_unit
    fallback = clean_values(getattr(sample, fallback_field, None) for sample in window.samples)
    if fallback:
        return fallback, fallback_unit
    return [], None


def _summary(prefix: str, values: list[float]) -> dict[str, float | None]:
    return {
        f"{prefix}_mean": safe_mean(values),
        f"{prefix}_min": safe_min(values),
        f"{prefix}_max": safe_max(values),
        f"{prefix}_abs_max": safe_abs_max(values),
        f"{prefix}_rms": rms(values),
        f"{prefix}_std": safe_std(values),
    }
