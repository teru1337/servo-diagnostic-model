"""Rule-based state classification for Version 0.1."""

import math
from numbers import Real
from typing import Any


VALID_STATES = {"normal", "observation", "warning", "critical", "unknown"}


def classify_state(
    health_score: float | None,
    anomaly_score: float | None,
    risks: dict[str, Any] | None,
    thresholds: dict[str, Any] | None,
    features: dict[str, Any] | None,
) -> str:
    safe_risks = risks or {}
    safe_thresholds = thresholds or {}
    safe_features = features or {}

    if not _is_number(health_score):
        return "unknown"
    if safe_features.get("sample_count") == 0:
        return "unknown"
    if (
        safe_features.get("is_too_short") is True
        and _risk_value(safe_risks.get("data_quality")) >= 1.0
    ):
        return "unknown"

    if safe_features.get("error_flag") is True or safe_features.get("fault_flag") is True:
        return "critical"
    if _risk_value(safe_risks.get("error")) >= 1.0:
        return "critical"
    if _risk_value(safe_risks.get("statusword")) >= 1.0:
        return "critical"

    health_warning = _threshold(safe_thresholds, "health_warning", 50.0)
    health_observation = _threshold(safe_thresholds, "health_observation", 70.0)
    health_normal = _threshold(safe_thresholds, "health_normal", 85.0)
    anomaly_observation = _threshold(safe_thresholds, "anomaly_observation", 0.3)
    anomaly_warning = _threshold(safe_thresholds, "anomaly_warning", 0.5)
    anomaly_critical = _threshold(safe_thresholds, "anomaly_critical", 0.75)
    risk_observation = _threshold(safe_thresholds, "risk_observation", 0.5)
    risk_warning = _threshold(safe_thresholds, "risk_warning", 0.75)
    risk_critical = _threshold(safe_thresholds, "risk_critical", 0.9)
    anomaly = _risk_value(anomaly_score)
    score = float(health_score)
    excluded = ["statistical_anomaly", "data_quality"]

    if score < health_warning or anomaly >= anomaly_critical:
        return "critical"
    if has_risk_above(safe_risks, risk_critical, exclude=excluded):
        return "critical"
    if score < health_observation or anomaly >= anomaly_warning:
        return "warning"
    if has_risk_above(safe_risks, risk_warning, exclude=excluded):
        return "warning"
    if score < health_normal or anomaly >= anomaly_observation:
        return "observation"
    if has_risk_above(safe_risks, risk_observation, exclude=excluded):
        return "observation"
    return "normal"


def risk_level_from_state(state: str) -> str:
    return {
        "normal": "low",
        "observation": "medium",
        "warning": "high",
        "critical": "critical",
        "unknown": "unknown",
    }.get(state, "unknown")


def has_risk_above(
    risks: dict[str, Any] | None,
    threshold: float,
    exclude: list[str] | None = None,
) -> bool:
    excluded = set(exclude or [])
    if not _is_number(threshold):
        return False
    return any(
        key not in excluded and _risk_value(value) >= float(threshold)
        for key, value in (risks or {}).items()
    )


def _threshold(thresholds: dict[str, Any], key: str, default: float) -> float:
    value = thresholds.get(key)
    return float(value) if _is_number(value) else default


def _risk_value(value: Any) -> float:
    if not _is_number(value):
        return 0.0
    return min(max(float(value), 0.0), 1.0)


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )
