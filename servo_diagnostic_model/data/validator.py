"""Validation for normalized telemetry dataframes."""

import pandas as pd


DIAGNOSTIC_COLUMNS = {
    "velocity",
    "current_A",
    "torque_Nm",
    "dc_bus_voltage",
    "drive_temp",
    "statusword",
    "error_code",
}

NUMERIC_COLUMNS = DIAGNOSTIC_COLUMNS | {
    "t",
    "position",
    "torque",
    "current",
    "rated_current_A",
    "max_current_A",
    "rated_torque_Nm",
    "max_torque_Nm",
    "max_velocity_rpm",
}


def validate_dataframe(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return critical validation errors and non-blocking warnings."""

    errors: list[str] = []
    warnings: list[str] = []

    if df.empty:
        errors.append("Telemetry dataframe is empty.")
        return errors, warnings

    errors.extend(check_time_column(df))
    errors.extend(check_required_columns(df))
    errors.extend(check_duration(df))
    warnings.extend(check_missing_columns(df))
    warnings.extend(check_numeric_quality(df))
    return errors, warnings


def check_time_column(df: pd.DataFrame) -> list[str]:
    """Validate that at least one usable time representation exists."""

    if "t" not in df.columns and "ts" not in df.columns:
        return ["Missing required time column: expected 't' or 'ts'."]

    t_valid = "t" in df.columns and pd.to_numeric(
        df["t"], errors="coerce"
    ).notna().any()
    ts_valid = "ts" in df.columns and pd.to_datetime(
        df["ts"], errors="coerce"
    ).notna().any()
    if not t_valid and not ts_valid:
        return ["Time column contains no valid values."]
    return []


def check_required_columns(df: pd.DataFrame) -> list[str]:
    """Validate that enough diagnostic channels are available."""

    available = DIAGNOSTIC_COLUMNS.intersection(df.columns)
    if len(available) < 3:
        return [
            "Fewer than three diagnostic columns are available; "
            f"found {len(available)}."
        ]
    return []


def check_missing_columns(df: pd.DataFrame) -> list[str]:
    """Warn about unavailable optional diagnostic channels."""

    return [
        f"Optional diagnostic column is missing: {column}."
        for column in sorted(DIAGNOSTIC_COLUMNS - set(df.columns))
    ]


def check_numeric_quality(df: pd.DataFrame) -> list[str]:
    """Warn when known numeric columns contain missing or invalid values."""

    warnings: list[str] = []
    for column in sorted(NUMERIC_COLUMNS.intersection(df.columns)):
        invalid_count = int(pd.to_numeric(df[column], errors="coerce").isna().sum())
        if invalid_count:
            warnings.append(
                f"Numeric column '{column}' contains {invalid_count} missing or invalid values."
            )
    return warnings


def check_duration(df: pd.DataFrame) -> list[str]:
    """Validate that elapsed time represents a non-zero duration."""

    if "t" not in df.columns:
        return []
    times = pd.to_numeric(df["t"], errors="coerce").dropna()
    if len(times) < 2:
        return ["Telemetry duration requires at least two valid time values."]
    if float(times.max() - times.min()) <= 0:
        return ["Telemetry duration is zero."]
    return []
