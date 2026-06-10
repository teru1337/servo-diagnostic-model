"""Deterministic rule-based recommendations for Version 0.1."""

import math
from numbers import Real
from typing import Any


PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def make_recommendation(
    priority: str,
    category: str,
    action: str,
    reason: str,
    source_risks: list[str],
    target_role: str,
    confidence: float = 0.8,
    is_blocking: bool = False,
    next_step: str | None = None,
) -> dict[str, Any]:
    """Build one JSON-compatible recommendation from a deterministic template."""

    recommendation: dict[str, Any] = {
        "priority": priority if priority in PRIORITY_ORDER else "low",
        "category": str(category),
        "action": str(action),
        "reason": str(reason),
        "source_risks": list(dict.fromkeys(str(risk) for risk in source_risks)),
        "target_role": str(target_role),
        "confidence": min(max(_number(confidence), 0.0), 1.0),
        "is_blocking": bool(is_blocking),
    }
    if next_step is not None:
        recommendation["next_step"] = str(next_step)
    return recommendation


def sort_recommendations(
    recommendations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return recommendations ordered by priority while preserving ties."""

    return sorted(
        recommendations,
        key=lambda item: PRIORITY_ORDER.get(str(item.get("priority")), 4),
    )


def deduplicate_recommendations(
    recommendations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge recommendations with the same category."""

    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for recommendation in recommendations:
        category = str(recommendation.get("category", "unknown"))
        if category not in merged:
            merged[category] = dict(recommendation)
            merged[category]["source_risks"] = list(
                dict.fromkeys(recommendation.get("source_risks", []))
            )
            order.append(category)
            continue

        current = merged[category]
        current["source_risks"] = list(
            dict.fromkeys(
                [
                    *current.get("source_risks", []),
                    *recommendation.get("source_risks", []),
                ]
            )
        )
        if PRIORITY_ORDER.get(str(recommendation.get("priority")), 4) < PRIORITY_ORDER.get(
            str(current.get("priority")), 4
        ):
            source_risks = current["source_risks"]
            merged[category] = dict(recommendation)
            merged[category]["source_risks"] = source_risks
        else:
            current["is_blocking"] = bool(
                current.get("is_blocking") or recommendation.get("is_blocking")
            )
            current["confidence"] = max(
                _number(current.get("confidence")),
                _number(recommendation.get("confidence")),
            )
    return [merged[category] for category in order]


def limit_recommendations(
    recommendations: list[dict[str, Any]], max_count: int = 3
) -> list[dict[str, Any]]:
    """Limit recommendation count without mutating the input list."""

    if not isinstance(max_count, int) or isinstance(max_count, bool):
        max_count = 3
    return list(recommendations[: max(max_count, 0)])


def generate_recommendations(
    state: str,
    risks: dict[str, Any] | None,
    features: dict[str, Any] | None,
    main_causes: list[dict[str, Any]] | None,
    thresholds: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate deterministic recommendations from state, risks, and features."""

    del main_causes  # Reserved for richer deterministic templates in later versions.
    safe_risks = risks or {}
    safe_features = features or {}
    recommendations: list[dict[str, Any]] = []
    data_quality = _risk(safe_risks, "data_quality")

    if state == "unknown" or data_quality >= 0.75:
        recommendations.append(_data_quality_recommendation(high=True))

    if safe_features.get("error_flag") is True or _risk(safe_risks, "error") >= 1.0:
        recommendations.append(_error_recommendation(safe_features))

    has_fault = (
        safe_features.get("fault_flag") is True
        or _risk(safe_risks, "statusword") >= 1.0
    )
    if has_fault:
        recommendations.append(_fault_recommendation())
    elif safe_features.get("warning_flag") is True:
        recommendations.append(_warning_recommendation())

    if _risk(safe_risks, "voltage") >= 0.75:
        recommendations.append(_voltage_recommendation())

    temperature = _risk(safe_risks, "temperature")
    if temperature >= 0.75:
        recommendations.append(_temperature_recommendation(high=True))
    elif temperature >= 0.5:
        recommendations.append(_temperature_recommendation(high=False))

    mechanical_risks = [
        risk_key
        for risk_key in ("current", "torque")
        if _risk(safe_risks, risk_key) >= 0.75
    ]
    if mechanical_risks:
        recommendations.append(_mechanical_recommendation(mechanical_risks))

    if _risk(safe_risks, "velocity") >= 0.75:
        recommendations.append(_velocity_recommendation())

    anomaly = _risk(safe_risks, "statistical_anomaly")
    if anomaly >= 0.75:
        recommendations.append(_anomaly_recommendation(high=True))
    elif anomaly >= 0.5:
        recommendations.append(_anomaly_recommendation(high=False))

    if 0.5 <= data_quality < 0.75:
        recommendations.append(_data_quality_recommendation(high=False))

    if not recommendations:
        recommendations.append(_normal_recommendation())

    max_count = (thresholds or {}).get("max_recommendations", 3)
    return limit_recommendations(
        sort_recommendations(deduplicate_recommendations(recommendations)),
        max_count=max_count,
    )


def _normal_recommendation() -> dict[str, Any]:
    return make_recommendation(
        "low",
        "normal_operation",
        "Continue monitoring the servo drive.",
        "No recommendation-level risks were detected.",
        [],
        "operator",
        confidence=1.0,
        next_step="Continue observing Health Score and telemetry trends.",
    )


def _data_quality_recommendation(high: bool) -> dict[str, Any]:
    return make_recommendation(
        "high" if high else "medium",
        "data_quality",
        "Check telemetry completeness, timestamps, gaps, and invalid values.",
        "Telemetry quality is insufficient for fully reliable diagnostics.",
        ["data_quality"],
        "engineer" if high else "admin",
        confidence=0.9 if high else 0.85,
        is_blocking=high,
        next_step="Restore a valid telemetry stream and repeat diagnostics.",
    )


def _error_recommendation(features: dict[str, Any]) -> dict[str, Any]:
    codes = features.get("unique_error_codes") or []
    reason = "A non-zero servo drive error code was detected."
    if codes:
        reason += f" Detected error codes: {', '.join(str(code) for code in codes)}."
    return make_recommendation(
        "critical",
        "drive_error",
        "Check error_code against the drive manual and perform the prescribed diagnostics.",
        reason,
        ["error"],
        "engineer",
        confidence=1.0,
        is_blocking=True,
        next_step="Determine the cause before resetting the error or restarting.",
    )


def _fault_recommendation() -> dict[str, Any]:
    return make_recommendation(
        "critical",
        "statusword_fault",
        "Check the statusword, CiA 402 state, and cause of the Fault condition.",
        "The statusword indicates a drive fault.",
        ["statusword"],
        "engineer",
        confidence=1.0,
        is_blocking=True,
        next_step="Do not restart until the fault cause has been checked.",
    )


def _warning_recommendation() -> dict[str, Any]:
    return make_recommendation(
        "high",
        "statusword_fault",
        "Inspect the drive warning state and compare it with current telemetry.",
        "The statusword contains an active warning flag.",
        ["statusword"],
        "engineer",
        confidence=0.9,
        next_step="Identify the warning cause before it develops into a fault.",
    )


def _voltage_recommendation() -> dict[str, Any]:
    return make_recommendation(
        "high",
        "power_supply",
        "Check the power supply, DC bus, braking resistor, and braking mode.",
        "DC-bus voltage risk indicates undervoltage, overvoltage, or instability.",
        ["voltage"],
        "engineer",
        confidence=0.9,
        next_step="Review voltage_min, voltage_max, and voltage_std.",
    )


def _temperature_recommendation(high: bool) -> dict[str, Any]:
    return make_recommendation(
        "high" if high else "medium",
        "thermal",
        (
            "Check cooling, ventilation, duty cycle, and load."
            if high
            else "Observe the temperature trend over subsequent windows."
        ),
        (
            "Temperature or its growth rate is approaching an unsafe range."
            if high
            else "Temperature is not critical, but thermal risk is elevated."
        ),
        ["temperature"],
        "engineer" if high else "operator",
        confidence=0.9 if high else 0.8,
        next_step="Review temp_max and temp_slope.",
    )


def _mechanical_recommendation(source_risks: list[str]) -> dict[str, Any]:
    return make_recommendation(
        "high",
        "mechanical_load",
        "Check mechanical load, coupling, friction, jamming, and motion profile.",
        "Current or torque load is elevated relative to configured limits.",
        source_risks,
        "engineer",
        confidence=0.9,
        next_step="Inspect the driven mechanism and compare current and torque trends.",
    )


def _velocity_recommendation() -> dict[str, Any]:
    return make_recommendation(
        "medium",
        "motion_instability",
        "Check the speed profile and configured maximum speed limit.",
        "Velocity is approaching the configured limit.",
        ["velocity"],
        "engineer",
        confidence=0.75,
        next_step="Compare abs_velocity_max with max_velocity_rpm.",
    )


def _anomaly_recommendation(high: bool) -> dict[str, Any]:
    return make_recommendation(
        "high" if high else "medium",
        "statistical_anomaly",
        (
            "Check the features contributing most to the anomaly score."
            if high
            else "Observe the anomaly trend over subsequent windows."
        ),
        (
            "Current behavior substantially differs from the normal profile."
            if high
            else "A moderate deviation from the normal profile was detected."
        ),
        ["statistical_anomaly"],
        "engineer",
        confidence=0.8 if high else 0.7,
        next_step="Review feature_scores and investigate persistent deviations.",
    )


def _risk(risks: dict[str, Any], key: str) -> float:
    return min(max(_number(risks.get(key)), 0.0), 1.0)


def _number(value: Any) -> float:
    if (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    ):
        return float(value)
    return 0.0
