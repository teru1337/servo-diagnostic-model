"""Main-cause selection and deterministic human-readable explanations."""

from typing import Any

from .numeric import is_finite_number, bounded_risk


CAUSE_DETAILS = {
    "current": (
        "current_A",
        "Current load is elevated and may indicate overload or increased mechanical resistance.",
    ),
    "torque": (
        "torque_Nm",
        "Load torque is elevated relative to the permitted operating range.",
    ),
    "velocity": (
        "velocity",
        "Velocity is approaching the configured speed limit.",
    ),
    "voltage": (
        "dc_bus_voltage",
        "DC-bus voltage shows undervoltage, overvoltage, or instability risk.",
    ),
    "temperature": (
        "drive_temp",
        "Drive temperature or temperature growth is approaching an unsafe range.",
    ),
    "error": ("error_code", "A non-zero drive error code was detected."),
    "statusword": (
        "statusword",
        "The drive statusword contains a fault, warning, or unavailable status.",
    ),
    "statistical_anomaly": (
        "anomaly_score",
        "Current behavior differs from the normal statistical profile.",
    ),
    "data_quality": (
        "telemetry",
        "Telemetry quality is reduced by missing, invalid, short, or gapped data.",
    ),
}

STATE_MESSAGES = {
    "normal": "Drive condition is assessed as normal.",
    "observation": "Drive condition requires observation.",
    "warning": "A warning condition was detected.",
    "critical": "A critical drive condition was detected.",
    "unknown": "Drive condition cannot be determined reliably.",
}


def severity_from_risk(risk: float) -> str:
    value = bounded_risk(risk)
    if value >= 0.75:
        return "critical"
    if value >= 0.5:
        return "warning"
    if value >= 0.3:
        return "observation"
    return "low"


def get_main_causes(
    risks: dict[str, Any] | None,
    features: dict[str, Any] | None,
    top_n: int = 3,
    min_risk: float = 0.3,
) -> list[dict[str, Any]]:
    if top_n <= 0:
        return []
    minimum = bounded_risk(min_risk)
    ranked = sorted(
        (
            (key, bounded_risk(value))
            for key, value in (risks or {}).items()
            if is_finite_number(value) and bounded_risk(value) >= minimum
        ),
        key=lambda item: (-item[1], item[0]),
    )
    causes: list[dict[str, Any]] = []
    for risk_key, risk_value in ranked[:top_n]:
        parameter, message = CAUSE_DETAILS.get(
            risk_key,
            (risk_key, f"Risk '{risk_key}' is elevated."),
        )
        causes.append(
            {
                "risk_key": risk_key,
                "parameter": parameter,
                "risk_value": risk_value,
                "severity": severity_from_risk(risk_value),
                "message": message,
            }
        )
    return causes


def generate_explanation(
    state: str,
    health_score: float,
    anomaly_score: float,
    risks: dict[str, Any] | None,
    features: dict[str, Any] | None,
    main_causes: list[dict[str, Any]] | None,
) -> list[str]:
    safe_state = state if state in STATE_MESSAGES else "unknown"
    messages = [STATE_MESSAGES[safe_state]]
    if is_finite_number(health_score):
        messages.append(f"Health Score is {min(max(float(health_score), 0.0), 100.0):.1f}.")
    if safe_state == "unknown":
        messages.append("Telemetry is insufficient or its quality is too low.")
    elif safe_state == "normal":
        messages.append("No significant physical risks, error flags, or fault flags were detected.")
    else:
        causes = main_causes or []
        if causes:
            messages.extend(str(cause.get("message", "")) for cause in causes if cause.get("message"))
        else:
            messages.append("The state is driven by Health Score or anomaly thresholds.")
    if bounded_risk(anomaly_score) > 0:
        messages.append(f"Anomaly Score is {bounded_risk(anomaly_score):.3f}.")
    return messages
