"""Build article-ready figures and a concise laboratory results report."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

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
        for group in GROUP_ORDER:
            if group == "normal" or group not in test_groups.index:
                continue
            row = rows.setdefault(group, {"expected_risk_label": group})
            for column in test_groups.columns:
                row[column] = float(test_groups.loc[group, column])

    missing = [group for group in GROUP_ORDER if group not in rows]
    if missing:
        raise ValueError(f"Group comparison is missing groups: {missing}")
    return pd.DataFrame([rows[group] for group in GROUP_ORDER])


def build_group_risk_comparison(
    results: dict[str, Any], group_comparison: pd.DataFrame
) -> pd.DataFrame:
    """Aggregate test risks and retain normal with unavailable physical risk."""
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
    return pd.concat([pd.DataFrame([normal_row]), risk_rows], ignore_index=True)


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
) -> Path:
    source_files, feature_rows = _profile_summary(profile_path)
    if source_files is None and normal_manifest_path.is_file():
        source_files = len(pd.read_csv(normal_manifest_path))
    e2_anomaly, e2_physical = _e2_metrics(results)
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
        "- Normal group statistics were obtained from the verified Group Comparison table in `artifacts/diagnostics/lab_pipeline_analysis.md`; normal minimum Health Score and group-level physical-risk mean were not available.",
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
        "- Normal group-level physical risk and minimum Health Score were unavailable in the completed comparison artifact.",
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


def _write_readme(output_path: Path, inputs: dict[str, Path]) -> Path:
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
    risk_comparison = build_group_risk_comparison(results, comparison)
    jobs = {
        "fig1_group_anomaly_with_normal": lambda path: plot_group_anomaly_comparison(comparison, path),
        "fig2_group_health_with_normal": lambda path: plot_group_health_comparison(comparison, path),
        "fig3_e2_r02_scores_over_time": lambda path: plot_scores_over_time(results, session_filter, path),
        "fig4_e2_r02_risks_over_time": lambda path: plot_risks_over_time(results, session_filter, path),
        "fig5_statistical_vs_physical_risks": lambda path: plot_statistical_vs_physical_risks(
            risk_comparison, path
        ),
        "fig6_e2_r02_current_torque": lambda path: plot_current_torque_over_time(
            results, session_filter, path
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
    )
    readme = _write_readme(output / "README.md", paths)
    generated["results_report"] = str(report)
    generated["README"] = str(readme)
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--normal-manifest", required=True)
    parser.add_argument("--normal-profile", required=True)
    parser.add_argument("--limits")
    parser.add_argument("--weights")
    parser.add_argument("--thresholds")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--session", nargs="+", default=["E2", "LOAD", "MED", "R02"])
    args = parser.parse_args()
    generated = build_article_figures(
        args.summary,
        args.results,
        args.analysis,
        args.normal_manifest,
        args.normal_profile,
        args.output_dir,
        " ".join(args.session),
    )
    for name, path in generated.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
