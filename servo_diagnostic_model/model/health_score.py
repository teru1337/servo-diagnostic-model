"""Weighted Health Score calculation and hard safety limits."""

from typing import Any

from .numeric import is_finite_number


def calculate_health_score(
    risks: dict[str, Any] | None,
    weights: dict[str, Any] | None,
    features: dict[str, Any] | None = None,
) -> float:
    """Calculate a normalized weighted Health Score in range 0..100."""

    safe_risks = risks or {}
    safe_weights = weights or {}
    weighted_risk = 0.0
    total_weight = 0.0
    for risk_key, weight in safe_weights.items():
        if not is_finite_number(weight) or weight < 0:
            continue
        if risk_key not in safe_risks or not is_finite_number(safe_risks[risk_key]):
            continue
        weighted_risk += _clamp(float(safe_risks[risk_key]), 0.0, 1.0) * float(weight)
        total_weight += float(weight)

    score = 100.0 if total_weight == 0 else 100.0 * (1.0 - weighted_risk / total_weight)
    return apply_hard_limits(_clamp(score, 0.0, 100.0), safe_risks, features or {})


def apply_hard_limits(
    health_score: float,
    risks: dict[str, Any] | None,
    features: dict[str, Any] | None,
) -> float:
    """Apply documented maximum Health Score caps for critical conditions."""

    score = _clamp(float(health_score), 0.0, 100.0) if is_finite_number(health_score) else 0.0
    safe_risks = risks or {}
    safe_features = features or {}

    if (
        safe_features.get("error_flag") is True
        or safe_features.get("fault_flag") is True
        or _risk_at_least(safe_risks, "error", 1.0)
        or _risk_at_least(safe_risks, "statusword", 1.0)
    ):
        score = min(score, 40.0)
    if _risk_at_least(safe_risks, "temperature", 1.0):
        score = min(score, 50.0)
    if _risk_at_least(safe_risks, "voltage", 1.0):
        score = min(score, 50.0)
    if _risk_at_least(safe_risks, "data_quality", 1.0):
        score = min(score, 60.0)
    return _clamp(score, 0.0, 100.0)


def _risk_at_least(risks: dict[str, Any], key: str, threshold: float) -> bool:
    value = risks.get(key)
    return is_finite_number(value) and _clamp(float(value), 0.0, 1.0) >= threshold


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)
