import ast
import json
from pathlib import Path

import pytest

from servo_diagnostic_model.api.profile_service import (
    extract_feature_rows_from_csv,
    fit_normal_profile_from_csv,
)
from servo_diagnostic_model.model.statistical_profile import load_profile


THRESHOLDS = {
    "window_seconds": 5,
    "window_step_seconds": 1,
    "min_samples_per_window": 10,
}

FORBIDDEN_IMPORTS = {
    "sklearn",
    "tensorflow",
    "torch",
    "pytorch",
    "keras",
    "xgboost",
    "lightgbm",
    "catboost",
}


def _write_telemetry_csv(path, error_code=0):
    rows = [
        "t,device_id,statusword,velocity,current_A,torque_Nm,dc_bus_voltage,drive_temp,error_code"
    ]
    rows.extend(
        (
            f"{index / 10},servo-1,4,{100 + index % 5},"
            f"{1 + index % 3 / 100},{0.5 + index % 2 / 100},"
            f"{310 + index % 4 / 10},{35 + index % 3 / 100},{error_code}"
        )
        for index in range(101)
    )
    path.write_text("\n".join(rows), encoding="utf-8")


def test_extract_feature_rows_from_csv_returns_rows(tmp_path):
    csv_path = tmp_path / "normal.csv"
    _write_telemetry_csv(csv_path)

    rows = extract_feature_rows_from_csv(str(csv_path), THRESHOLDS)

    assert rows
    assert all("motion_phase" in row for row in rows)
    assert all("current_rms" in row for row in rows)


def test_fit_normal_profile_from_csv_creates_global_stats(tmp_path):
    csv_path = tmp_path / "normal.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(csv_path)

    profile = fit_normal_profile_from_csv(
        str(csv_path), str(output_path), THRESHOLDS, min_count=5
    )

    assert profile["global"]
    assert "current_rms" in profile["global"]


def test_fit_normal_profile_from_csv_writes_json_file(tmp_path):
    csv_path = tmp_path / "normal.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(csv_path)

    profile = fit_normal_profile_from_csv(
        str(csv_path), str(output_path), THRESHOLDS, min_count=5
    )

    assert output_path.is_file()
    assert json.loads(output_path.read_text(encoding="utf-8")) == profile


def test_output_profile_contains_required_sections(tmp_path):
    csv_path = tmp_path / "normal.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(csv_path)

    profile = fit_normal_profile_from_csv(
        str(csv_path), str(output_path), THRESHOLDS, min_count=5
    )

    assert {"meta", "global", "by_motion_phase"} <= profile.keys()


@pytest.mark.parametrize(
    "contents",
    [
        "",
        "velocity,current_A,torque_Nm\n100,1,0.5\n",
    ],
)
def test_invalid_or_empty_csv_raises_clear_error(tmp_path, contents):
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match="empty|cannot be used"):
        extract_feature_rows_from_csv(str(csv_path), THRESHOLDS)


def test_no_normal_rows_raises_clear_error(tmp_path):
    csv_path = tmp_path / "faulted.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(csv_path, error_code=42)

    with pytest.raises(ValueError, match="No valid normal feature rows"):
        fit_normal_profile_from_csv(
            str(csv_path), str(output_path), THRESHOLDS, min_count=5
        )


def test_saved_profile_can_be_loaded(tmp_path):
    csv_path = tmp_path / "normal.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(csv_path)

    profile = fit_normal_profile_from_csv(
        str(csv_path), str(output_path), THRESHOLDS, min_count=5
    )

    assert load_profile(str(output_path)) == profile


def test_profile_service_uses_no_forbidden_ml_libraries():
    path = Path("servo_diagnostic_model/api/profile_service.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_roots = {
        name.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for name in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert not imported_roots.intersection(FORBIDDEN_IMPORTS)
