"""Service for fitting normal statistical profiles from laboratory CSV telemetry."""

import argparse
import json
from pathlib import Path
from typing import Any

from servo_diagnostic_model.data.loader import load_telemetry
from servo_diagnostic_model.data.preprocessing import (
    coerce_numeric_columns,
    dataframe_to_samples,
    normalize_column_names,
    parse_time_columns,
    sort_by_time,
)
from servo_diagnostic_model.data.validator import validate_dataframe
from servo_diagnostic_model.data.windowing import make_windows
from servo_diagnostic_model.features.feature_extractor import extract_features
from servo_diagnostic_model.model.statistical_profile import (
    filter_normal_feature_rows,
    fit_normal_profile,
    save_profile,
)


def extract_feature_rows_from_csv(
    csv_path: str, thresholds: dict[str, Any]
) -> list[dict[str, Any]]:
    """Load a telemetry CSV and extract one feature dictionary per valid window."""

    dataframe = load_telemetry(csv_path)
    dataframe = normalize_column_names(dataframe)
    dataframe = parse_time_columns(dataframe)
    dataframe = coerce_numeric_columns(dataframe)
    dataframe = sort_by_time(dataframe)
    validation_errors, _ = validate_dataframe(dataframe)
    if validation_errors:
        raise ValueError(
            "Telemetry CSV cannot be used for profile fitting: "
            + "; ".join(validation_errors)
        )

    samples = dataframe_to_samples(dataframe)
    windows = make_windows(
        samples,
        window_seconds=_positive_float(thresholds, "window_seconds", 5.0),
        step_seconds=_positive_float(thresholds, "window_step_seconds", 1.0),
        min_samples=_positive_int(thresholds, "min_samples_per_window", 10),
    )
    if not windows:
        raise ValueError(
            "Telemetry CSV produced no valid windows for profile fitting."
        )
    return [extract_features(window, thresholds) for window in windows]


def fit_normal_profile_from_csv(
    csv_path: str,
    output_path: str,
    thresholds: dict[str, Any],
    feature_names: list[str] | None = None,
    min_count: int = 5,
) -> dict[str, Any]:
    """Fit and save a normal profile from normal laboratory CSV telemetry."""

    feature_rows = extract_feature_rows_from_csv(csv_path, thresholds)
    normal_rows = filter_normal_feature_rows(feature_rows)
    if not normal_rows:
        raise ValueError(
            "No valid normal feature rows are available for profile fitting."
        )

    profile = fit_normal_profile(normal_rows, feature_names, min_count)
    if not profile.get("global"):
        raise ValueError(
            "Normal feature rows do not contain enough numeric values "
            f"to fit a global profile with min_count={min_count}."
        )
    save_profile(profile, output_path)
    return profile


def _positive_float(
    thresholds: dict[str, Any], key: str, default: float
) -> float:
    try:
        value = float(thresholds.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Threshold '{key}' must be a positive number.") from exc
    if value <= 0:
        raise ValueError(f"Threshold '{key}' must be a positive number.")
    return value


def _positive_int(thresholds: dict[str, Any], key: str, default: int) -> int:
    value = thresholds.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f"Threshold '{key}' must be a positive integer.")
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Threshold '{key}' must be a positive integer.") from exc
    if integer <= 0 or integer != float(value):
        raise ValueError(f"Threshold '{key}' must be a positive integer.")
    return integer


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Fit a normal servo telemetry profile from a laboratory CSV."
    )
    parser.add_argument("csv_path")
    parser.add_argument("output_path")
    parser.add_argument(
        "--thresholds",
        default="servo_diagnostic_model/config/thresholds.json",
        help="Path to thresholds JSON.",
    )
    parser.add_argument("--min-count", type=int, default=5)
    args = parser.parse_args()

    thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
    if not isinstance(thresholds, dict):
        raise ValueError("Thresholds file must contain a JSON object.")
    profile = fit_normal_profile_from_csv(
        args.csv_path,
        args.output_path,
        thresholds,
        min_count=args.min_count,
    )
    print(
        f"Saved normal profile with {profile['meta']['row_count']} normal windows "
        f"to {args.output_path}"
    )


if __name__ == "__main__":
    _main()
