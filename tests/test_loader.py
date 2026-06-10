import pandas as pd
import pytest

from servo_diagnostic_model.data.loader import load_csv, load_telemetry


def test_load_csv_success(tmp_path):
    path = tmp_path / "telemetry.csv"
    path.write_text("t,velocity\n0.0,100\n0.1,110\n", encoding="utf-8")

    result = load_csv(path)

    assert list(result.columns) == ["t", "velocity"]
    assert len(result) == 2


def test_load_csv_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_csv(tmp_path / "missing.csv")


def test_load_telemetry_dispatches_csv(tmp_path):
    path = tmp_path / "telemetry.CSV"
    pd.DataFrame({"t": [0.0]}).to_csv(path, index=False)

    result = load_telemetry(path)

    assert result.loc[0, "t"] == 0.0


def test_load_telemetry_rejects_unsupported_type(tmp_path):
    path = tmp_path / "telemetry.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported telemetry file type"):
        load_telemetry(path)
