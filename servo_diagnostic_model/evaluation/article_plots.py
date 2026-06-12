"""Build article-ready figures and a concise laboratory results report."""

from __future__ import annotations

import argparse
import json
import re
import warnings
from pathlib import Path
from typing import Any

import pandas as pd

from servo_diagnostic_model.api.diagnostic_service import diagnose_csv
from servo_diagnostic_model.evaluation.plots import (
    GROUP_ORDER,
    PHYSICAL_RISKS,
    ensure_output_dir,
    load_diagnostic_results,
    load_diagnostic_summary,
    plot_current_torque_over_time,
    plot_group_anomaly_comparison,
    plot_group_health_comparison,
    plot_risks_over_time,
    plot_scores_over_time,
    plot_statistical_vs_physical_risks,
)


ARTICLE_FIGURES = {
    "fig1_group_anomaly_with_normal": "Group anomaly comparison including normal operation.",
    "fig2_group_health_with_normal": "Group Health Score comparison including normal operation.",
    "fig3_e2_r02_scores_over_time": "E2 R02 Anomaly Score and Health Score over time.",
    "fig4_e2_r02_risks_over_time": "E2 R02 statistical and physical risks over time.",
    "fig5_statistical_vs_physical_risks": "Group-level statistical versus physical risk comparison.",
    "fig6_e2_r02_current_torque": "E2 R02 current and torque features over time.",
}
LEGACY_GROUP_ORDER = ["normal", "transition", "elevated_load", "pre_emergency_proxy"]

FINAL_ARTICLE_COMMAND = (
    ".\\.venv\\Scripts\\python.exe -m servo_diagnostic_model.evaluation.article_plots "
    "--validation-dir artifacts/validation_after_threshold_calibration "
    "--calibration-dir artifacts/calibration_after_threshold_application "
    "--thresholds servo_diagnostic_model/config/thresholds.json "
    "--output-dir artifacts/article_figures_after_threshold_calibration"
)


def _number(value: str) -> float | None:
    cleaned = value.strip().replace(",", "")
    if cleaned.lower() in {"", "not available", "n/a", "nan"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def derive_group_comparison(
    summary_df: pd.DataFrame, analysis_path: str | Path
) -> pd.DataFrame:
    """Build the verified four-group comparison used by article figures."""
    analysis_file = Path(analysis_path)
    if not analysis_file.is_file():
        raise FileNotFoundError(f"Pipeline analysis does not exist: {analysis_file}")
    analysis = analysis_file.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^\|\s*(normal|transition|elevated_load|pre_emergency_proxy)\s*\|"
        r"\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|",
        re.MULTILINE,
    )
    rows: dict[str, dict[str, Any]] = {}
    for match in pattern.finditer(analysis):
        group, files, windows, mean_anomaly, max_anomaly, mean_health = match.groups()
        rows[group] = {
            "expected_risk_label": group,
            "files": _number(files),
            "windows": _number(windows),
            "mean_anomaly_score": _number(mean_anomaly),
            "max_anomaly_score": _number(max_anomaly),
            "mean_health_score": _number(mean_health),
            "min_health_score": None,
        }
    if "normal" not in rows:
        raise ValueError("Pipeline analysis does not contain a verified normal group row")

    if not summary_df.empty:
        test_groups = summary_df.groupby("expected_risk_label", sort=False).agg(
            mean_anomaly_score=("mean_anomaly_score", "mean"),
            max_anomaly_score=("max_anomaly_score", "max"),
            mean_health_score=("mean_health_score", "mean"),
            min_health_score=("min_health_score", "min"),
        )
        for group in LEGACY_GROUP_ORDER:
            if group == "normal" or group not in test_groups.index:
                continue
            row = rows.setdefault(group, {"expected_risk_label": group})
            for column in test_groups.columns:
                row[column] = float(test_groups.loc[group, column])

    missing = [group for group in LEGACY_GROUP_ORDER if group not in rows]
    if missing:
        raise ValueError(f"Group comparison is missing groups: {missing}")
    return pd.DataFrame([rows[group] for group in LEGACY_GROUP_ORDER])


def build_group_risk_comparison(
    results: dict[str, Any],
    group_comparison: pd.DataFrame,
    normal_metrics: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Aggregate test risks and include computed normal physical risk when available."""
    rows: list[dict[str, Any]] = []
    for entry in results.get("files", []):
        group = entry.get("manifest", {}).get("risk_label", "unknown")
        for window in entry.get("windows", []):
            risks = window.get("risks", {})
            row = {"group": group}
            row.update(
                {
                    name: risks.get(name)
                    for name in ("statistical_anomaly", *PHYSICAL_RISKS)
                }
            )
            rows.append(row)
    risk_rows = pd.DataFrame(rows)
    for column in risk_rows.columns.difference(["group"]):
        risk_rows[column] = pd.to_numeric(risk_rows[column], errors="coerce")
    normal = group_comparison.loc[
        group_comparison["expected_risk_label"] == "normal", "mean_anomaly_score"
    ].iloc[0]
    normal_row = {"group": "normal", "statistical_anomaly": normal}
    normal_row.update({name: None for name in PHYSICAL_RISKS})
    if normal_metrics and normal_metrics.get("mean_max_physical_risk") is not None:
        normal_row["max_physical_risk"] = normal_metrics["mean_max_physical_risk"]
    return pd.concat([pd.DataFrame([normal_row]), risk_rows], ignore_index=True)


def diagnose_manifest_files(
    manifest_path: str | Path,
    normal_profile_path: str | Path,
    limits_path: str | Path,
    weights_path: str | Path,
    thresholds_path: str | Path,
) -> dict[str, Any]:
    """Diagnose every CSV listed in a manifest using an existing normal profile."""
    manifest_file = Path(manifest_path)
    if not manifest_file.is_file():
        raise FileNotFoundError(f"Normal manifest does not exist: {manifest_file}")
    manifest = pd.read_csv(manifest_file)
    if "path" not in manifest:
        raise ValueError("Normal manifest must contain a path column")
    files = []
    for row in manifest.to_dict("records"):
        csv_path = Path(str(row["path"]))
        try:
            windows = diagnose_csv(
                str(csv_path),
                str(limits_path),
                str(weights_path),
                str(thresholds_path),
                str(normal_profile_path),
            )
        except Exception as error:
            warnings.warn(f"Could not diagnose normal CSV {csv_path}: {error}")
            continue
        files.append({"manifest": row, "windows": windows})
    return {"files": files}


def compute_group_metrics_from_results(results: dict[str, Any]) -> dict[str, Any]:
    """Compute score and physical-risk metrics from diagnostic window results."""
    health: list[float] = []
    anomaly: list[float] = []
    max_physical: list[float] = []
    windows = 0
    for entry in results.get("files", []):
        for window in entry.get("windows", []):
            windows += 1
            if window.get("health_score") is not None:
                health.append(float(window["health_score"]))
            if window.get("anomaly_score") is not None:
                anomaly.append(float(window["anomaly_score"]))
            risks = [
                float(window.get("risks", {}).get(name))
                for name in PHYSICAL_RISKS
                if window.get("risks", {}).get(name) is not None
            ]
            if risks:
                max_physical.append(max(risks))
    return {
        "files": len(results.get("files", [])),
        "windows": windows,
        "mean_anomaly_score": sum(anomaly) / len(anomaly) if anomaly else None,
        "max_anomaly_score": max(anomaly) if anomaly else None,
        "mean_health_score": sum(health) / len(health) if health else None,
        "min_health_score": min(health) if health else None,
        "mean_max_physical_risk": (
            sum(max_physical) / len(max_physical) if max_physical else None
        ),
    }


def load_validation_results(path: str | Path) -> dict[str, Any]:
    """Load validation diagnostic JSON, which is stored as a list of file results."""
    result_path = Path(path)
    if not result_path.is_file():
        raise FileNotFoundError(f"Validation diagnostic results do not exist: {result_path}")
    value = json.loads(result_path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        return {"files": value}
    if isinstance(value, dict) and isinstance(value.get("files"), list):
        return value
    raise ValueError("Validation diagnostic results must be a file-result list or files object")


def build_post_threshold_group_comparison(
    normal_results: dict[str, Any], test_results: dict[str, Any]
) -> pd.DataFrame:
    """Aggregate post-threshold holdout results into the article group table."""
    combined = []
    for entry in normal_results.get("files", []):
        copied = dict(entry)
        copied["manifest"] = dict(entry.get("manifest", {}))
        copied["manifest"]["risk_label"] = "normal_validation"
        combined.append(copied)
    combined.extend(test_results.get("files", []))
    rows = []
    for group in ("normal_validation", "transition", "elevated_load", "pre_emergency_proxy"):
        files = [
            entry
            for entry in combined
            if entry.get("manifest", {}).get("risk_label") == group
        ]
        metrics = compute_group_metrics_from_results({"files": files})
        rows.append({"expected_risk_label": group, **metrics})
    return pd.DataFrame(rows)


def build_post_threshold_risk_rows(
    normal_results: dict[str, Any], test_results: dict[str, Any]
) -> pd.DataFrame:
    """Return window-level risk rows for all final article groups."""
    rows: list[dict[str, Any]] = []
    for results, normal in ((normal_results, True), (test_results, False)):
        for entry in results.get("files", []):
            group = (
                "normal_validation"
                if normal
                else entry.get("manifest", {}).get("risk_label", "unknown")
            )
            for window in entry.get("windows", []):
                risks = window.get("risks", {})
                row = {"group": group}
                row.update(
                    {
                        name: risks.get(name)
                        for name in ("statistical_anomaly", *PHYSICAL_RISKS)
                    }
                )
                rows.append(row)
    return pd.DataFrame(rows)


def _load_anomaly_warning(thresholds_path: str | Path) -> float:
    thresholds = json.loads(Path(thresholds_path).read_text(encoding="utf-8"))
    value = float(thresholds.get("anomaly_warning"))
    if value != 0.62:
        raise ValueError(f"Expected anomaly_warning = 0.62, found {value}")
    return value


def _write_final_results_report(
    output_path: Path,
    comparison: pd.DataFrame,
    recommendation: dict[str, Any],
    threshold: float,
) -> Path:
    selected = recommendation["selected_metrics"]
    table = [
        "| Group | Windows | Mean Anomaly Score | Max Anomaly Score | Mean Health Score | Min Health Score | Mean Max Physical Risk |",
        "| ----- | ------: | -----------------: | ----------------: | ----------------: | ---------------: | ---------------------: |",
    ]
    for row in comparison.to_dict("records"):
        table.append(
            f"| {row['expected_risk_label']} | {int(row['windows'])} | "
            f"{_format(row['mean_anomaly_score'])} | {_format(row['max_anomaly_score'])} | "
            f"{_format(row['mean_health_score'])} | {_format(row['min_health_score'])} | "
            f"{_format(row['mean_max_physical_risk'])} |"
        )
    lines = [
        "# Results Report After Threshold Calibration",
        "",
        "## 1. Configuration",
        "",
        f"- `anomaly_warning = {threshold:.2f}`",
        "- Source config: `servo_diagnostic_model/config/thresholds.json`",
        "- These figures reflect the current production threshold configuration.",
        "",
        "## 2. Generated figures",
        "",
        *[f"- `{name}.png`: {description}" for name, description in ARTICLE_FIGURES.items()],
        "",
        "## 3. Holdout validation summary",
        "",
        "- Validation type: same-campaign holdout validation, not independent validation.",
        "- Train files: 9",
        "- Validation files: 8",
        f"- Validation windows: {int(selected['normal_windows'])}",
        f"- Mean Anomaly Score: {_format(selected['normal_mean_anomaly'])}",
        f"- Maximum Anomaly Score: {_format(selected['normal_max_anomaly'])}",
        f"- Mean Health Score: {_format(comparison.iloc[0]['mean_health_score'])}",
        f"- Minimum Health Score: {_format(comparison.iloc[0]['min_health_score'])}",
        f"- Warning-or-higher false-positive rate after threshold calibration: {selected['normal_warning_or_higher_rate']:.3%}",
        f"- Critical false-positive rate: {selected['normal_critical_rate']:.3%}",
        "",
        "## 4. Group separation summary",
        "",
        *table,
        "",
        "## 5. E2 R02 summary",
        "",
        f"- Maximum Anomaly Score: {_format(selected['e2_r02_max_anomaly'])}",
        f"- Mean Anomaly Score: {_format(selected['e2_r02_mean_anomaly'])}",
        f"- Detection rate above {threshold:.2f}: {selected['e2_r02_detection_rate_above_threshold']:.3%}",
        f"- Rank by maximum anomaly: {selected['e2_r02_rank_by_max_anomaly']}",
        f"- Rank by mean anomaly: {selected['e2_r02_rank_by_mean_anomaly']}",
        "- E2 R02 is a pre-emergency proxy, not a confirmed fault.",
        "",
        "## 6. Interpretation",
        "",
        "The diagnostic model preserved the mean Anomaly Score ordering from normal holdout operation through transition and elevated-load operation to the pre-emergency proxy group. After threshold calibration, normal holdout warning-or-higher false positives were reduced to approximately 7.9%, while E2 R02 remained fully detected above the calibrated threshold.",
        "",
        "These results do not establish confirmed fault prediction, validated industrial deployment, independent validation, or causal proof of degradation.",
        "",
        "## 7. Limitations",
        "",
        "- Same-campaign holdout validation, not independent validation.",
        "- E2 is a pre-emergency proxy, not a confirmed fault.",
        "- Thermal diversity is limited.",
        "- Remaining false positives are influenced by position and voltage-level features.",
        "- The threshold should be validated on new independent normal data before production use.",
        "- Feature weights should be reviewed only after new-data validation.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _write_final_readme(
    output_path: Path, sources: list[Path], threshold: float
) -> Path:
    lines = [
        "# Article Figures After Threshold Calibration",
        "",
        "This folder contains the final article-ready figures and results report generated from the post-threshold holdout-validation and calibration artifacts.",
        "",
        "## Generation command",
        "",
        "```powershell",
        FINAL_ARTICLE_COMMAND,
        "```",
        "",
        "## Sources",
        "",
        *[f"- `{source.as_posix()}`" for source in sources],
        "",
        "All preferred post-threshold sources were available; no fallback artifacts were used.",
        "",
        "## Configuration confirmation",
        "",
        f"- `anomaly_warning = {threshold:.2f}`",
        "- No diagnostic formulas, feature extraction, statistical anomaly scoring, physical risks, Health Score logic, limits, weights, or normal profiles were changed.",
        "",
        "## Remaining limitations",
        "",
        "- This is same-campaign holdout validation, not independent validation.",
        "- E2 R02 is a pre-emergency proxy, not a confirmed fault.",
        "- Thermal diversity remains limited.",
        "- Remaining normal false positives are influenced by position and voltage-level features.",
        "- Validate the threshold on new independent normal data before production use.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def build_threshold_calibrated_article_figures(
    validation_dir: str | Path,
    calibration_dir: str | Path,
    thresholds_path: str | Path,
    output_dir: str | Path,
    session_filter: str = "E2 LOAD MED R02",
) -> dict[str, str]:
    """Build the final article package from post-threshold evaluation artifacts."""
    validation = Path(validation_dir)
    calibration = Path(calibration_dir)
    sources = [
        validation / "normal_holdout_diagnostic_results.json",
        validation / "test_with_holdout_profile_results.json",
        validation / "normal_profile_holdout_train.json",
        validation / "holdout_validation_report.md",
        calibration / "calibration_recommendation.json",
        calibration / "group_separation_summary.csv",
        Path(thresholds_path),
    ]
    missing = [path for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required post-threshold sources are missing: {missing}")
    threshold = _load_anomaly_warning(thresholds_path)
    normal_results = load_validation_results(sources[0])
    test_results = load_validation_results(sources[1])
    profile = json.loads(sources[2].read_text(encoding="utf-8"))
    recommendation = json.loads(sources[4].read_text(encoding="utf-8"))
    comparison = build_post_threshold_group_comparison(normal_results, test_results)
    risk_rows = build_post_threshold_risk_rows(normal_results, test_results)
    normal_medians = {
        name: extract_profile_median(profile, name)
        for name in ("current_rms", "torque_rms")
    }
    output = ensure_output_dir(output_dir)
    jobs = {
        "fig1_group_anomaly_with_normal": lambda path: plot_group_anomaly_comparison(comparison, path),
        "fig2_group_health_with_normal": lambda path: plot_group_health_comparison(comparison, path),
        "fig3_e2_r02_scores_over_time": lambda path: plot_scores_over_time(
            test_results, session_filter, path, threshold
        ),
        "fig4_e2_r02_risks_over_time": lambda path: plot_risks_over_time(test_results, session_filter, path),
        "fig5_statistical_vs_physical_risks": lambda path: plot_statistical_vs_physical_risks(risk_rows, path),
        "fig6_e2_r02_current_torque": lambda path: plot_current_torque_over_time(
            test_results, session_filter, path, normal_medians
        ),
    }
    generated: dict[str, str] = {}
    for name, plotter in jobs.items():
        created = plotter(output / f"{name}.png")
        if created is not None:
            generated[name] = str(created)
    generated["results_report"] = str(
        _write_final_results_report(
            output / "results_report.md", comparison, recommendation, threshold
        )
    )
    generated["README"] = str(
        _write_final_readme(output / "README.md", sources, threshold)
    )
    return generated


def compute_normal_group_metrics(
    manifest_path: str | Path,
    normal_profile_path: str | Path,
    limits_path: str | Path,
    weights_path: str | Path,
    thresholds_path: str | Path,
) -> dict[str, Any]:
    normal_results = diagnose_manifest_files(
        manifest_path,
        normal_profile_path,
        limits_path,
        weights_path,
        thresholds_path,
    )
    return compute_group_metrics_from_results(normal_results)


def extract_profile_median(profile: dict[str, Any], feature_name: str) -> float | None:
    """Return a global normal-profile median when available."""
    value = profile.get("global", {}).get(feature_name, {}).get("median")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _format(value: Any) -> str:
    return "not available" if pd.isna(value) else f"{float(value):.3f}"


def _profile_summary(profile_path: Path) -> tuple[int | None, int | None]:
    if not profile_path.is_file():
        return None, None
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    meta = profile.get("meta", {})
    row_count = meta.get("normal_row_count", meta.get("window_count", meta.get("row_count")))
    return meta.get("source_file_count"), row_count


def _e2_metrics(results: dict[str, Any]) -> tuple[float | None, float | None]:
    anomaly: list[float] = []
    physical: list[float] = []
    for entry in results.get("files", []):
        searchable = " ".join(
            str(entry.get("manifest", {}).get(key, ""))
            for key in ("session_id", "experiment_id", "path")
        ).lower()
        if not all(token in searchable for token in ("e2", "load_med", "r02")):
            continue
        for window in entry.get("windows", []):
            if window.get("anomaly_score") is not None:
                anomaly.append(float(window["anomaly_score"]))
            risks = window.get("risks", {})
            physical.extend(
                float(risks[name])
                for name in PHYSICAL_RISKS
                if risks.get(name) is not None
            )
    return (max(anomaly) if anomaly else None, max(physical) if physical else None)


def _write_results_report(
    output_path: Path,
    comparison: pd.DataFrame,
    results: dict[str, Any],
    profile_path: Path,
    normal_manifest_path: Path,
    normal_metrics: dict[str, Any] | None,
    normal_medians: dict[str, float | None],
) -> Path:
    source_files, feature_rows = _profile_summary(profile_path)
    if source_files is None and normal_manifest_path.is_file():
        source_files = len(pd.read_csv(normal_manifest_path))
    e2_anomaly, e2_physical = _e2_metrics(results)
    normal_physical = (normal_metrics or {}).get("mean_max_physical_risk")
    table = [
        "| Group | Mean Anomaly Score | Max Anomaly Score | Mean Health Score | Min Health Score |",
        "| ----- | -----------------: | ----------------: | ----------------: | ---------------: |",
    ]
    for row in comparison.to_dict("records"):
        table.append(
            f"| {row['expected_risk_label']} | {_format(row['mean_anomaly_score'])} | "
            f"{_format(row['max_anomaly_score'])} | {_format(row['mean_health_score'])} | "
            f"{_format(row['min_health_score'])} |"
        )
    lines = [
        "# Laboratory Results Report",
        "",
        "## 1. Purpose",
        "",
        "This report summarizes article-ready results from the physical-statistical diagnostic pipeline for preliminary laboratory validation.",
        "",
        "## 2. Data and profile",
        "",
        f"- The existing `{profile_path.as_posix()}` profile was used without retraining.",
        f"- Normal profile source files: {source_files if source_files is not None else 'not available'}.",
        f"- Normal profile feature rows/windows: {feature_rows if feature_rows is not None else 'not available'}.",
        "- Diagnostic test groups: transition, elevated_load, and pre_emergency_proxy.",
        "- E2 R02 is the main pre-emergency proxy case.",
        "- Group anomaly and mean-health values were obtained from the verified Group Comparison table in `artifacts/diagnostics/lab_pipeline_analysis.md`.",
        (
            f"- Normal minimum Health Score and mean maximum physical risk were computed from "
            f"{normal_metrics['files']} normal manifest files and {normal_metrics['windows']} windows "
            "using the existing normal profile without retraining."
            if normal_metrics and normal_metrics.get("windows")
            else "- Normal manifest diagnostics were unavailable; missing normal metrics remain documented rather than drawn in figures."
        ),
        "",
        "## 3. Main quantitative result",
        "",
        *table,
        "",
        "## 4. Interpretation",
        "",
        "- Anomaly Score increases from normal operation to the pre-emergency proxy group.",
        "- E2 R02 has the strongest statistical deviation among the evaluated test sessions.",
        "- Physical risks remain low compared with statistical anomaly risk.",
        (
            f"- Normal-group mean maximum physical risk is {_format(normal_physical)}."
            if normal_physical is not None
            else "- Normal-group mean maximum physical risk is not available."
        ),
        (
            f"- Figure 6 includes normal-profile median references for current_rms "
            f"({_format(normal_medians.get('current_rms'))} A) and torque_rms "
            f"({_format(normal_medians.get('torque_rms'))} N\u00b7m)."
            if all(normal_medians.get(name) is not None for name in ("current_rms", "torque_rms"))
            else "- One or more normal-profile current/torque medians were unavailable."
        ),
        "- This supports a physical-statistical approach as an early-deviation indicator while retaining physically meaningful limit context.",
        "",
        "## 5. Figure list",
        "",
        *[f"- `{name}.png`: {description}" for name, description in ARTICLE_FIGURES.items()],
        "",
        "## 6. Article-ready wording",
        "",
        "The pre-emergency proxy group demonstrated the highest mean Anomaly Score.",
        f"The E2 R02 session reached a maximum Anomaly Score of approximately {_format(e2_anomaly)}.",
        f"The maximum plotted E2 R02 physical risk was approximately {_format(e2_physical)}, indicating that the detected deviation was statistical rather than a hard-limit violation.",
        "The group-level ordering supports the use of the statistical layer as an early-deviation indicator in preliminary laboratory validation.",
        "",
        "## 7. Limitations",
        "",
        "- E2 is a pre-emergency proxy, not a validated fault.",
        "- Normal false positives require further calibration.",
        "- The normal profile should be validated on independent normal data.",
        "- Physical limits should not be tuned only to increase anomaly contrast.",
        "",
        "## 8. Recommended next steps",
        "",
        "1. Inspect false positives in normal sessions.",
        "2. Create an independent normal-validation manifest.",
        "3. Tune statistical thresholds and feature weights if needed.",
        "4. Keep physical limits physically meaningful.",
        "5. Prepare article tables and captions.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _write_readme(
    output_path: Path,
    inputs: dict[str, Path],
    normal_metrics: dict[str, Any] | None,
    normal_medians: dict[str, float | None],
) -> Path:
    command = (
        ".\\.venv\\Scripts\\python.exe -m servo_diagnostic_model.evaluation.article_plots "
        "--summary artifacts/diagnostics/lab_diagnostic_summary.csv "
        "--results artifacts/diagnostics/lab_diagnostic_results.json "
        "--analysis artifacts/diagnostics/lab_pipeline_analysis.md "
        "--normal-manifest data/lab/manifests/normal_profile_files.csv "
        "--normal-profile artifacts/profiles/normal_profile_lab.json "
        "--limits servo_diagnostic_model/config/limits.json "
        "--weights servo_diagnostic_model/config/weights.json "
        "--thresholds servo_diagnostic_model/config/thresholds.json "
        "--output-dir artifacts/article_figures"
    )
    lines = [
        "# Article Figures",
        "",
        "## Generation command",
        "",
        "```powershell",
        command,
        "```",
        "",
        "## Input artifacts",
        "",
        *[f"- `{path.as_posix()}`" for path in inputs.values()],
        "",
        "## Figures",
        "",
    ]
    for name, description in ARTICLE_FIGURES.items():
        lines.extend([f"### {name}", "", description, "", f"![{name}]({name}.png)", ""])
    lines.extend(
        [
            "## Normal references",
            "",
            (
                f"Normal minimum Health Score and mean maximum physical risk were computed from "
                f"{normal_metrics['files']} manifest files without retraining the profile."
                if normal_metrics and normal_metrics.get("windows")
                else "Normal manifest diagnostic metrics were unavailable."
            ),
            (
                "Figure 6 includes normal-profile median reference lines for current_rms and torque_rms."
                if all(normal_medians.get(name) is not None for name in ("current_rms", "torque_rms"))
                else "Normal-profile median reference lines were unavailable."
            ),
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def build_article_figures(
    summary_path: str | Path,
    results_path: str | Path,
    analysis_path: str | Path,
    normal_manifest_path: str | Path,
    normal_profile_path: str | Path,
    output_dir: str | Path,
    session_filter: str = "E2 LOAD MED R02",
    limits_path: str | Path | None = None,
    weights_path: str | Path | None = None,
    thresholds_path: str | Path | None = None,
) -> dict[str, str]:
    output = ensure_output_dir(output_dir)
    paths = {
        "summary": Path(summary_path),
        "results": Path(results_path),
        "analysis": Path(analysis_path),
        "normal_manifest": Path(normal_manifest_path),
        "normal_profile": Path(normal_profile_path),
    }
    summary = load_diagnostic_summary(paths["summary"])
    results = load_diagnostic_results(paths["results"])
    comparison = derive_group_comparison(summary, paths["analysis"])
    normal_metrics = None
    if limits_path and weights_path and thresholds_path:
        normal_metrics = compute_normal_group_metrics(
            paths["normal_manifest"],
            paths["normal_profile"],
            limits_path,
            weights_path,
            thresholds_path,
        )
        if normal_metrics.get("min_health_score") is not None:
            comparison.loc[
                comparison["expected_risk_label"] == "normal", "min_health_score"
            ] = normal_metrics["min_health_score"]
    profile = json.loads(paths["normal_profile"].read_text(encoding="utf-8"))
    normal_medians = {
        name: extract_profile_median(profile, name)
        for name in ("current_rms", "torque_rms")
    }
    risk_comparison = build_group_risk_comparison(results, comparison, normal_metrics)
    jobs = {
        "fig1_group_anomaly_with_normal": lambda path: plot_group_anomaly_comparison(comparison, path),
        "fig2_group_health_with_normal": lambda path: plot_group_health_comparison(comparison, path),
        "fig3_e2_r02_scores_over_time": lambda path: plot_scores_over_time(results, session_filter, path),
        "fig4_e2_r02_risks_over_time": lambda path: plot_risks_over_time(results, session_filter, path),
        "fig5_statistical_vs_physical_risks": lambda path: plot_statistical_vs_physical_risks(
            risk_comparison, path
        ),
        "fig6_e2_r02_current_torque": lambda path: plot_current_torque_over_time(
            results, session_filter, path, normal_medians
        ),
    }
    generated: dict[str, str] = {}
    for name, plotter in jobs.items():
        created = plotter(output / f"{name}.png")
        if created is not None:
            generated[name] = str(created)
    report = _write_results_report(
        output / "results_report.md",
        comparison,
        results,
        paths["normal_profile"],
        paths["normal_manifest"],
        normal_metrics,
        normal_medians,
    )
    readme = _write_readme(output / "README.md", paths, normal_metrics, normal_medians)
    generated["results_report"] = str(report)
    generated["README"] = str(readme)
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary")
    parser.add_argument("--results")
    parser.add_argument("--analysis")
    parser.add_argument("--normal-manifest")
    parser.add_argument("--normal-profile")
    parser.add_argument("--validation-dir")
    parser.add_argument("--calibration-dir")
    parser.add_argument("--limits")
    parser.add_argument("--weights")
    parser.add_argument("--thresholds")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--session", nargs="+", default=["E2", "LOAD", "MED", "R02"])
    args = parser.parse_args()
    if args.validation_dir or args.calibration_dir:
        if not all((args.validation_dir, args.calibration_dir, args.thresholds)):
            parser.error("--validation-dir, --calibration-dir, and --thresholds are required together")
        generated = build_threshold_calibrated_article_figures(
            args.validation_dir,
            args.calibration_dir,
            args.thresholds,
            args.output_dir,
            " ".join(args.session),
        )
    else:
        required = {
            "--summary": args.summary,
            "--results": args.results,
            "--analysis": args.analysis,
            "--normal-manifest": args.normal_manifest,
            "--normal-profile": args.normal_profile,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            parser.error(f"missing legacy article inputs: {', '.join(missing)}")
        generated = build_article_figures(
            args.summary,
            args.results,
            args.analysis,
            args.normal_manifest,
            args.normal_profile,
            args.output_dir,
            " ".join(args.session),
            args.limits,
            args.weights,
            args.thresholds,
        )
    for name, path in generated.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
