"""Robust statistical anomaly scoring for Version 0.2."""

from typing import Any

from .numeric import is_finite_number


def robust_feature_score(
    value: float, stats: dict[str, Any], z_limit: float = 5.0
) -> float:
    """Convert a robust z-score to a clamped feature anomaly score."""

    if not is_finite_number(value) or not is_finite_number(stats.get("median")):
        return 0.0
    if not is_finite_number(z_limit) or z_limit <= 0:
        z_limit = 5.0

    scale = stats.get("mad")
    if not is_finite_number(scale) or scale <= 0:
        scale = stats.get("std")
    if not is_finite_number(scale) or scale <= 0:
        scale = 1e-9

    z_score = abs(float(value) - float(stats["median"])) / float(scale)
    return _clamp(z_score / float(z_limit))


def select_profile_for_phase(
    profile: dict[str, Any] | None, motion_phase: str | None
) -> tuple[dict[str, Any], str | None]:
    """Prefer a phase profile and fall back to the global profile."""

    safe_profile = profile or {}
    phase_profiles = safe_profile.get("by_motion_phase")
    if isinstance(phase_profiles, dict) and isinstance(motion_phase, str):
        phase_profile = phase_profiles.get(motion_phase)
        if isinstance(phase_profile, dict) and phase_profile:
            return phase_profile, f"by_motion_phase.{motion_phase}"

    global_profile = safe_profile.get("global")
    if isinstance(global_profile, dict) and global_profile:
        return global_profile, "global"
    return {}, None


def calculate_anomaly_score(
    features: dict[str, Any],
    profile: dict[str, Any] | None = None,
    thresholds: dict[str, Any] | None = None,
    feature_weights: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate a robust weighted anomaly score for one feature row."""

    if profile is None:
        return _unavailable_result()

    selected_profile, profile_name = select_profile_for_phase(
        profile, features.get("motion_phase")
    )
    if not selected_profile:
        return _unavailable_result()

    z_limit = (thresholds or {}).get("robust_z_limit", 5.0)
    feature_scores = {
        feature_name: robust_feature_score(features[feature_name], stats, z_limit)
        for feature_name, stats in selected_profile.items()
        if isinstance(stats, dict) and is_finite_number(features.get(feature_name))
    }
    if not feature_scores:
        return {
            "anomaly_score": 0.0,
            "feature_scores": {},
            "profile_used": profile_name,
            "available": False,
        }

    weights = feature_weights or {}
    weighted_total = 0.0
    total_weight = 0.0
    for feature_name, score in feature_scores.items():
        weight = weights.get(feature_name, 1.0)
        if not is_finite_number(weight) or weight <= 0:
            continue
        weighted_total += score * float(weight)
        total_weight += float(weight)
    mean_score = weighted_total / total_weight if total_weight > 0 else 0.0
    anomaly_score = _clamp(0.7 * mean_score + 0.3 * max(feature_scores.values()))
    return {
        "anomaly_score": anomaly_score,
        "feature_scores": feature_scores,
        "profile_used": profile_name,
        "available": True,
    }


def _unavailable_result() -> dict[str, Any]:
    return {
        "anomaly_score": 0.0,
        "feature_scores": {},
        "profile_used": None,
        "available": False,
    }


def _clamp(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)
