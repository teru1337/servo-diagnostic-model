import ast
import json
from pathlib import Path

import pandas as pd

from servo_diagnostic_model.evaluation.article_plots import (
    ARTICLE_FIGURES,
    build_article_figures,
    compute_group_metrics_from_results,
    compute_normal_group_metrics,
    derive_group_comparison,
    extract_profile_median,
)
from servo_diagnostic_model.evaluation.plots import plot_current_torque_over_time


def _summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "expected_risk_label": ["transition", "elevated_load", "pre_emergency_proxy"],
            "mean_anomaly_score": [0.3, 0.5, 0.8],
            "max_anomaly_score": [0.4, 0.6, 0.9],
            "mean_health_score": [96.0, 94.0, 91.0],
            "min_health_score": [95.0, 92.0, 88.0],
        }
    )


def _analysis() -> str:
    return """# Analysis

## Group Comparison

| Expected group | Files | Windows | Mean file anomaly | Maximum anomaly | Mean file health |
|---|---:|---:|---:|---:|---:|
| normal | 2 | 20 | 0.100 | 0.200 | 98.000 |
| transition | 1 | 3 | 0.300 | 0.400 | 96.000 |
| elevated_load | 1 | 3 | 0.500 | 0.600 | 94.000 |
| pre_emergency_proxy | 1 | 3 | 0.800 | 0.900 | 91.000 |
"""


def _results() -> dict:
    windows = [
        {
            "window_start": float(index),
            "anomaly_score": 0.7 + index * 0.05,
            "health_score": 93.0 - index,
            "risks": {
                "statistical_anomaly": 0.7 + index * 0.05,
                "current": 0.02,
                "torque": 0.03,
                "velocity": 0.04,
                "temperature": 0.0,
            },
            "features": {"current_rms": 1.0 + index, "torque_rms": 0.5 + index},
        }
        for index in range(3)
    ]
    return {
        "files": [
            {
                "manifest": {
                    "path": "e2.csv",
                    "experiment_id": "E2_LOAD_MED_INERTIA",
                    "session_id": "E2_LOAD_MED_INERTIA_R02",
                    "risk_label": "pre_emergency_proxy",
                },
                "windows": windows,
            }
        ]
    }


def test_derive_group_comparison_includes_normal(tmp_path: Path) -> None:
    analysis_path = tmp_path / "analysis.md"
    analysis_path.write_text(_analysis(), encoding="utf-8")

    comparison = derive_group_comparison(_summary(), analysis_path)

    assert comparison["expected_risk_label"].tolist() == [
        "normal",
        "transition",
        "elevated_load",
        "pre_emergency_proxy",
    ]
    assert comparison.iloc[0]["mean_anomaly_score"] == 0.1


def test_build_article_figures_creates_expected_package(tmp_path: Path, monkeypatch) -> None:
    summary_path = tmp_path / "summary.csv"
    results_path = tmp_path / "results.json"
    analysis_path = tmp_path / "analysis.md"
    manifest_path = tmp_path / "normal.csv"
    profile_path = tmp_path / "profile.json"
    output_dir = tmp_path / "article"
    _summary().to_csv(summary_path, index=False)
    results_path.write_text(json.dumps(_results()), encoding="utf-8")
    analysis_path.write_text(_analysis(), encoding="utf-8")
    pd.DataFrame({"path": ["normal_1.csv", "normal_2.csv"]}).to_csv(manifest_path, index=False)
    profile_path.write_text(
        json.dumps(
            {
                "meta": {"source_file_count": 2, "feature_row_count": 20},
                "global": {
                    "current_rms": {"median": 0.08},
                    "torque_rms": {"median": 0.04},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "servo_diagnostic_model.evaluation.article_plots.diagnose_csv",
        lambda *args: [
            {
                "health_score": 90.0,
                "anomaly_score": 0.2,
                "risks": {"current": 0.1, "torque": 0.05, "velocity": 0.02},
            }
        ],
    )

    generated = build_article_figures(
        summary_path,
        results_path,
        analysis_path,
        manifest_path,
        profile_path,
        output_dir,
        limits_path="limits.json",
        weights_path="weights.json",
        thresholds_path="thresholds.json",
    )

    expected = {f"{name}.png" for name in ARTICLE_FIGURES} | {"results_report.md", "README.md"}
    assert {path.name for path in output_dir.iterdir()} == expected
    assert all(Path(path).stat().st_size > 0 for path in generated.values())
    report = (output_dir / "results_report.md").read_text(encoding="utf-8")
    assert "| normal | 0.100 | 0.200 | 98.000 | 90.000 |" in report
    assert "Normal-group mean maximum physical risk is 0.100." in report
    assert "Group anomaly and mean-health values were obtained from the verified Group Comparison table" in report
    assert "not available" not in Path("servo_diagnostic_model/evaluation/plots.py").read_text(
        encoding="utf-8"
    )


def test_compute_group_metrics_includes_min_health_and_physical_risk() -> None:
    metrics = compute_group_metrics_from_results(_results())

    assert metrics["min_health_score"] == 91.0
    assert metrics["mean_max_physical_risk"] == 0.04


def test_compute_normal_group_metrics_uses_manifest_diagnostics(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "normal.csv"
    manifest.write_text("path\nnormal_1.csv\nnormal_2.csv\n", encoding="utf-8")

    def fake_diagnose_csv(*args):
        return [
            {
                "health_score": 96.0,
                "anomaly_score": 0.2,
                "risks": {"current": 0.1, "torque": 0.05, "velocity": 0.02},
            }
        ]

    monkeypatch.setattr(
        "servo_diagnostic_model.evaluation.article_plots.diagnose_csv",
        fake_diagnose_csv,
    )
    metrics = compute_normal_group_metrics(
        manifest, "profile.json", "limits.json", "weights.json", "thresholds.json"
    )

    assert metrics["files"] == 2
    assert metrics["windows"] == 2
    assert metrics["min_health_score"] == 96.0
    assert metrics["mean_max_physical_risk"] == 0.1


def test_extract_profile_median() -> None:
    profile = {"global": {"current_rms": {"median": 0.08}}}
    assert extract_profile_median(profile, "current_rms") == 0.08
    assert extract_profile_median(profile, "torque_rms") is None


def test_current_torque_plot_adds_profile_reference_lines(tmp_path: Path, monkeypatch) -> None:
    labels = []

    def inspect_figure(fig, output_path):
        labels.extend(line.get_label() for axis in fig.axes for line in axis.lines)
        return Path(output_path)

    monkeypatch.setattr(
        "servo_diagnostic_model.evaluation.plots.save_figure", inspect_figure
    )
    plot_current_torque_over_time(
        _results(),
        "E2 LOAD MED R02",
        tmp_path / "features.png",
        {"current_rms": 0.08, "torque_rms": 0.04},
    )

    assert "normal median current_rms" in labels
    assert "normal median torque_rms" in labels


def test_article_plotting_module_does_not_import_forbidden_libraries() -> None:
    source = Path("servo_diagnostic_model/evaluation/article_plots.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {
        "seaborn",
        "sklearn",
        "tensorflow",
        "torch",
        "keras",
        "xgboost",
        "lightgbm",
        "catboost",
        "plotly",
        "bokeh",
    }
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imports.intersection(forbidden)
