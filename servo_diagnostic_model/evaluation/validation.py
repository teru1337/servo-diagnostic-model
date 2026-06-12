"""Reusable holdout-validation utilities for laboratory diagnostics."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import random
import re
from typing import Any, Iterable

import pandas as pd

from servo_diagnostic_model.api.diagnostic_service import diagnose_csv, load_json_config
from servo_diagnostic_model.api.profile_service import fit_normal_profile_from_manifest


PHYSICAL_RISK_KEYS = ("current", "torque", "velocity", "voltage", "temperature")
WARNING_OR_HIGHER_STATES = {"warning", "critical"}


def _read_manifest(path: str | Path) -> pd.DataFrame:
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"CSV manifest not found: {manifest_path}")
    manifest = pd.read_csv(manifest_path, dtype=str, keep_default_na=False)
    if "path" not in manifest.columns:
        raise ValueError(f"CSV manifest must contain a 'path' column: {manifest_path}")
    if manifest.empty or not manifest["path"].str.strip().any():
        raise ValueError(f"CSV manifest contains no CSV paths: {manifest_path}")
    return manifest


def _repeat(value: Any) -> str | None:
    match = re.search(r"(?:^|_)R(\d{2})(?:_|$)", str(value), re.IGNORECASE)
    return match.group(1) if match else None


def _seeded_split(
    manifest: pd.DataFrame, validation_fraction: float, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1.")
    indices = list(manifest.index)
    random.Random(seed).shuffle(indices)
    validation_count = max(1, min(len(indices) - 1, round(len(indices) * validation_fraction)))
    validation_indices = set(indices[:validation_count])
    validation = manifest.loc[manifest.index.isin(validation_indices)]
    train = manifest.loc[~manifest.index.isin(validation_indices)]
    return train, validation


def create_normal_holdout_manifests(
    normal_manifest_path: str | Path,
    train_manifest_path: str | Path,
    validation_manifest_path: str | Path,
    strategy: str = "by_repeat",
    validation_fraction: float = 0.35,
    seed: int = 42,
) -> dict[str, Any]:
    """Create deterministic, non-overlapping normal train and holdout manifests."""

    manifest = _read_manifest(normal_manifest_path)
    strategy_used = strategy
    if strategy == "by_repeat":
        repeat_source = manifest.get("session_id", manifest["path"])
        repeats = repeat_source.map(_repeat)
        if {"01", "02"} <= set(repeats.dropna()):
            train = manifest.loc[repeats != "02"]
            validation = manifest.loc[repeats == "02"]
        else:
            strategy_used = "seeded"
            train, validation = _seeded_split(manifest, validation_fraction, seed)
    elif strategy == "seeded":
        train, validation = _seeded_split(manifest, validation_fraction, seed)
    else:
        raise ValueError("strategy must be 'by_repeat' or 'seeded'.")

    train_paths = set(train["path"].str.strip())
    validation_paths = set(validation["path"].str.strip())
    overlap = train_paths & validation_paths
    if overlap:
        raise ValueError(f"Train and validation manifests overlap: {sorted(overlap)}")
    if train.empty or validation.empty:
        raise ValueError("Holdout split must create non-empty train and validation subsets.")

    train_path = Path(train_manifest_path)
    validation_path = Path(validation_manifest_path)
    train_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    train.to_csv(train_path, index=False)
    validation.to_csv(validation_path, index=False)
    return {
        "source_manifest": str(normal_manifest_path),
        "train_manifest": str(train_path),
        "validation_manifest": str(validation_path),
        "strategy_requested": strategy,
        "strategy_used": strategy_used,
        "validation_fraction": validation_fraction,
        "seed": seed,
        "source_files": len(manifest),
        "train_files": len(train),
        "validation_files": len(validation),
        "overlap_count": 0,
        "train_paths": sorted(train_paths),
        "validation_paths": sorted(validation_paths),
    }


def fit_validation_normal_profile(
    train_manifest_path: str | Path,
    output_profile_path: str | Path,
    thresholds_path: str | Path,
    min_count: int = 5,
) -> dict[str, Any]:
    """Fit a separate validation profile using only the holdout-training manifest."""

    thresholds = load_json_config(str(thresholds_path))
    profile = fit_normal_profile_from_manifest(
        train_manifest_path, output_profile_path, thresholds, min_count=min_count
    )
    profile["meta"]["validation_role"] = "holdout_train"
    profile["meta"]["source_manifest"] = str(train_manifest_path)
    Path(output_profile_path).write_text(
        json.dumps(profile, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return profile


def diagnose_manifest(
    manifest_path: str | Path,
    normal_profile_path: str | Path,
    limits_path: str | Path,
    weights_path: str | Path,
    thresholds_path: str | Path,
) -> list[dict[str, Any]]:
    """Diagnose each manifest file and retain its manifest metadata."""

    manifest = _read_manifest(manifest_path)
    results: list[dict[str, Any]] = []
    for row in manifest.to_dict("records"):
        windows = diagnose_csv(
            str(row["path"]),
            str(limits_path),
            str(weights_path),
            str(thresholds_path),
            str(normal_profile_path),
        )
        results.append({"manifest": row, "windows": windows})
    json.dumps(results, allow_nan=False)
    return results


def _windows(results: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for item in results:
        if "windows" in item:
            yield from item.get("windows", [])
        else:
            yield item


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _threshold_value(thresholds: dict[str, Any] | None) -> float | None:
    if not thresholds:
        return None
    for key in ("anomaly_warning", "anomaly_critical", "anomaly_observation"):
        if key in thresholds:
            return float(thresholds[key])
    return None


def compute_validation_metrics(
    results: list[dict[str, Any]],
    expected_group: str | None = None,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate holdout false-positive and diagnostic separation metrics."""

    windows = list(_windows(results))
    health = [float(row["health_score"]) for row in windows if row.get("health_score") is not None]
    anomaly = [float(row["anomaly_score"]) for row in windows if row.get("anomaly_score") is not None]
    statistical = [
        float(row["risks"]["statistical_anomaly"])
        for row in windows
        if row.get("risks", {}).get("statistical_anomaly") is not None
    ]
    physical = [
        max(
            float(row["risks"][key])
            for key in PHYSICAL_RISK_KEYS
            if row.get("risks", {}).get(key) is not None
        )
        for row in windows
        if any(row.get("risks", {}).get(key) is not None for key in PHYSICAL_RISK_KEYS)
    ]
    states = Counter(str(row.get("state", "unknown")) for row in windows)
    risk_levels = Counter(str(row.get("risk_level", "unknown")) for row in windows)
    warning_or_higher = sum(row.get("state") in WARNING_OR_HIGHER_STATES for row in windows)
    critical = sum(row.get("state") == "critical" for row in windows)
    threshold = _threshold_value(thresholds)
    threshold_exceedances = (
        sum(value >= threshold for value in anomaly) if threshold is not None else None
    )
    count = len(windows)
    return {
        "expected_group": expected_group,
        "files": len(results),
        "windows": count,
        "mean_health_score": _mean(health),
        "min_health_score": min(health) if health else None,
        "mean_anomaly_score": _mean(anomaly),
        "max_anomaly_score": max(anomaly) if anomaly else None,
        "mean_statistical_anomaly_risk": _mean(statistical),
        "max_statistical_anomaly_risk": max(statistical) if statistical else None,
        "mean_max_physical_risk": _mean(physical),
        "max_max_physical_risk": max(physical) if physical else None,
        "state_counts": dict(sorted(states.items())),
        "risk_level_counts": dict(sorted(risk_levels.items())),
        "false_positive_windows_warning_or_higher": warning_or_higher,
        "false_positive_rate_warning_or_higher": warning_or_higher / count if count else None,
        "false_positive_windows_critical": critical,
        "false_positive_rate_critical": critical / count if count else None,
        "anomaly_threshold": threshold,
        "anomaly_threshold_exceedance_rate": (
            threshold_exceedances / len(anomaly)
            if threshold_exceedances is not None and anomaly
            else None
        ),
        "data_quality_nonzero_windows": sum(
            float(row.get("risks", {}).get("data_quality", 0.0)) > 0 for row in windows
        ),
    }


def summarize_files(
    results: list[dict[str, Any]], thresholds: dict[str, Any]
) -> pd.DataFrame:
    """Create one summary row per diagnosed manifest file."""

    rows = []
    for item in results:
        manifest = item.get("manifest", {})
        metrics = compute_validation_metrics([item], manifest.get("risk_label"), thresholds)
        rows.append({**manifest, **metrics})
    return pd.DataFrame(rows)


def group_comparison(
    normal_results: list[dict[str, Any]],
    test_results: list[dict[str, Any]],
    thresholds: dict[str, Any],
) -> pd.DataFrame:
    """Build the requested holdout-normal and test-group comparison table."""

    rows = [compute_validation_metrics(normal_results, "normal_validation", thresholds)]
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in test_results:
        label = str(item.get("manifest", {}).get("risk_label", "unknown"))
        groups.setdefault(label, []).append(item)
    for label in ("transition", "elevated_load", "pre_emergency_proxy"):
        rows.append(compute_validation_metrics(groups.get(label, []), label, thresholds))
    return pd.DataFrame(rows)
