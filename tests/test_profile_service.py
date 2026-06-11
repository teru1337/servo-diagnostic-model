import ast
import json
from pathlib import Path
import sys

import pytest

from servo_diagnostic_model.api.profile_service import (
    _main,
    extract_feature_rows_from_csv,
    extract_feature_rows_from_csv_files,
    fit_normal_profile_from_csv,
    fit_normal_profile_from_csv_files,
    fit_normal_profile_from_manifest,
    read_csv_manifest,
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


def _write_telemetry_csv(
    path, error_code=0, risk_label=None, is_artificial_anomaly=None
):
    metadata_columns = []
    if risk_label is not None:
        metadata_columns.append("risk_label")
    if is_artificial_anomaly is not None:
        metadata_columns.append("is_artificial_anomaly")
    rows = [
        "t,device_id,statusword,velocity,current_A,torque_Nm,dc_bus_voltage,drive_temp,error_code"
        + ("," + ",".join(metadata_columns) if metadata_columns else "")
    ]
    for index in range(101):
        values = [
            f"{index / 10},servo-1,4,{100 + index % 5},"
            f"{1 + index % 3 / 100},{0.5 + index % 2 / 100},"
            f"{310 + index % 4 / 10},{35 + index % 3 / 100},{error_code}"
        ]
        if risk_label is not None:
            values.append(str(risk_label(index) if callable(risk_label) else risk_label))
        if is_artificial_anomaly is not None:
            values.append(
                str(
                    is_artificial_anomaly(index)
                    if callable(is_artificial_anomaly)
                    else is_artificial_anomaly
                )
            )
        rows.append(",".join(values))
    path.write_text("\n".join(rows), encoding="utf-8")


def _write_manifest(path, csv_paths):
    rows = ["path,comment"]
    rows.extend(f"{csv_path},normal laboratory telemetry" for csv_path in csv_paths)
    path.write_text("\n".join(rows), encoding="utf-8")


def test_extract_feature_rows_from_csv_returns_rows(tmp_path):
    csv_path = tmp_path / "normal.csv"
    _write_telemetry_csv(csv_path)

    rows = extract_feature_rows_from_csv(str(csv_path), THRESHOLDS)

    assert rows
    assert all("motion_phase" in row for row in rows)
    assert all("current_rms" in row for row in rows)


def test_extract_feature_rows_from_csv_files_combines_files(tmp_path):
    first = tmp_path / "normal-1.csv"
    second = tmp_path / "normal-2.csv"
    _write_telemetry_csv(first)
    _write_telemetry_csv(second)

    rows = extract_feature_rows_from_csv_files([first, second], THRESHOLDS)

    assert len(rows) == 12


def test_fit_normal_profile_from_csv_creates_global_stats(tmp_path):
    csv_path = tmp_path / "normal.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(csv_path)

    profile = fit_normal_profile_from_csv(
        str(csv_path), str(output_path), THRESHOLDS, min_count=5
    )

    assert profile["global"]
    assert "current_rms" in profile["global"]


def test_fit_normal_profile_from_two_csv_files(tmp_path):
    first = tmp_path / "normal-1.csv"
    second = tmp_path / "normal-2.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(first)
    _write_telemetry_csv(second)

    profile = fit_normal_profile_from_csv_files(
        [first, second], output_path, THRESHOLDS, min_count=5
    )

    assert profile["meta"]["source_file_count"] == 2
    assert profile["meta"]["window_count"] == 12
    assert profile["meta"]["normal_row_count"] == 12
    assert profile["meta"]["profile_feature_count"] == len(profile["global"])


def test_read_csv_manifest_reads_path_column(tmp_path):
    first = tmp_path / "normal-1.csv"
    second = tmp_path / "normal-2.csv"
    manifest_path = tmp_path / "normal_profile_files.csv"
    _write_manifest(manifest_path, [first, second])

    assert read_csv_manifest(manifest_path) == [str(first), str(second)]


def test_missing_manifest_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="CSV manifest not found"):
        read_csv_manifest(tmp_path / "missing.csv")


def test_manifest_without_path_column_fails(tmp_path):
    manifest_path = tmp_path / "invalid.csv"
    manifest_path.write_text("file,comment\nnormal.csv,input\n", encoding="utf-8")

    with pytest.raises(ValueError, match="'path' column"):
        read_csv_manifest(manifest_path)


@pytest.mark.parametrize("contents", ["", "path,comment\n"])
def test_empty_manifest_fails(tmp_path, contents):
    manifest_path = tmp_path / "empty.csv"
    manifest_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match="empty|no CSV paths"):
        read_csv_manifest(manifest_path)


def test_fit_normal_profile_from_manifest_with_two_csv_files(tmp_path):
    first = tmp_path / "normal-1.csv"
    second = tmp_path / "normal-2.csv"
    manifest_path = tmp_path / "normal_profile_files.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(first)
    _write_telemetry_csv(second)
    _write_manifest(manifest_path, [first, second])

    profile = fit_normal_profile_from_manifest(
        manifest_path, output_path, THRESHOLDS, min_count=5
    )

    assert profile["meta"]["source_file_count"] == 2
    assert profile["meta"]["normal_row_count"] == 12
    assert load_profile(str(output_path)) == profile


def test_manifest_with_missing_csv_path_raises_clear_error(tmp_path):
    manifest_path = tmp_path / "normal_profile_files.csv"
    _write_manifest(manifest_path, [tmp_path / "missing.csv"])

    with pytest.raises(FileNotFoundError, match="Telemetry file not found"):
        fit_normal_profile_from_manifest(
            manifest_path,
            tmp_path / "normal_profile.json",
            THRESHOLDS,
        )


def test_manifest_with_no_normal_rows_raises_clear_error(tmp_path):
    csv_path = tmp_path / "faulted.csv"
    manifest_path = tmp_path / "normal_profile_files.csv"
    _write_telemetry_csv(csv_path, error_code=42)
    _write_manifest(manifest_path, [csv_path])

    with pytest.raises(ValueError, match="No valid normal feature rows"):
        fit_normal_profile_from_manifest(
            manifest_path,
            tmp_path / "normal_profile.json",
            THRESHOLDS,
        )


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
    assert profile["by_motion_phase"]


def test_profile_result_is_json_serializable(tmp_path):
    csv_path = tmp_path / "normal.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(csv_path)

    profile = fit_normal_profile_from_csv(
        csv_path, output_path, THRESHOLDS, min_count=5
    )

    json.dumps(profile, allow_nan=False)


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


def test_no_csv_paths_matched_raises_clear_error(tmp_path):
    with pytest.raises(ValueError, match="No CSV paths matched"):
        fit_normal_profile_from_csv_files(
            [], tmp_path / "normal_profile.json", THRESHOLDS
        )


def test_missing_csv_path_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Telemetry file not found"):
        fit_normal_profile_from_csv_files(
            [tmp_path / "missing.csv"],
            tmp_path / "normal_profile.json",
            THRESHOLDS,
        )


def test_mixed_normal_and_error_csv_excludes_bad_windows(tmp_path):
    normal_path = tmp_path / "normal.csv"
    error_path = tmp_path / "error.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(normal_path, risk_label="normal")
    _write_telemetry_csv(error_path, error_code=42, risk_label="error")

    profile = fit_normal_profile_from_csv_files(
        [normal_path, error_path], output_path, THRESHOLDS, min_count=5
    )

    assert profile["meta"]["window_count"] == 12
    assert profile["meta"]["normal_row_count"] == 6
    assert profile["meta"]["row_count"] == 6


def test_mixed_risk_labels_within_csv_exclude_non_normal_windows(tmp_path):
    csv_path = tmp_path / "mixed.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(
        csv_path, risk_label=lambda index: "normal" if index < 60 else "error"
    )

    profile = fit_normal_profile_from_csv(
        csv_path, output_path, THRESHOLDS, min_count=1
    )

    assert profile["meta"]["window_count"] == 6
    assert 0 < profile["meta"]["normal_row_count"] < 6


def test_artificial_anomaly_rows_are_excluded(tmp_path):
    normal_path = tmp_path / "normal.csv"
    artificial_path = tmp_path / "artificial.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(normal_path, risk_label="normal", is_artificial_anomaly=0)
    _write_telemetry_csv(
        artificial_path, risk_label="normal", is_artificial_anomaly=1
    )

    profile = fit_normal_profile_from_csv_files(
        [normal_path, artificial_path], output_path, THRESHOLDS, min_count=5
    )

    assert profile["meta"]["normal_row_count"] == 6


def test_input_glob_matches_multiple_files(tmp_path, monkeypatch, capsys):
    _write_telemetry_csv(tmp_path / "normal-1.csv")
    _write_telemetry_csv(tmp_path / "normal-2.csv")
    output_path = tmp_path / "normal_profile.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "profile_service",
            "--input-glob",
            str(tmp_path / "*.csv"),
            str(output_path),
        ],
    )

    _main()

    profile = load_profile(str(output_path))
    assert profile["meta"]["source_file_count"] == 2
    assert "2 files" in capsys.readouterr().out


def test_manifest_cli_fits_multiple_files(tmp_path, monkeypatch, capsys):
    first = tmp_path / "normal-1.csv"
    second = tmp_path / "normal-2.csv"
    manifest_path = tmp_path / "normal_profile_files.csv"
    output_path = tmp_path / "normal_profile.json"
    _write_telemetry_csv(first)
    _write_telemetry_csv(second)
    _write_manifest(manifest_path, [first, second])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "profile_service",
            "--manifest",
            str(manifest_path),
            str(output_path),
        ],
    )

    _main()

    profile = load_profile(str(output_path))
    assert profile["meta"]["source_file_count"] == 2
    assert "2 files" in capsys.readouterr().out


def test_input_glob_with_no_matches_raises_clear_error(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "profile_service",
            "--input-glob",
            str(tmp_path / "*.csv"),
            str(tmp_path / "normal_profile.json"),
        ],
    )

    with pytest.raises(ValueError, match="No CSV paths matched"):
        _main()


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
