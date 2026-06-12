import ast
import json
from pathlib import Path
import sys

import pandas as pd

from servo_diagnostic_model.evaluation.lab_validation import _main, run_lab_validation
from servo_diagnostic_model.evaluation.validation import (
    compute_validation_metrics,
    create_normal_holdout_manifests,
    diagnose_manifest,
    fit_validation_normal_profile,
    group_comparison,
)


FORBIDDEN_IMPORTS = {
    "sklearn", "tensorflow", "torch", "pytorch", "keras", "xgboost", "lightgbm", "catboost"
}


def _write_telemetry(path: Path, offset: float = 0.0) -> None:
    rows = [
        "t,device_id,statusword,velocity,current_A,torque_Nm,dc_bus_voltage,drive_temp,error_code"
    ]
    for index in range(101):
        rows.append(
            f"{index / 10},servo-1,4,{100 + offset + index % 5},"
            f"{1 + offset / 100 + index % 3 / 100},{0.5 + index % 2 / 100},"
            f"{310 + index % 4 / 10},{35 + index % 3 / 100},0"
        )
    path.write_text("\n".join(rows), encoding="utf-8")


def _write_manifest(path: Path, rows: list[tuple[Path, str, str]]) -> None:
    pd.DataFrame(
        [
            {"path": str(csv), "session_id": session, "risk_label": label, "comment": "test"}
            for csv, session, label in rows
        ]
    ).to_csv(path, index=False)


def _write_configs(tmp_path: Path) -> tuple[Path, Path, Path]:
    limits = {
        "rated_current_A": 4.27, "max_current_A": 12.8, "rated_torque_Nm": 2.39,
        "max_torque_Nm": 8.36, "max_velocity_rpm": 6000, "dc_bus_min_safe": 280,
        "dc_bus_max_safe": 340, "dc_bus_min_critical": 240, "dc_bus_max_critical": 380,
        "voltage_std_limit": 5.0, "temp_safe": 55, "temp_warning": 70,
        "temp_critical": 85, "temp_slope_limit": 0.2, "missing_ratio_limit": 0.3,
        "invalid_ratio_limit": 0.2, "time_gap_count_limit": 3,
    }
    weights = {
        "error": 0.25, "statusword": 0.15, "temperature": 0.18, "current": 0.16,
        "torque": 0.14, "voltage": 0.14, "statistical_anomaly": 0.08,
        "velocity": 0.03, "data_quality": 0.02,
    }
    thresholds = {
        "window_seconds": 5, "window_step_seconds": 1, "min_samples_per_window": 10,
        "health_normal": 85, "health_observation": 70, "health_warning": 50,
        "anomaly_observation": 0.3, "anomaly_warning": 0.5, "anomaly_critical": 0.75,
        "risk_observation": 0.5, "risk_warning": 0.75, "risk_critical": 0.9,
        "min_risk_for_main_cause": 0.3,
    }
    paths = tuple(tmp_path / name for name in ("limits.json", "weights.json", "thresholds.json"))
    for path, value in zip(paths, (limits, weights, thresholds)):
        path.write_text(json.dumps(value), encoding="utf-8")
    return paths


def _dataset(tmp_path: Path) -> tuple[Path, Path, tuple[Path, Path, Path]]:
    normal_rows = []
    for experiment in ("A1", "A2"):
        for repeat in ("R01", "R02"):
            csv = tmp_path / f"{experiment}_{repeat}.csv"
            _write_telemetry(csv, 0 if repeat == "R01" else 1)
            normal_rows.append((csv, f"{experiment}_{repeat}", "normal"))
    test_rows = []
    for index, label in enumerate(("transition", "elevated_load", "pre_emergency_proxy")):
        csv = tmp_path / f"T{index}.csv"
        _write_telemetry(csv, (index + 1) * 20)
        session = "E2_LOAD_MED_INERTIA_R02" if label == "pre_emergency_proxy" else f"T{index}_R01"
        test_rows.append((csv, session, label))
    normal_manifest = tmp_path / "normal.csv"
    test_manifest = tmp_path / "test.csv"
    _write_manifest(normal_manifest, normal_rows)
    _write_manifest(test_manifest, test_rows)
    return normal_manifest, test_manifest, _write_configs(tmp_path)


def test_holdout_split_is_deterministic_and_non_overlapping(tmp_path):
    normal, _, _ = _dataset(tmp_path)
    first_train = tmp_path / "first_train.csv"
    first_validation = tmp_path / "first_validation.csv"
    second_train = tmp_path / "second_train.csv"
    second_validation = tmp_path / "second_validation.csv"

    first = create_normal_holdout_manifests(normal, first_train, first_validation)
    second = create_normal_holdout_manifests(normal, second_train, second_validation)

    assert first["train_files"] == 2
    assert first["validation_files"] == 2
    assert first["overlap_count"] == 0
    assert first_train.read_text() == second_train.read_text()
    assert first_validation.read_text() == second_validation.read_text()


def test_holdout_split_falls_back_to_deterministic_seeded_split(tmp_path):
    source = tmp_path / "normal.csv"
    rows = []
    for index in range(5):
        csv = tmp_path / f"normal-{index}.csv"
        rows.append((csv, f"session-{index}", "normal"))
    _write_manifest(source, rows)

    first = create_normal_holdout_manifests(
        source, tmp_path / "train-1.csv", tmp_path / "validation-1.csv"
    )
    second = create_normal_holdout_manifests(
        source, tmp_path / "train-2.csv", tmp_path / "validation-2.csv"
    )

    assert first["strategy_used"] == "seeded"
    assert first["train_paths"] == second["train_paths"]
    assert first["validation_paths"] == second["validation_paths"]
    assert not set(first["train_paths"]) & set(first["validation_paths"])


def test_profile_is_separate_and_diagnostics_are_json_compatible(tmp_path):
    normal, _, (limits, weights, thresholds) = _dataset(tmp_path)
    train = tmp_path / "train.csv"
    validation = tmp_path / "validation.csv"
    production = tmp_path / "production.json"
    output = tmp_path / "holdout.json"
    production.write_text('{"production": true}', encoding="utf-8")
    create_normal_holdout_manifests(normal, train, validation)

    profile = fit_validation_normal_profile(train, output, thresholds)
    results = diagnose_manifest(validation, output, limits, weights, thresholds)

    assert output.is_file()
    assert profile["meta"]["validation_role"] == "holdout_train"
    assert json.loads(production.read_text()) == {"production": True}
    json.dumps(results, allow_nan=False)


def test_metrics_and_group_comparison_include_required_fields(tmp_path):
    normal, test, (limits, weights, thresholds) = _dataset(tmp_path)
    train = tmp_path / "train.csv"
    validation = tmp_path / "validation.csv"
    profile = tmp_path / "profile.json"
    create_normal_holdout_manifests(normal, train, validation)
    fit_validation_normal_profile(train, profile, thresholds)
    normal_results = diagnose_manifest(validation, profile, limits, weights, thresholds)
    test_results = diagnose_manifest(test, profile, limits, weights, thresholds)
    threshold_values = json.loads(thresholds.read_text())

    metrics = compute_validation_metrics(normal_results, "normal_validation", threshold_values)
    comparison = group_comparison(normal_results, test_results, threshold_values)

    assert "false_positive_rate_warning_or_higher" in metrics
    assert "false_positive_rate_critical" in metrics
    assert "anomaly_threshold_exceedance_rate" in metrics
    assert list(comparison["expected_group"]) == [
        "normal_validation", "transition", "elevated_load", "pre_emergency_proxy"
    ]


def test_end_to_end_workflow_creates_required_artifacts(tmp_path):
    normal, test, (limits, weights, thresholds) = _dataset(tmp_path)
    output = tmp_path / "artifacts"

    result = run_lab_validation(normal, test, limits, weights, thresholds, output)

    required = {
        "normal_profile_holdout_train.json", "normal_holdout_diagnostic_results.json",
        "normal_holdout_summary.csv", "test_with_holdout_profile_results.json",
        "test_with_holdout_profile_summary.csv", "holdout_validation_report.md",
    }
    assert required <= {path.name for path in output.iterdir()}
    assert result["split"]["overlap_count"] == 0
    assert "# Normal Holdout Validation Report" in (output / "holdout_validation_report.md").read_text()


def test_cli_runs_on_tiny_synthetic_artifacts(tmp_path, monkeypatch, capsys):
    normal, test, (limits, weights, thresholds) = _dataset(tmp_path)
    output = tmp_path / "cli-output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "lab_validation", "--normal-manifest", str(normal), "--test-manifest", str(test),
            "--limits", str(limits), "--weights", str(weights), "--thresholds", str(thresholds),
            "--output-dir", str(output), "--strategy", "by_repeat",
        ],
    )

    _main()

    assert (output / "holdout_validation_report.md").is_file()
    assert "Holdout validation complete" in capsys.readouterr().out


def test_validation_modules_use_no_forbidden_ml_libraries():
    imported_roots = set()
    for path in (
        Path("servo_diagnostic_model/evaluation/validation.py"),
        Path("servo_diagnostic_model/evaluation/lab_validation.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_roots |= {
            name.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for name in node.names
        }
        imported_roots |= {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
    assert not imported_roots.intersection(FORBIDDEN_IMPORTS)
