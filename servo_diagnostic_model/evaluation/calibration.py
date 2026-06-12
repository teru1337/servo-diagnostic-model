"""Evaluation-only anomaly-threshold calibration utilities."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


PHYSICAL_RISK_KEYS = ("current", "torque", "velocity", "voltage", "temperature")
RISK_KEYS = PHYSICAL_RISK_KEYS + (
    "statistical_anomaly", "data_quality", "error", "statusword"
)
GROUP_ORDER = (
    "normal_validation", "transition", "elevated_load", "pre_emergency_proxy"
)
E2_TOKEN = "E2_LOAD_MED_INERTIA_R02"


def load_diagnostic_results(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate manifest-wrapped diagnostic result JSON."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("Diagnostic results must contain a JSON list.")
    return value


def _group_label(manifest: dict[str, Any]) -> str:
    label = str(manifest.get("risk_label", "")).strip()
    if label == "normal":
        return "normal_validation"
    return label or "unknown"


def flatten_diagnostic_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten manifest-wrapped diagnostics into analysis-ready window rows."""

    rows: list[dict[str, Any]] = []
    for entry in results:
        manifest = entry.get("manifest", {})
        for window in entry.get("windows", []):
            risks = window.get("risks", {})
            physical = [
                float(risks[key])
                for key in PHYSICAL_RISK_KEYS
                if risks.get(key) is not None
            ]
            row = {
                "source_path": manifest.get("path"),
                "experiment_id": manifest.get("experiment_id"),
                "session_id": manifest.get("session_id"),
                "group": _group_label(manifest),
                "window_start": window.get("window_start"),
                "window_end": window.get("window_end"),
                "health_score": window.get("health_score"),
                "anomaly_score": window.get("anomaly_score"),
                "state": window.get("state"),
                "risk_level": window.get("risk_level"),
                "motion_phase": window.get("motion_phase"),
                "max_physical_risk": max(physical) if physical else None,
                "feature_scores": window.get("debug", {})
                .get("anomaly", {})
                .get("feature_scores", {}),
                "profile_used": window.get("debug", {})
                .get("anomaly", {})
                .get("profile_used"),
            }
            row.update({f"{key}_risk": risks.get(key) for key in RISK_KEYS})
            rows.append(row)
    json.dumps(rows, allow_nan=False)
    return rows


def _scores(rows: Iterable[dict[str, Any]]) -> list[float]:
    return [float(row["anomaly_score"]) for row in rows if row.get("anomaly_score") is not None]


def _rate(rows: list[dict[str, Any]], threshold: float) -> float | None:
    return sum(float(row["anomaly_score"]) >= threshold for row in rows) / len(rows) if rows else None


def _session_ranks(rows: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    sessions: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row.get("session_id") and row.get("anomaly_score") is not None:
            sessions[str(row["session_id"])].append(float(row["anomaly_score"]))
    by_max = sorted(sessions, key=lambda key: max(sessions[key]), reverse=True)
    by_mean = sorted(sessions, key=lambda key: mean(sessions[key]), reverse=True)
    max_rank = next((i + 1 for i, key in enumerate(by_max) if E2_TOKEN in key), None)
    mean_rank = next((i + 1 for i, key in enumerate(by_mean) if E2_TOKEN in key), None)
    return max_rank, mean_rank


def run_anomaly_threshold_sweep(
    rows: list[dict[str, Any]],
    thresholds: list[float],
    warning_target_min: float = 0.05,
    warning_target_max: float = 0.10,
) -> list[dict[str, Any]]:
    """Simulate anomaly-warning threshold behavior without invoking the classifier."""

    groups = {group: [row for row in rows if row.get("group") == group] for group in GROUP_ORDER}
    normal = groups["normal_validation"]
    normal_scores = _scores(normal)
    e2 = [row for row in rows if E2_TOKEN in str(row.get("session_id", ""))]
    e2_scores = _scores(e2)
    e2_max_rank, e2_mean_rank = _session_ranks(rows)
    means = {group: mean(_scores(group_rows)) for group, group_rows in groups.items() if _scores(group_rows)}
    maxima = {group: max(_scores(group_rows)) for group, group_rows in groups.items() if _scores(group_rows)}
    ordering = all(
        means.get(left, float("inf")) < means.get(right, float("-inf"))
        for left, right in zip(GROUP_ORDER, GROUP_ORDER[1:])
    )
    critical_windows = sum(row.get("state") == "critical" for row in normal)
    output = []
    for threshold in thresholds:
        threshold = round(float(threshold), 10)
        normal_warning = sum(score >= threshold for score in normal_scores)
        result: dict[str, Any] = {
            "threshold": threshold,
            "normal_windows": len(normal),
            "normal_mean_anomaly": mean(normal_scores) if normal_scores else None,
            "normal_max_anomaly": max(normal_scores) if normal_scores else None,
            "normal_warning_or_higher_windows": normal_warning,
            "normal_warning_or_higher_rate": normal_warning / len(normal) if normal else None,
            "normal_critical_windows": critical_windows,
            "normal_critical_rate": critical_windows / len(normal) if normal else None,
            "e2_r02_max_anomaly": max(e2_scores) if e2_scores else None,
            "e2_r02_mean_anomaly": mean(e2_scores) if e2_scores else None,
            "e2_r02_detection_rate_above_threshold": _rate(e2, threshold),
            "e2_r02_rank_by_max_anomaly": e2_max_rank,
            "e2_r02_rank_by_mean_anomaly": e2_mean_rank,
            "ordering_holds": ordering,
        }
        for group, group_rows in groups.items():
            scores = _scores(group_rows)
            result[f"{group}_windows"] = len(group_rows)
            result[f"{group}_mean_anomaly"] = mean(scores) if scores else None
            result[f"{group}_max_anomaly"] = max(scores) if scores else None
            result[f"{group}_detection_windows_above_threshold"] = sum(
                score >= threshold for score in scores
            )
            result[f"{group}_detection_rate_above_threshold"] = _rate(group_rows, threshold)
        result.update(
            {
                "transition_mean_anomaly": means.get("transition"),
                "elevated_load_mean_anomaly": means.get("elevated_load"),
                "pre_emergency_proxy_mean_anomaly": means.get("pre_emergency_proxy"),
                "mean_gap_transition_minus_normal": means.get("transition", 0) - means.get("normal_validation", 0),
                "mean_gap_elevated_minus_normal": means.get("elevated_load", 0) - means.get("normal_validation", 0),
                "mean_gap_pre_emergency_minus_normal": means.get("pre_emergency_proxy", 0) - means.get("normal_validation", 0),
                "mean_gap_e2_minus_transition": (mean(e2_scores) - means.get("transition", 0)) if e2_scores else None,
                "mean_gap_e2_minus_elevated_load": (mean(e2_scores) - means.get("elevated_load", 0)) if e2_scores else None,
            }
        )
        result["target_fpr_match"] = warning_target_min <= result["normal_warning_or_higher_rate"] <= warning_target_max
        result["acceptable_critical_fpr"] = result["normal_critical_rate"] <= 0.005
        result["e2_still_detected"] = (
            (result["e2_r02_detection_rate_above_threshold"] or 0) > 0
            and (e2_max_rank or 999) <= 3
        )
        result["recommended_candidate"] = all(
            result[key]
            for key in ("target_fpr_match", "acceptable_critical_fpr", "ordering_holds", "e2_still_detected")
        )
        output.append(result)
    return output


def select_calibration_candidate(sweep_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the strongest threshold-only candidate under the stated priorities."""

    if not sweep_rows:
        raise ValueError("Threshold sweep is empty.")
    matches = [row for row in sweep_rows if row["target_fpr_match"]]
    if matches:
        candidates = matches
        target_reached = True
        reason = "A threshold reaches the 5-10% normal warning false-positive target."
    else:
        above = [row for row in sweep_rows if row["normal_warning_or_higher_rate"] > 0.10]
        pool = above or sweep_rows
        closest_rate = min(row["normal_warning_or_higher_rate"] for row in pool)
        candidates = [
            row for row in pool if row["normal_warning_or_higher_rate"] == closest_rate
        ]
        target_reached = False
        reason = "No threshold-only candidate reaches the 5-10% target; selected the closest available result."
    selected = max(
        candidates,
        key=lambda row: (
            row["ordering_holds"],
            row["e2_still_detected"],
            -abs(row["normal_warning_or_higher_rate"] - 0.075),
            row["e2_r02_detection_rate_above_threshold"] or 0,
            -(row["e2_r02_rank_by_max_anomaly"] or 999),
            row["mean_gap_pre_emergency_minus_normal"],
            -row["normal_critical_rate"],
        ),
    )
    return {
        "selected_threshold": selected["threshold"],
        "target_fpr_reached": target_reached,
        "threshold_only_sufficient": bool(
            target_reached
            and selected["ordering_holds"]
            and selected["e2_still_detected"]
            and selected["acceptable_critical_fpr"]
        ),
        "reason": reason,
        "selected_metrics": selected,
    }


def analyze_normal_false_positive_features(
    rows: list[dict[str, Any]], threshold: float
) -> dict[str, Any]:
    """Rank feature-score contributions in rows at or above a threshold."""

    selected = [
        row
        for row in rows
        if row.get("group") == "normal_validation"
        and float(row.get("anomaly_score", 0.0)) >= threshold
    ]
    values: dict[str, list[float]] = defaultdict(list)
    phases: dict[str, int] = defaultdict(int)
    profiles: dict[str, int] = defaultdict(int)
    for row in selected:
        phases[str(row.get("motion_phase", "unknown"))] += 1
        profiles[str(row.get("profile_used", "unknown"))] += 1
        for feature, value in row.get("feature_scores", {}).items():
            if value is not None:
                values[str(feature)].append(float(value))
    features = [
        {
            "feature": feature,
            "windows": len(scores),
            "mean_feature_score": mean(scores),
            "max_feature_score": max(scores),
        }
        for feature, scores in values.items()
    ]
    features.sort(key=lambda row: (row["mean_feature_score"], row["max_feature_score"]), reverse=True)
    return {
        "threshold": threshold,
        "false_positive_windows": len(selected),
        "top_features": features[:10],
        "all_features": features,
        "motion_phase_counts": dict(sorted(phases.items())),
        "profile_used_counts": dict(sorted(profiles.items())),
    }


def analyze_e2_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank mean E2 R02 feature-score contributions."""

    e2_rows = [row for row in rows if E2_TOKEN in str(row.get("session_id", ""))]
    values: dict[str, list[float]] = defaultdict(list)
    for row in e2_rows:
        for feature, value in row.get("feature_scores", {}).items():
            if value is not None:
                values[str(feature)].append(float(value))
    output = [
        {
            "feature": feature,
            "windows": len(scores),
            "mean_feature_score": mean(scores),
            "max_feature_score": max(scores),
        }
        for feature, scores in values.items()
    ]
    return sorted(output, key=lambda row: (row["mean_feature_score"], row["max_feature_score"]), reverse=True)[:10]


def group_separation_summary(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    """Summarize group anomaly separation at a selected threshold."""

    output = []
    for group in GROUP_ORDER:
        group_rows = [row for row in rows if row.get("group") == group]
        scores = _scores(group_rows)
        output.append(
            {
                "group": group,
                "mean_anomaly": mean(scores) if scores else None,
                "max_anomaly": max(scores) if scores else None,
                "windows": len(group_rows),
                "detection_rate_above_candidate": _rate(group_rows, threshold),
            }
        )
    return output
