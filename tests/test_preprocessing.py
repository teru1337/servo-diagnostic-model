import pandas as pd

from servo_diagnostic_model.data.preprocessing import (
    coerce_numeric_columns,
    dataframe_to_samples,
    normalize_column_names,
    parse_time_columns,
    sort_by_time,
)
from servo_diagnostic_model.data.validator import validate_dataframe


def test_normalize_column_names_maps_aliases():
    df = pd.DataFrame(
        columns=[
            " timestamp ",
            "RPM",
            "current amp",
            "moment-Nm",
            "temp",
            "Custom Field",
        ]
    )

    result = normalize_column_names(df)

    assert list(result.columns) == [
        "ts",
        "velocity",
        "current_A",
        "torque_Nm",
        "drive_temp",
        "custom_field",
    ]


def test_parse_time_from_ts_creates_elapsed_seconds():
    df = pd.DataFrame(
        {"ts": ["2026-01-01T00:00:01", "2026-01-01T00:00:01.250"]}
    )

    result = parse_time_columns(df)

    assert result["ts"].notna().all()
    assert result["t"].tolist() == [0.0, 0.25]


def test_parse_time_uses_existing_t_column():
    df = pd.DataFrame(
        {
            "ts": ["2026-01-01T00:00:00", "2026-01-01T00:00:01"],
            "t": ["4.5", "5.5"],
        }
    )

    result = parse_time_columns(df)

    assert result["t"].tolist() == [4.5, 5.5]


def test_validate_missing_time_is_critical_error():
    errors, warnings = validate_dataframe(pd.DataFrame({"velocity": [100.0]}))

    assert any("time column" in error.lower() for error in errors)
    assert isinstance(warnings, list)


def test_validate_too_few_diagnostic_columns_is_critical_error():
    df = pd.DataFrame({"t": [0.0, 1.0], "velocity": [100.0, 110.0]})

    errors, _ = validate_dataframe(df)

    assert any("fewer than three" in error.lower() for error in errors)


def test_validate_zero_duration_is_critical_error():
    df = pd.DataFrame(
        {
            "t": [0.0, 0.0],
            "velocity": [100.0, 110.0],
            "current_A": [1.0, 1.1],
            "drive_temp": [30.0, 30.1],
        }
    )

    errors, _ = validate_dataframe(df)

    assert any("duration is zero" in error.lower() for error in errors)


def test_coerce_numeric_columns_preserves_missing_values():
    df = pd.DataFrame(
        {
            "t": ["0", "0.1", "bad"],
            "velocity": ["100", "bad", None],
            "statusword": ["4663", "bad", None],
        }
    )

    result = coerce_numeric_columns(df)

    assert result.loc[0, "velocity"] == 100.0
    assert pd.isna(result.loc[1, "velocity"])
    assert pd.isna(result.loc[2, "velocity"])
    assert result.loc[0, "statusword"] == 4663
    assert pd.isna(result.loc[1, "statusword"])
    assert pd.isna(result.loc[2, "statusword"])


def test_sort_by_time_and_dataframe_to_samples_tolerate_optional_fields():
    df = pd.DataFrame({"t": [1.0, 0.0], "velocity": [None, 100.0]})

    samples = dataframe_to_samples(sort_by_time(df))

    assert [sample.t for sample in samples] == [0.0, 1.0]
    assert samples[0].velocity == 100.0
    assert samples[1].velocity is None
    assert samples[0].error_code is None
