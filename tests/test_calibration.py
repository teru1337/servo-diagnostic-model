import ast
import hashlib
import json
from pathlib import Path
import sys

from servo_diagnostic_model.evaluation.calibration import (
    analyze_normal_false_positive_features,
    flatten_diagnostic_results,
    load_diagnostic_results,
    run_anomaly_threshold_sweep,
    select_calibration_candidate,
)
from servo_diagnostic_model.evaluation.lab_calibration import _main, run_lab_calibration


FORBIDDEN = {"sklearn", "tensorflow", "torch", "pytorch", "keras", "xgboost", "lightgbm", "catboost"}


def _window(score, state="observation", features=None, physical=0.1):
    return {
        "window_start": 0.0, "window_end": 5.0, "device_id": "servo",
        "health_score": 95.0, "anomaly_score": score, "state": state,
        "risk_level": "medium", "motion_phase": "moving", "features": {},
        "risks": {
            "current": physical, "torque": 0.02, "velocity": 0.03, "voltage": 0.04,
            "temperature": 0.05, "statistical_anomaly": 0.99, "data_quality": 1.0,
            "error": 1.0, "statusword": 1.0,
        },
        "main_causes": [], "explanation": [], "recommendations": [], "data_quality": {},
        "debug": {"anomaly": {"feature_scores": features or {"current_rms": score}, "profile_used": "global"}},
    }


def _entry(label, session, scores, states=None):
    return {
        "manifest": {
            "path": f"{session}.csv", "experiment_id": session.split("_R")[0],
            "session_id": session, "risk_label": label,
        },
        "windows": [
            _window(score, (states or ["observation"] * len(scores))[index])
            for index, score in enumerate(scores)
        ],
    }


def _results():
    normal = [_entry("normal", "A1_R02", [0.40, 0.52, 0.61, 0.76], ["observation", "warning", "warning", "critical"])]
    test = [
        _entry("transition", "B2_R01", [0.55, 0.60]),
        _entry("elevated_load", "B3_R01", [0.65, 0.70]),
        _entry("pre_emergency_proxy", "E2_LOAD_MED_INERTIA_R02", [0.80, 0.86]),
    ]
    return normal, test


def _write_inputs(tmp_path):
    normal, test = _results()
    normal_path = tmp_path / "normal.json"
    test_path = tmp_path / "test.json"
    thresholds = tmp_path / "thresholds.json"
    weights = tmp_path / "weights.json"
    normal_path.write_text(json.dumps(normal), encoding="utf-8")
    test_path.write_text(json.dumps(test), encoding="utf-8")
    thresholds.write_text(json.dumps({"anomaly_warning": 0.5}), encoding="utf-8")
    weights.write_text(json.dumps({"statistical_anomaly": 0.08}), encoding="utf-8")
    return normal_path, test_path, thresholds, weights


def test_load_and_flatten_preserves_groups_and_excludes_nonphysical_risks(tmp_path):
    normal, _ = _results()
    path = tmp_path / "results.json"
    path.write_text(json.dumps(normal), encoding="utf-8")

    rows = flatten_diagnostic_results(load_diagnostic_results(path))

    assert rows[0]["group"] == "normal_validation"
    assert rows[0]["session_id"] == "A1_R02"
    assert rows[0]["max_physical_risk"] == 0.1
    assert rows[0]["statistical_anomaly_risk"] == 0.99


def test_threshold_sweep_computes_expected_rates_and_columns():
    normal, test = _results()
    rows = flatten_diagnostic_results(normal + test)

    sweep = run_anomaly_threshold_sweep(rows, [0.50, 0.70])

    assert sweep[0]["normal_warning_or_higher_rate"] == 0.75
    assert sweep[1]["normal_warning_or_higher_rate"] == 0.25
    assert sweep[0]["normal_critical_rate"] == 0.25
    assert sweep[0]["ordering_holds"] is True
    assert sweep[0]["e2_r02_rank_by_max_anomaly"] == 1
    assert "transition_detection_rate_above_threshold" in sweep[0]


def test_candidate_selection_prefers_target_fpr():
    rows = [
        {"threshold": .6, "target_fpr_match": False, "normal_warning_or_higher_rate": .2},
        {"threshold": .7, "target_fpr_match": True, "normal_warning_or_higher_rate": .08},
    ]
    for row in rows:
        row.update({
            "ordering_holds": True, "e2_still_detected": True, "acceptable_critical_fpr": True,
            "e2_r02_detection_rate_above_threshold": 1.0, "e2_r02_rank_by_max_anomaly": 1,
            "mean_gap_pre_emergency_minus_normal": .2, "normal_critical_rate": 0.0,
        })

    selected = select_calibration_candidate(rows)

    assert selected["selected_threshold"] == .7
    assert selected["target_fpr_reached"] is True


def test_candidate_selection_handles_no_perfect_candidate():
    rows = []
    for threshold, rate in ((.6, .20), (.7, .12), (.8, .03)):
        rows.append({
            "threshold": threshold, "target_fpr_match": False, "normal_warning_or_higher_rate": rate,
            "ordering_holds": True, "e2_still_detected": True, "acceptable_critical_fpr": True,
            "e2_r02_detection_rate_above_threshold": 1.0, "e2_r02_rank_by_max_anomaly": 1,
            "mean_gap_pre_emergency_minus_normal": .2, "normal_critical_rate": 0.0,
        })

    selected = select_calibration_candidate(rows)

    assert selected["selected_threshold"] == .7
    assert selected["target_fpr_reached"] is False


def test_false_positive_feature_analysis_uses_debug_scores():
    normal, _ = _results()
    rows = flatten_diagnostic_results(normal)
    rows[2]["feature_scores"] = {"position_std": 1.0, "current_rms": 0.2}

    result = analyze_normal_false_positive_features(rows, 0.60)

    assert result["false_positive_windows"] == 2
    assert any(row["feature"] == "position_std" for row in result["top_features"])


def test_workflow_and_cli_create_report_without_modifying_inputs(tmp_path, monkeypatch, capsys):
    normal, test, thresholds, weights = _write_inputs(tmp_path)
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (thresholds, weights)}
    output = tmp_path / "output"

    result = run_lab_calibration(normal, test, thresholds, weights, output, .45, .90, .01)

    assert (output / "calibration_report.md").is_file()
    assert (output / "normal_false_positive_features.csv").is_file()
    assert result["production_changes_applied"] is False
    assert hashes == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in hashes}

    cli_output = tmp_path / "cli"
    monkeypatch.setattr(sys, "argv", [
        "lab_calibration", "--normal-results", str(normal), "--test-results", str(test),
        "--thresholds", str(thresholds), "--weights", str(weights), "--output-dir", str(cli_output),
        "--threshold-start", ".45", "--threshold-stop", ".90", "--threshold-step", ".01",
        "--target-fpr-min", ".05", "--target-fpr-max", ".10",
    ])
    _main()
    assert (cli_output / "calibration_report.md").is_file()
    assert "Calibration analysis complete" in capsys.readouterr().out


def test_production_configs_and_profiles_are_not_modified(tmp_path):
    paths = [
        Path("servo_diagnostic_model/config/thresholds.json"),
        Path("servo_diagnostic_model/config/weights.json"),
        Path("artifacts/profiles/normal_profile_lab.json"),
        Path("artifacts/validation/normal_profile_holdout_train.json"),
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    normal, test, thresholds, weights = _write_inputs(tmp_path)

    run_lab_calibration(normal, test, thresholds, weights, tmp_path / "output")

    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def test_calibration_modules_use_no_forbidden_ml_libraries():
    roots = set()
    for path in (
        Path("servo_diagnostic_model/evaluation/calibration.py"),
        Path("servo_diagnostic_model/evaluation/lab_calibration.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots |= {name.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for name in node.names}
        roots |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not roots.intersection(FORBIDDEN)
