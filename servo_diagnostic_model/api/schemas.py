"""JSON-compatible API contracts for diagnostic results."""

from typing import Any, TypedDict


class DiagnosticResult(TypedDict):
    """Version 0.1 diagnostic result returned for one telemetry window."""

    window_start: float
    window_end: float
    device_id: str | None
    health_score: float
    anomaly_score: float
    state: str
    risk_level: str
    motion_phase: str
    features: dict[str, Any]
    risks: dict[str, float]
    main_causes: list[dict[str, Any]]
    explanation: list[str]
    recommendations: list[dict[str, Any]]
    data_quality: dict[str, Any]
    debug: dict[str, Any]


REQUIRED_RESULT_FIELDS = frozenset(DiagnosticResult.__required_keys__)
