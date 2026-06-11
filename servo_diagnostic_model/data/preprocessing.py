"""Normalization and conversion of telemetry dataframes."""

from collections.abc import Hashable
from datetime import datetime
import re
from typing import Any

import pandas as pd

from .schemas import TelemetrySample


COLUMN_ALIASES: dict[str, str] = {
    "timestamp": "ts",
    "datetime": "ts",
    "time_abs": "ts",
    "created_at": "ts",
    "time": "t",
    "time_s": "t",
    "seconds": "t",
    "elapsed": "t",
    "elapsed_s": "t",
    "speed": "velocity",
    "rpm": "velocity",
    "velocity_rpm": "velocity",
    "motor_speed": "velocity",
    "actual_velocity": "velocity",
    "current_a": "current_A",
    "current_amp": "current_A",
    "current_ampere": "current_A",
    "actual_current_a": "current_A",
    "current_permille": "current",
    "current_raw": "current",
    "current_percent": "current",
    "torque_nm": "torque_Nm",
    "actual_torque_nm": "torque_Nm",
    "moment_nm": "torque_Nm",
    "torque_permille": "torque",
    "torque_raw": "torque",
    "torque_percent": "torque",
    "moment": "torque",
    "dc_voltage": "dc_bus_voltage",
    "bus_voltage": "dc_bus_voltage",
    "vdc": "dc_bus_voltage",
    "voltage": "dc_bus_voltage",
    "dc_bus": "dc_bus_voltage",
    "temperature": "drive_temp",
    "temp": "drive_temp",
    "drive_temperature": "drive_temp",
    "servo_temp": "drive_temp",
    "power_stage_temp": "drive_temp",
    "status_word": "statusword",
    "cia402_statusword": "statusword",
    "status": "statusword",
    "error": "error_code",
    "fault_code": "error_code",
    "alarm_code": "error_code",
    "err_code": "error_code",
    "mode": "mode_display",
    "operation_mode": "mode_display",
    "drive_mode": "mode_display",
    "mode_name": "mode_display",
}

CANONICAL_COLUMNS = {
    "ts",
    "t",
    "device_id",
    "statusword",
    "mode_display",
    "position",
    "velocity",
    "torque",
    "torque_Nm",
    "current",
    "current_A",
    "dc_bus_voltage",
    "drive_temp",
    "error_code",
    "rated_current_A",
    "max_current_A",
    "rated_torque_Nm",
    "max_torque_Nm",
    "max_velocity_rpm",
}

INTEGER_COLUMNS = {"statusword", "error_code"}
NUMERIC_COLUMNS = CANONICAL_COLUMNS - {
    "ts",
    "device_id",
    "mode_display",
}


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw column names and map aliases to canonical names."""

    result = df.copy()
    canonical_by_normalized = {
        _normalize_raw_column_name(name): name for name in CANONICAL_COLUMNS
    }
    rename_map: dict[Hashable, str] = {}
    claimed = set(result.columns)

    for column in result.columns:
        normalized = _normalize_raw_column_name(column)
        target = COLUMN_ALIASES.get(
            normalized, canonical_by_normalized.get(normalized, normalized)
        )
        if target == column or (target in claimed and target != column):
            continue
        rename_map[column] = target
        claimed.add(target)

    return result.rename(columns=rename_map)


def _normalize_raw_column_name(column: Hashable) -> str:
    normalized = str(column).strip().lower().replace("-", "_")
    return re.sub(r"\s+", "_", normalized)


def parse_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Parse absolute time and derive elapsed seconds when needed."""

    result = df.copy()
    if "ts" in result.columns:
        if _looks_like_unix_seconds(result["ts"]):
            result["ts"] = pd.to_datetime(result["ts"], unit="s", errors="coerce")
        else:
            result["ts"] = pd.to_datetime(
                result["ts"], errors="coerce", format="mixed"
            )

    if "t" in result.columns:
        result["t"] = pd.to_numeric(result["t"], errors="coerce").astype(float)
    elif "ts" in result.columns:
        first_valid = result["ts"].min()
        if pd.isna(first_valid):
            result["t"] = float("nan")
        else:
            result["t"] = (result["ts"] - first_valid).dt.total_seconds()

    return result


def _looks_like_unix_seconds(values: pd.Series) -> bool:
    """Return whether a numeric series contains plausible Unix-second values."""

    if not pd.api.types.is_numeric_dtype(values):
        return False
    valid_values = values.dropna()
    if valid_values.empty:
        return False
    return bool(valid_values.between(100_000_000, 100_000_000_000).all())


def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce known numeric telemetry fields without filling invalid values."""

    result = df.copy()
    for column in NUMERIC_COLUMNS.intersection(result.columns):
        numeric = pd.to_numeric(result[column], errors="coerce")
        if column in INTEGER_COLUMNS:
            result[column] = numeric.astype("Int64")
        else:
            result[column] = numeric.astype(float)
    return result


def sort_by_time(df: pd.DataFrame) -> pd.DataFrame:
    """Sort telemetry stably by elapsed time, then absolute time."""

    if "t" in df.columns:
        sort_column = "t"
    elif "ts" in df.columns:
        sort_column = "ts"
    else:
        return df.copy().reset_index(drop=True)
    return df.sort_values(sort_column, kind="mergesort").reset_index(drop=True)


def dataframe_to_samples(df: pd.DataFrame) -> list[TelemetrySample]:
    """Convert normalized dataframe rows to telemetry samples."""

    samples: list[TelemetrySample] = []
    for row in df.to_dict(orient="records"):
        t = _optional_float(row.get("t"))
        if t is None:
            continue
        samples.append(
            TelemetrySample(
                t=t,
                ts=_optional_datetime(row.get("ts")),
                device_id=_optional_string(row.get("device_id")),
                statusword=_optional_int(row.get("statusword")),
                mode_display=_optional_string(row.get("mode_display")),
                position=_optional_float(row.get("position")),
                velocity=_optional_float(row.get("velocity")),
                torque=_optional_float(row.get("torque")),
                torque_Nm=_optional_float(row.get("torque_Nm")),
                current=_optional_float(row.get("current")),
                current_A=_optional_float(row.get("current_A")),
                dc_bus_voltage=_optional_float(row.get("dc_bus_voltage")),
                drive_temp=_optional_float(row.get("drive_temp")),
                error_code=_optional_int(row.get("error_code")),
            )
        )
    return samples


def _is_missing(value: Any) -> bool:
    return value is None or bool(pd.isna(value))


def _optional_float(value: Any) -> float | None:
    return None if _is_missing(value) else float(value)


def _optional_int(value: Any) -> int | None:
    return None if _is_missing(value) else int(value)


def _optional_string(value: Any) -> str | None:
    return None if _is_missing(value) else str(value)


def _optional_datetime(value: Any) -> datetime | None:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value if isinstance(value, datetime) else None
