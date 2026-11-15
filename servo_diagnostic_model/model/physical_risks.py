"""Config-driven physical risk calculations for Version 0.1."""

from typing import Any

from .numeric import is_finite_number


REQUIRED_RISK_KEYS = (
    "current",
    "torque",
    "velocity",
    "voltage",
    "temperature",
    "statusword",
    "error",
    "data_quality",
    "statistical_anomaly",
)

CRITICAL_FEATURE_GROUPS = (
    ("current_rms", "current_abs_max"),
    ("torque_rms", "torque_abs_max"),
    ("abs_velocity_max",),
    ("voltage_min", "voltage_max", "voltage_std"),
    ("temp_max", "temp_slope"),
    ("statusword_available",),
    ("error_flag",),
)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a finite numeric value to the requested range."""

    if not is_finite_number(low) or not is_finite_number(high) or low > high:
        raise ValueError("clamp requires finite limits where low <= high.")
    if not is_finite_number(value):
        return float(low)
    return float(min(max(value, low), high))


def safe_divide(
    numerator: float | None,
    denominator: float | None,
    default: float = 0.0,
) -> float:
    """Divide finite numbers, returning default for invalid input or zero divisor."""

    if not is_finite_number(numerator) or not is_finite_number(denominator) or denominator == 0:
        return float(default)
    return float(numerator / denominator)


def linear_risk(value: float, safe: float, critical: float) -> float:
    """Return linearly increasing risk from safe to critical."""

    if not all(is_finite_number(item) for item in (value, safe, critical)):
        return 0.0
    if critical <= safe:
        return 0.0
    return clamp((value - safe) / (critical - safe))


def inverse_linear_risk(value: float, safe: float, critical: float) -> float:
    """Return linearly increasing risk as value falls from safe to critical."""

    if not all(is_finite_number(item) for item in (value, safe, critical)):
        return 0.0
    if critical >= safe:
        return 0.0
    return clamp((safe - value) / (safe - critical))


def calculate_current_risk(features: dict[str, Any], limits: dict[str, Any]) -> float:
    if features.get("current_unit") != "A":
        return 0.0
    risks = [
        _ratio_risk(features.get("current_rms"), limits.get("rated_current_A")),
        _ratio_risk(features.get("current_abs_max"), limits.get("max_current_A")),
    ]
    if features.get("motion_phase") in {"holding", "stopped"}:
        risks.append(
            _ratio_risk(
                features.get("current_at_low_speed"), limits.get("rated_current_A")
            )
        )
    return clamp(max(risks))


def calculate_torque_risk(features: dict[str, Any], limits: dict[str, Any]) -> float:
    if features.get("torque_unit") != "Nm":
        return 0.0
    risks = [
        _ratio_risk(features.get("torque_rms"), limits.get("rated_torque_Nm")),
        _ratio_risk(features.get("torque_abs_max"), limits.get("max_torque_Nm")),
    ]
    if features.get("motion_phase") in {"holding", "stopped"}:
        risks.append(
            _ratio_risk(
                features.get("torque_at_low_speed"), limits.get("rated_torque_Nm")
            )
        )
    return clamp(max(risks))


def calculate_velocity_risk(features: dict[str, Any], limits: dict[str, Any]) -> float:
    return _ratio_risk(features.get("abs_velocity_max"), limits.get("max_velocity_rpm"))


def calculate_voltage_risk(features: dict[str, Any], limits: dict[str, Any]) -> float:
    low = inverse_linear_risk(
        features.get("voltage_min"),
        limits.get("dc_bus_min_safe"),
        limits.get("dc_bus_min_critical"),
    )
    high = linear_risk(
        features.get("voltage_max"),
        limits.get("dc_bus_max_safe"),
        limits.get("dc_bus_max_critical"),
    )
    unstable = _ratio_risk(
        features.get("voltage_std"), limits.get("voltage_std_limit")
    )
    return clamp(max(low, high, unstable))


def calculate_temperature_risk(
    features: dict[str, Any], limits: dict[str, Any]
) -> float:
    level = linear_risk(
        features.get("temp_max"),
        limits.get("temp_safe"),
        limits.get("temp_critical"),
    )
    slope = features.get("temp_slope")
    slope_risk = (
        _ratio_risk(max(float(slope), 0.0), limits.get("temp_slope_limit"))
        if is_finite_number(slope)
        else 0.0
    )
    slope_risk = _gate_safe_temperature_slope_risk(slope_risk, features, limits)
    return clamp(max(level, slope_risk))


def calculate_error_risk(features: dict[str, Any]) -> float:
    return 1.0 if features.get("error_flag") is True else 0.0


def calculate_statusword_risk(features: dict[str, Any]) -> float:
    if features.get("fault_flag") is True:
        return 1.0
    if features.get("statusword_available") is not True:
        risk = 0.3
    elif features.get("warning_flag") is True:
        risk = 0.6
    else:
        risk = 0.0
    if (
        features.get("operation_enabled_ratio") == 0
        and features.get("motion_phase") != "stopped"
    ):
        risk = max(risk, 0.4)
    return clamp(risk)


def calculate_data_quality_risk(
    features: dict[str, Any], limits: dict[str, Any]
) -> float:
    risks = [
        _ratio_risk(features.get("missing_ratio"), limits.get("missing_ratio_limit")),
        _ratio_risk(features.get("invalid_ratio"), limits.get("invalid_ratio_limit")),
        _ratio_risk(
            features.get("time_gap_count"), limits.get("time_gap_count_limit")
        ),
        1.0 if features.get("is_too_short") is True else 0.0,
        _missing_critical_features_risk(features),
    ]
    return clamp(max(risks))


def calculate_physical_risks(
    features: dict[str, Any] | None, limits: dict[str, Any] | None
) -> dict[str, float]:
    """Calculate all Version 0.1 risks and clamp every output."""

    safe_features = features or {}
    safe_limits = limits or {}
    risks = {
        "current": calculate_current_risk(safe_features, safe_limits),
        "torque": calculate_torque_risk(safe_features, safe_limits),
        "velocity": calculate_velocity_risk(safe_features, safe_limits),
        "voltage": calculate_voltage_risk(safe_features, safe_limits),
        "temperature": calculate_temperature_risk(safe_features, safe_limits),
        "statusword": calculate_statusword_risk(safe_features),
        "error": calculate_error_risk(safe_features),
        "data_quality": calculate_data_quality_risk(safe_features, safe_limits),
        "statistical_anomaly": 0.0,
    }
    return {key: clamp(risks[key]) for key in REQUIRED_RISK_KEYS}


def _ratio_risk(value: Any, limit: Any) -> float:
    if not is_finite_number(value) or not is_finite_number(limit) or limit <= 0:
        return 0.0
    return clamp(safe_divide(abs(float(value)), float(limit)))


def _gate_safe_temperature_slope_risk(
    slope_risk: float,
    features: dict[str, Any],
    limits: dict[str, Any],
) -> float:
    temp_max = features.get("temp_max")
    temp_safe = limits.get("temp_safe")
    if not is_finite_number(temp_max) or not is_finite_number(temp_safe) or temp_max >= temp_safe:
        return clamp(slope_risk)

    safe_cap = limits.get("temp_slope_safe_risk_cap")
    if is_finite_number(safe_cap):
        slope_risk = min(slope_risk, clamp(float(safe_cap)))

    temp_min = features.get("temp_min")
    quantized_range = limits.get("temp_quantized_range_C")
    quantized_cap = limits.get("temp_slope_quantized_risk_cap")
    if (
        is_finite_number(temp_min)
        and is_finite_number(quantized_range)
        and quantized_range >= 0
        and is_finite_number(quantized_cap)
        and float(temp_max) - float(temp_min) <= float(quantized_range)
    ):
        slope_risk = min(slope_risk, clamp(float(quantized_cap)))
    return clamp(slope_risk)


def _missing_critical_features_risk(features: dict[str, Any]) -> float:
    if not features:
        return 1.0
    missing_groups = sum(
        not any(_feature_available(features, name) for name in group)
        for group in CRITICAL_FEATURE_GROUPS
    )
    return missing_groups / len(CRITICAL_FEATURE_GROUPS)


def _feature_available(features: dict[str, Any], name: str) -> bool:
    if name not in features or features[name] is None:
        return False
    value = features[name]
    if name == "statusword_available":
        return value is True
    return isinstance(value, bool) or is_finite_number(value)
