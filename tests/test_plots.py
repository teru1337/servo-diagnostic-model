import ast
import json
from pathlib import Path

import pandas as pd

from servo_diagnostic_model.evaluation.plots import (
    build_all_lab_plots,
    ensure_output_dir,
    load_diagnostic_results,
    load_diagnostic_summary,
    plot_current_torque_over_time,
    plot_data_quality_cases,
    plot_group_anomaly_comparison,
    plot_group_health_comparison,
    plot_risks_over_time,
    plot_scores_over_time,
    plot_statistical_vs_physical_risks,
)


EXPECTED_FILES = {
    "group_anomaly_comparison.png",
    "group_health_comparison.png",
    "e2_r02_scores_over_time.png",
    "e2_r02_risks_over_time.png",
    "e2_r02_current_torque_over_time.png",
    "statistical_vs_physical_risks.png",
    "data_quality_cases.png",
    "plots_summary.md",
}


def _summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "expected_risk_label": [
                "normal",
                "transition",
                "elevated_load",
                "pre_emergency_proxy",
            ],
            "mean_anomaly_score": [0.1, 0.3, 0.5, 0.8],
            "max_anomaly_score": [0.2, 0.4, 0.6, 0.9],
            "mean_health_score": [98.0, 96.0, 94.0, 91.0],
            "min_health_score": [97.0, 95.0, 92.0, 88.0],
        }
    )


def _results() -> dict:
    windows = []
    for index in range(3):
        windows.append(
            {
                "window_start": float(index),
                "anomaly_score": 0.6 + index * 0.1,
                "health_score": 94.0 - index,
                "risks": {
                    "statistical_anomaly": 0.6 + index * 0.1,
                    "current": 0.02,
                    "torque": 0.03,
                    "velocity": 0.01,
                    "temperature": 0.0,
                    "data_quality": 0.2 if index == 1 else 0.0,
                },
                "features": {"current_rms": 1.0 + index, "torque_rms": 0.5 + index},
            }
        )
    return {
        "files": [
            {
                "manifest": {
                    "path": "data/lab/exports/e2.csv",
                    "experiment_id": "E2_LOAD_MED_INERTIA",
                    "session_id": "E2_LOAD_MED_INERTIA_R02",
                    "risk_label": "pre_emergency_proxy",
                },
                "windows": windows,
            },
            {
                "manifest": {
                    "path": "data/lab/exports/normal.csv",
                    "session_id": "A1_NORMAL_R01",
                    "risk_label": "normal",
                },
                "windows": [
                    {
                        "window_start": 0.0,
                        "risks": {
                            "statistical_anomaly": 0.1,
                            "current": 0.01,
                            "torque": 0.01,
                            "velocity": 0.01,
                            "data_quality": 0.0,
                        },
                    }
                ],
            },
        ]
    }


def test_load_diagnostic_artifacts(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.csv"
    results_path = tmp_path / "results.json"
    _summary().to_csv(summary_path, index=False)
    results_path.write_text(json.dumps(_results()), encoding="utf-8")

    assert len(load_diagnostic_summary(summary_path)) == 4
    assert len(load_diagnostic_results(results_path)["files"]) == 2


def test_plotting_functions_create_nonempty_files(tmp_path: Path) -> None:
    summary = _summary()
    results = _results()
    session = "E2 LOAD MED R02"
    plots = [
        plot_group_anomaly_comparison(summary, tmp_path / "anomaly.png"),
        plot_group_health_comparison(summary, tmp_path / "health.png"),
        plot_scores_over_time(results, session, tmp_path / "scores.png"),
        plot_risks_over_time(results, session, tmp_path / "risks.png"),
        plot_current_torque_over_time(results, session, tmp_path / "features.png"),
        plot_statistical_vs_physical_risks(results, tmp_path / "comparison.png"),
        plot_data_quality_cases(results, tmp_path / "quality.png"),
    ]

    assert all(path is not None and path.stat().st_size > 0 for path in plots)


def test_article_plot_labels_use_article_wording(tmp_path: Path, monkeypatch) -> None:
    figures = []

    def inspect_figure(fig, output_path):
        figures.append(fig)
        return Path(output_path)

    monkeypatch.setattr(
        "servo_diagnostic_model.evaluation.plots.save_figure", inspect_figure
    )
    plot_group_anomaly_comparison(_summary(), tmp_path / "anomaly.png")
    plot_scores_over_time(_results(), "E2 LOAD MED R02", tmp_path / "scores.png")

    anomaly_axis = figures[0].axes[0]
    visible_text = [
        anomaly_axis.get_title(),
        anomaly_axis.get_ylabel(),
        *(tick.get_text() for tick in anomaly_axis.get_xticklabels()),
        *(text.get_text() for text in anomaly_axis.get_legend().get_texts()),
        figures[1]._suptitle.get_text(),
        *(
            text.get_text()
            for axis in figures[1].axes
            for text in axis.get_legend().get_texts()
        ),
    ]
    joined = " ".join(visible_text)

    assert "Условно предаварийный" in joined
    assert "прокси" not in joined.lower()
    assert "proxy" not in joined.lower()
    assert "anomaly Score" not in joined
    assert "Anomaly Score" in joined


def test_build_all_lab_plots_creates_expected_outputs(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.csv"
    results_path = tmp_path / "results.json"
    output_dir = tmp_path / "nested" / "plots"
    _summary().to_csv(summary_path, index=False)
    results_path.write_text(json.dumps(_results()), encoding="utf-8")

    generated = build_all_lab_plots(summary_path, results_path, output_dir)

    assert output_dir.is_dir()
    assert set(path.name for path in output_dir.iterdir()) == EXPECTED_FILES
    assert all(Path(path).stat().st_size > 0 for path in generated.values())


def test_ensure_output_dir_creates_directory(tmp_path: Path) -> None:
    output = ensure_output_dir(tmp_path / "a" / "b")
    assert output.is_dir()


def test_plotting_module_does_not_import_forbidden_libraries() -> None:
    source_path = Path("servo_diagnostic_model/evaluation/plots.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
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
