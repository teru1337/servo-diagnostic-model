"""Shared preparation of CSV telemetry at the service boundary."""

from pathlib import Path

import pandas as pd

from .loader import load_telemetry
from .preprocessing import (
    coerce_numeric_columns,
    normalize_column_names,
    parse_time_columns,
    sort_by_time,
)


def prepare_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize columns and values before validating or windowing."""
    dataframe = normalize_column_names(dataframe)
    dataframe = parse_time_columns(dataframe)
    dataframe = coerce_numeric_columns(dataframe)
    return sort_by_time(dataframe)


def read_csv(path: str | Path) -> pd.DataFrame:
    """Load and prepare a CSV, leaving error policy to the caller."""
    return prepare_frame(load_telemetry(path))
