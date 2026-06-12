"""CLI and report generation for evaluation-only anomaly calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from servo_diagnostic_model.evaluation.calibration import (
    analyze_e2_features,
    analyze_normal_false_positive_features,
    flatten_diagnostic_results,
    group_separation_summary,
    load_diagnostic_results,
    run_anomaly_threshold_sweep,
    select_calibration_candidate,
)


def _json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def _pct(value: Any) -> str:
    return "n/a" if value is None else f"{float(value) * 100:.3f}%"


def _num(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.3f}"


def _key_rows(sweep: list[dict[str, Any]], current: float, selected: float) -> list[dict[str, Any]]:
    keys = {round(value, 2) for value in (current, .55, .60, .65, .70, .75, .80, selected)}
    return [row for row in sweep if round(row["threshold"], 2) in keys]


def write_calibration_report(
    path: Path,
    sweep: list[dict[str, Any]],
    candidate: dict[str, Any],
    groups: list[dict[str, Any]],
    normal_features: dict[str, Any],
    e2_features: list[dict[str, Any]],
    current_threshold: float,
) -> None:
    selected = candidate["selected_metrics"]
    current = min(sweep, key=lambda row: abs(row["threshold"] - current_threshold))
    sweep_table = [
        "| Threshold | Normal FPR warning+ | Normal critical FPR | Transition detection | Elevated-load detection | Pre-emergency detection | E2 R02 detection | Ordering holds |",
        "| --------: | ------------------: | ------------------: | -------------------: | ----------------------: | ----------------------: | ---------------: | -------------- |",
    ]
    for row in _key_rows(sweep, current_threshold, candidate["selected_threshold"]):
        sweep_table.append(
            f"| {row['threshold']:.2f} | {_pct(row['normal_warning_or_higher_rate'])} | "
            f"{_pct(row['normal_critical_rate'])} | {_pct(row['transition_detection_rate_above_threshold'])} | "
            f"{_pct(row['elevated_load_detection_rate_above_threshold'])} | "
            f"{_pct(row['pre_emergency_proxy_detection_rate_above_threshold'])} | "
            f"{_pct(row['e2_r02_detection_rate_above_threshold'])} | {row['ordering_holds']} |"
        )
    group_table = [
        "| Group | Mean Anomaly | Max Anomaly | Windows | Detection Rate Above Candidate |",
        "| ----- | -----------: | ----------: | ------: | -----------------------------: |",
    ]
    for row in groups:
        group_table.append(
            f"| {row['group']} | {_num(row['mean_anomaly'])} | {_num(row['max_anomaly'])} | "
            f"{row['windows']} | {_pct(row['detection_rate_above_candidate'])} |"
        )
    feature_table = [
        "| Feature | Mean FP Score | Max FP Score | Windows |",
        "| ------- | ------------: | -----------: | ------: |",
    ]
    for row in normal_features["top_features"]:
        feature_table.append(
            f"| {row['feature']} | {_num(row['mean_feature_score'])} | "
            f"{_num(row['max_feature_score'])} | {row['windows']} |"
        )
    threshold_sufficient = candidate["threshold_only_sufficient"]
    recommendation = (
        "A. Threshold-only calibration is sufficient for this holdout dataset, but must be validated on new data."
        if threshold_sufficient
        else "B. Threshold-only calibration helps, but feature-weight and classifier-mapping analysis is still needed."
    )
    strategy_threshold = "Primary candidate" if candidate["target_fpr_reached"] else "Useful but insufficient"
    top_names = ", ".join(row["feature"] for row in normal_features["top_features"][:5])
    content = f"""# Calibration Report

## 1. Purpose

This report is evaluation-only. It simulates anomaly-warning thresholds and does not modify model behavior, formulas, profiles, or production configuration.

## 2. Current holdout validation problem

- Normal-validation windows: {current['normal_windows']}
- Mean anomaly: {_num(current['normal_mean_anomaly'])}
- Maximum anomaly: {_num(current['normal_max_anomaly'])}
- Warning-or-higher false-positive rate: {_pct(current['normal_warning_or_higher_rate'])}
- Critical false-positive rate: {_pct(current['normal_critical_rate'])}
- Current group ordering holds: {current['ordering_holds']}

## 3. Threshold sweep methodology

Inputs were the existing normal-holdout and test diagnostic JSON files. Thresholds from {sweep[0]['threshold']:.2f} to {sweep[-1]['threshold']:.2f} were simulated without rerunning diagnosis or invoking the production classifier. This is analysis, not automatic calibration.

## 4. Threshold sweep summary

{chr(10).join(sweep_table)}

## 5. Candidate threshold

- Selected candidate: **{candidate['selected_threshold']:.2f}**
- Normal warning false-positive rate: {_pct(selected['normal_warning_or_higher_rate'])}
- Reaches 5-10% target: {candidate['target_fpr_reached']}
- E2 R02 remains detected: {selected['e2_still_detected']}
- Group ordering holds: {selected['ordering_holds']}

{candidate['reason']}

## 6. Group separation at candidate threshold

{chr(10).join(group_table)}

## 7. E2 R02 analysis

- Maximum anomaly: {_num(selected['e2_r02_max_anomaly'])}
- Mean anomaly: {_num(selected['e2_r02_mean_anomaly'])}
- Detection rate above candidate: {_pct(selected['e2_r02_detection_rate_above_threshold'])}
- Rank by session maximum: {selected['e2_r02_rank_by_max_anomaly']}
- Rank by session mean: {selected['e2_r02_rank_by_mean_anomaly']}

E2 R02 remains one of the strongest anomaly cases. It remains a pre-emergency proxy, not a confirmed fault.

## 8. Normal false-positive feature analysis

{chr(10).join(feature_table)}

Top contributors are {top_names or 'not available'}. Position and voltage-level features dominate the remaining normal false positives; current and torque features do not dominate them. All selected false-positive windows used phase-specific profiles, so the result does not indicate global-profile fallback, although motion-phase coverage still requires validation. Data-quality and physical risks are not the cause. The concentration of saturated feature scores means feature weighting should still be reviewed after threshold validation.

## 9. Calibration strategy comparison

| Strategy | Recommendation | Reason |
| -------- | -------------- | ------ |
| Change thresholds.json | {strategy_threshold} | Test the selected warning threshold first because separation and ordering remain measurable. |
| Change statistical anomaly weight in weights.json | Defer | Health Score remains high; changing this weight does not directly solve anomaly-driven warning classification. |
| Change feature weights inside anomaly score | Investigate next | Review the concentrated false-positive features before any tuning. |
| Change state-classifier mapping | Investigate if threshold validation fails | Warnings are primarily anomaly-threshold driven while Health Score remains high. |

Do not change physical limits; physical risks are low. Do not revisit temperature slope gating unless thermal false positives reappear.

## 10. Recommended next step

{recommendation} Do not apply the recommendation automatically.

## 11. Article wording

Holdout validation on a same-campaign normal subset preserved the mean Anomaly Score ordering from normal validation through transition and elevated-load operation to the pre-emergency proxy group. The initial warning threshold produced a high normal false-positive rate, so an evaluation-only calibration sweep was performed. E2 R02 remained a strong pre-emergency proxy case; these results do not establish proven fault prediction.

## 12. Limitations

- Same-campaign holdout, not independent validation.
- Limited normal-validation diversity.
- E2 is a proxy rather than a confirmed fault.
- Thresholds require validation on new data before production use.
- Feature weights should not be tuned aggressively on this small dataset.
"""
    path.write_text(content, encoding="utf-8")


def run_lab_calibration(
    normal_results_path: str | Path,
    test_results_path: str | Path,
    thresholds_path: str | Path,
    weights_path: str | Path,
    output_dir: str | Path,
    threshold_start: float = 0.45,
    threshold_stop: float = 0.90,
    threshold_step: float = 0.01,
    target_fpr_min: float = 0.05,
    target_fpr_max: float = 0.10,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    normal = flatten_diagnostic_results(load_diagnostic_results(normal_results_path))
    test = flatten_diagnostic_results(load_diagnostic_results(test_results_path))
    rows = normal + test
    threshold_values = json.loads(Path(thresholds_path).read_text(encoding="utf-8"))
    json.loads(Path(weights_path).read_text(encoding="utf-8"))
    count = round((threshold_stop - threshold_start) / threshold_step)
    values = [round(threshold_start + index * threshold_step, 10) for index in range(count + 1)]
    sweep = run_anomaly_threshold_sweep(rows, values, target_fpr_min, target_fpr_max)
    candidate = select_calibration_candidate(sweep)
    selected_threshold = candidate["selected_threshold"]
    normal_features = analyze_normal_false_positive_features(rows, selected_threshold)
    e2_features = analyze_e2_features(rows)
    groups = group_separation_summary(rows, selected_threshold)
    pd.DataFrame(sweep).to_csv(output / "anomaly_threshold_sweep.csv", index=False)
    _json(output / "anomaly_threshold_sweep.json", sweep)
    pd.DataFrame(groups).to_csv(output / "group_separation_summary.csv", index=False)
    pd.DataFrame(normal_features["all_features"]).to_csv(output / "normal_false_positive_features.csv", index=False)
    pd.DataFrame(e2_features).to_csv(output / "e2_r02_top_anomaly_features.csv", index=False)
    recommendation = {
        **candidate,
        "current_anomaly_warning": threshold_values.get("anomaly_warning"),
        "normal_false_positive_feature_analysis": normal_features,
        "e2_r02_top_anomaly_features": e2_features,
        "production_changes_applied": False,
    }
    _json(output / "calibration_recommendation.json", recommendation)
    write_calibration_report(
        output / "calibration_report.md", sweep, candidate, groups, normal_features,
        e2_features, float(threshold_values.get("anomaly_warning", 0.5)),
    )
    return recommendation


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run evaluation-only anomaly threshold calibration.")
    parser.add_argument("--normal-results", required=True)
    parser.add_argument("--test-results", required=True)
    parser.add_argument("--thresholds", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--threshold-start", type=float, default=0.45)
    parser.add_argument("--threshold-stop", type=float, default=0.90)
    parser.add_argument("--threshold-step", type=float, default=0.01)
    parser.add_argument("--target-fpr-min", type=float, default=0.05)
    parser.add_argument("--target-fpr-max", type=float, default=0.10)
    args = parser.parse_args()
    result = run_lab_calibration(
        args.normal_results, args.test_results, args.thresholds, args.weights,
        args.output_dir, args.threshold_start, args.threshold_stop, args.threshold_step,
        args.target_fpr_min, args.target_fpr_max,
    )
    print(f"Calibration analysis complete: selected threshold {result['selected_threshold']:.2f}.")


if __name__ == "__main__":
    _main()
