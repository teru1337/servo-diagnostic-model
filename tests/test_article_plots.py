import ast
import json
from pathlib import Path

import pandas as pd

from servo_diagnostic_model.evaluation.article_plots import (
    ARTICLE_FIGURES,
    build_article_figures,
    derive_group_comparison,
)


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


def test_build_article_figures_creates_expected_package(tmp_path: Path) -> None:
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
        json.dumps({"meta": {"source_file_count": 2, "feature_row_count": 20}}),
        encoding="utf-8",
    )

    generated = build_article_figures(
        summary_path,
        results_path,
        analysis_path,
        manifest_path,
        profile_path,
        output_dir,
    )

    expected = {f"{name}.png" for name in ARTICLE_FIGURES} | {"results_report.md", "README.md"}
    assert {path.name for path in output_dir.iterdir()} == expected
    assert all(Path(path).stat().st_size > 0 for path in generated.values())
    report = (output_dir / "results_report.md").read_text(encoding="utf-8")
    assert "| normal | 0.100 | 0.200 | 98.000 | not available |" in report
    assert "Normal group statistics were obtained from the verified Group Comparison table" in report


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
