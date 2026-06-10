"""Telemetry file loaders."""

from pathlib import Path

import pandas as pd


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load telemetry from a CSV file."""

    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Telemetry file not found: {csv_path}")

    try:
        return pd.read_csv(csv_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"Telemetry CSV is empty: {csv_path}") from exc


def load_telemetry(path: str | Path) -> pd.DataFrame:
    """Load telemetry using the loader selected by file extension."""

    telemetry_path = Path(path)
    if telemetry_path.suffix.lower() == ".csv":
        return load_csv(telemetry_path)
    raise ValueError(
        f"Unsupported telemetry file type: {telemetry_path.suffix or '<none>'}"
    )
