"""CLI orchestration for laboratory normal holdout validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from servo_diagnostic_model.api.diagnostic_service import load_json_config
from servo_diagnostic_model.evaluation.validation import (
    compute_validation_metrics,
    create_normal_holdout_manifests,
    diagnose_manifest,
    fit_validation_normal_profile,
    group_comparison,
    summarize_files,
)


GROUP_ORDER = ("normal_validation", "transition", "elevated_load", "pre_emergency_proxy")


def _number(value: Any, digits: int = 3) -> str:
    return "not available" if value is None or pd.isna(value) else f"{float(value):.{digits}f}"


def _percent(value: Any) -> str:
    return "not available" if value is None else f"{100 * float(value):.3f}%"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


def _e2_check(results: list[dict[str, Any]]) -> dict[str, Any]:
    cases = []
    for item in results:
        manifest = item.get("manifest", {})
        scores = [
            float(window["anomaly_score"])
            for window in item.get("windows", [])
            if window.get("anomaly_score") is not None
        ]
        if scores:
            cases.append(
                {
                    "session_id": manifest.get("session_id", manifest.get("path")),
                    "max_anomaly_score": max(scores),
                }
            )
    cases.sort(key=lambda row: row["max_anomaly_score"], reverse=True)
    e2_rank = next(
        (
            index + 1
            for index, row in enumerate(cases)
            if "E2_LOAD_MED_INERTIA_R02" in str(row["session_id"])
        ),
        None,
    )
    return {"rank": e2_rank, "strongest_cases": cases[:5]}


def _ordering_check(comparison: pd.DataFrame) -> dict[str, Any]:
    values = dict(zip(comparison["expected_group"], comparison["mean_anomaly_score"]))
    available = all(values.get(group) is not None for group in GROUP_ORDER)
    holds = available and all(
        float(values[left]) < float(values[right])
        for left, right in zip(GROUP_ORDER, GROUP_ORDER[1:])
    )
    return {"holds": holds, "mean_anomaly_scores": values}


def write_validation_report(
    output_path: str | Path,
    split: dict[str, Any],
    profile: dict[str, Any],
    normal_metrics: dict[str, Any],
    comparison: pd.DataFrame,
    ordering: dict[str, Any],
    e2: dict[str, Any],
) -> Path:
    """Write the publication-facing holdout-validation report."""

    test_rows = comparison.loc[comparison["expected_group"] != "normal_validation"]
    group_table = [
        "| Group | Files | Windows | Mean Anomaly Score | Max Anomaly Score | Mean Health Score | Min Health Score | Mean Max Physical Risk |",
        "| ----- | ----: | ------: | -----------------: | ----------------: | ----------------: | ---------------: | ---------------------: |",
    ]
    for _, row in test_rows.iterrows():
        group_table.append(
            f"| {row['expected_group']} | {int(row['files'])} | {int(row['windows'])} | "
            f"{_number(row['mean_anomaly_score'])} | {_number(row['max_anomaly_score'])} | "
            f"{_number(row['mean_health_score'])} | {_number(row['min_health_score'])} | "
            f"{_number(row['mean_max_physical_risk'])} |"
        )
    metric_names = [
        "files", "windows", "mean_health_score", "min_health_score",
        "mean_anomaly_score", "max_anomaly_score", "mean_statistical_anomaly_risk",
        "max_statistical_anomaly_risk", "mean_max_physical_risk", "max_max_physical_risk",
        "false_positive_windows_warning_or_higher", "false_positive_rate_warning_or_higher",
        "false_positive_windows_critical", "false_positive_rate_critical",
        "anomaly_threshold_exceedance_rate", "data_quality_nonzero_windows",
    ]
    normal_table = ["| Metric | Value |", "| ------ | ----: |"]
    for name in metric_names:
        value = normal_metrics.get(name)
        formatted = _percent(value) if "rate" in name else _number(value)
        normal_table.append(f"| {name} | {formatted} |")
    ordering_text = (
        "The desired mean-anomaly ordering holds for this holdout split."
        if ordering["holds"]
        else "The desired mean-anomaly ordering is imperfect for this holdout split and should be reported cautiously."
    )
    e2_text = (
        f"E2 R02 ranks {e2['rank']} among diagnosed test sessions by maximum Anomaly Score."
        if e2["rank"] is not None
        else "E2 R02 was not found in the diagnosed test manifest."
    )
    meta = profile.get("meta", {})
    content = f"""# Normal Holdout Validation Report

## 1. Purpose

This workflow validates a profile fitted on a held-out split of the same laboratory campaign. It is **holdout normal validation**, not truly independent validation.

## 2. Data split

- Source manifest: `{split['source_manifest']}`
- Train manifest: `{split['train_manifest']}`
- Validation manifest: `{split['validation_manifest']}`
- Train files: {split['train_files']}
- Validation files: {split['validation_files']}
- Split strategy: `{split['strategy_used']}`
- Train/validation path overlap: none

## 3. Validation profile

- Output profile: `artifacts/validation/normal_profile_holdout_train.json`
- Training feature rows/windows: {meta.get('normal_row_count', meta.get('window_count', 'not available'))}
- Global feature count: {len(profile.get('global', {}))}
- Motion-phase profiles: {', '.join(sorted(profile.get('by_motion_phase', {}))) or 'none'}

## 4. Normal holdout metrics

{chr(10).join(normal_table)}

State counts: `{json.dumps(normal_metrics.get('state_counts', {}), sort_keys=True)}`  
Risk-level counts: `{json.dumps(normal_metrics.get('risk_level_counts', {}), sort_keys=True)}`

## 5. Test group metrics with holdout-trained profile

{chr(10).join(group_table)}

## 6. Group ordering check

{ordering_text}

Observed mean anomaly scores: `{json.dumps(ordering['mean_anomaly_scores'], sort_keys=True)}`

## 7. E2 case check

{e2_text} It remains a pre-emergency proxy rather than a confirmed fault.

## 8. Interpretation for article

Describe this result as **holdout validation**, not independent validation, because both subsets come from the same laboratory campaign. Do not claim proven fault prediction. E2 remains a pre-emergency proxy.

## 9. Limitations

- This is not a truly independent data collection.
- Thermal diversity remains limited.
- E2 is a proxy, not a confirmed fault.
- False positives may still require threshold or feature-weight calibration after review.
- Profile coverage may depend on the motion-phase distribution.

## 10. Recommended next actions

1. Collect a new independent normal session if possible.
2. Use the new normal session as external validation.
3. Compare holdout and external-validation metrics.
4. Tune thresholds or feature weights only after validation results are reviewed.
5. Keep physical limits physically meaningful.
"""
    path = Path(output_path)
    path.write_text(content, encoding="utf-8")
    return path


def run_lab_validation(
    normal_manifest: str | Path,
    test_manifest: str | Path,
    limits: str | Path,
    weights: str | Path,
    thresholds: str | Path,
    output_dir: str | Path,
    strategy: str = "by_repeat",
    validation_fraction: float = 0.35,
    seed: int = 42,
) -> dict[str, Any]:
    """Run the complete holdout workflow and write all required artifacts."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    normal_parent = Path(normal_manifest).parent
    train_manifest = normal_parent / "normal_train_files.csv"
    validation_manifest = normal_parent / "normal_validation_files.csv"
    profile_path = output / "normal_profile_holdout_train.json"
    split = create_normal_holdout_manifests(
        normal_manifest, train_manifest, validation_manifest, strategy, validation_fraction, seed
    )
    profile = fit_validation_normal_profile(train_manifest, profile_path, thresholds)
    threshold_values = load_json_config(str(thresholds))
    normal_results = diagnose_manifest(validation_manifest, profile_path, limits, weights, thresholds)
    test_results = diagnose_manifest(test_manifest, profile_path, limits, weights, thresholds)
    _write_json(output / "normal_holdout_diagnostic_results.json", normal_results)
    _write_json(output / "test_with_holdout_profile_results.json", test_results)
    summarize_files(normal_results, threshold_values).to_csv(
        output / "normal_holdout_summary.csv", index=False
    )
    summarize_files(test_results, threshold_values).to_csv(
        output / "test_with_holdout_profile_summary.csv", index=False
    )
    normal_metrics = compute_validation_metrics(
        normal_results, "normal_validation", threshold_values
    )
    comparison = group_comparison(normal_results, test_results, threshold_values)
    ordering = _ordering_check(comparison)
    e2 = _e2_check(test_results)
    write_validation_report(
        output / "holdout_validation_report.md",
        split, profile, normal_metrics, comparison, ordering, e2,
    )
    return {
        "split": split,
        "profile": profile,
        "normal_metrics": normal_metrics,
        "group_comparison": comparison.to_dict("records"),
        "ordering": ordering,
        "e2": e2,
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run laboratory normal holdout validation.")
    parser.add_argument("--normal-manifest", required=True)
    parser.add_argument("--test-manifest", required=True)
    parser.add_argument("--limits", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--thresholds", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--strategy", choices=("by_repeat", "seeded"), default="by_repeat")
    parser.add_argument("--validation-fraction", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = run_lab_validation(
        args.normal_manifest, args.test_manifest, args.limits, args.weights,
        args.thresholds, args.output_dir, args.strategy, args.validation_fraction, args.seed,
    )
    print(
        f"Holdout validation complete: {result['split']['train_files']} train files, "
        f"{result['split']['validation_files']} validation files."
    )


if __name__ == "__main__":
    _main()
