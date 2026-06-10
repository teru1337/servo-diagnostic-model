"""Median/MAD normal profiles for Version 0.2 statistical diagnostics."""

import json
import math
from numbers import Real
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any


EXCLUDED_FEATURE_NAMES = {
    "window_start",
    "window_end",
    "sample_count",
    "sampling_rate_hz",
    "statusword",
    "error_code",
    "error_flag",
    "error_count",
    "fault_flag",
    "fault_count",
    "warning_flag",
    "warning_count",
    "statusword_available",
    "operation_enabled_ratio",
    "missing_ratio",
    "invalid_ratio",
    "time_gap_count",
    "is_too_short",
}


def calculate_mad(values: list[float]) -> float:
    """Calculate median absolute deviation for finite numeric values."""

    cleaned = _clean_values(values)
    if not cleaned:
        return 0.0
    center = median(cleaned)
    return float(median(abs(value - center) for value in cleaned))


def calculate_feature_stats(values: list[float]) -> dict[str, float | int]:
    """Calculate JSON-compatible summary statistics for one feature."""

    cleaned = _clean_values(values)
    if not cleaned:
        return {}
    return {
        "median": float(median(cleaned)),
        "mad": calculate_mad(cleaned),
        "mean": float(mean(cleaned)),
        "std": float(pstdev(cleaned)),
        "min": float(min(cleaned)),
        "max": float(max(cleaned)),
        "count": len(cleaned),
    }


def infer_numeric_feature_names(feature_rows: list[dict[str, Any]]) -> list[str]:
    """Infer stable numeric diagnostic feature names from feature rows."""

    names = {
        name
        for row in feature_rows
        for name, value in row.items()
        if name not in EXCLUDED_FEATURE_NAMES and _is_number(value)
    }
    return sorted(names)


def fit_normal_profile(
    feature_rows: list[dict[str, Any]],
    feature_names: list[str] | None = None,
    min_count: int = 5,
) -> dict[str, Any]:
    """Fit global and motion-phase normal profiles from normal feature rows."""

    if min_count <= 0:
        raise ValueError("min_count must be greater than zero.")
    normal_rows = filter_normal_feature_rows(feature_rows)
    selected_names = (
        list(dict.fromkeys(feature_names))
        if feature_names is not None
        else infer_numeric_feature_names(normal_rows)
    )
    rows_by_phase: dict[str, list[dict[str, Any]]] = {}
    for row in normal_rows:
        phase = row.get("motion_phase")
        if isinstance(phase, str) and phase:
            rows_by_phase.setdefault(phase, []).append(row)

    return {
        "meta": {
            "version": "0.2",
            "min_count": min_count,
            "feature_names": selected_names,
            "row_count": len(normal_rows),
            "reliable": len(normal_rows) >= min_count,
        },
        "global": _profile_for_rows(normal_rows, selected_names, min_count),
        "by_motion_phase": {
            phase: stats
            for phase, rows in sorted(rows_by_phase.items())
            if (stats := _profile_for_rows(rows, selected_names, min_count))
        },
    }


def save_profile(profile: dict[str, Any], path: str) -> None:
    """Save a normal profile as JSON."""

    profile_path = Path(path)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(profile, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )


def load_profile(path: str) -> dict[str, Any]:
    """Load a normal profile from JSON."""

    profile_path = Path(path)
    if not profile_path.is_file():
        raise FileNotFoundError(f"Normal profile not found: {profile_path}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError(f"Normal profile must contain a JSON object: {profile_path}")
    return profile


def filter_normal_feature_rows(
    feature_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Exclude error, fault, short, and poor-quality rows from profile fitting."""

    return [
        row
        for row in feature_rows
        if isinstance(row, dict)
        and row.get("error_flag") is not True
        and row.get("fault_flag") is not True
        and row.get("is_too_short") is not True
        and _quality_below(row.get("missing_ratio"), 0.1)
        and _quality_below(row.get("invalid_ratio"), 0.1)
    ]


def _profile_for_rows(
    rows: list[dict[str, Any]], feature_names: list[str], min_count: int
) -> dict[str, dict[str, float | int]]:
    profile: dict[str, dict[str, float | int]] = {}
    for feature_name in feature_names:
        values = [
            float(row[feature_name])
            for row in rows
            if _is_number(row.get(feature_name))
        ]
        if len(values) >= min_count:
            profile[feature_name] = calculate_feature_stats(values)
    return profile


def _clean_values(values: list[Any]) -> list[float]:
    return [float(value) for value in values if _is_number(value)]


def _quality_below(value: Any, limit: float) -> bool:
    return value is None or (_is_number(value) and float(value) < limit)


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )
