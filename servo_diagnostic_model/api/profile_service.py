"""Service for fitting normal statistical profiles from laboratory CSV telemetry."""

import argparse
import glob
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from servo_diagnostic_model.data.loader import load_telemetry
from servo_diagnostic_model.data.csv_pipeline import prepare_frame
from servo_diagnostic_model.data.preprocessing import dataframe_to_samples
from servo_diagnostic_model.data.validator import validate_dataframe
from servo_diagnostic_model.data.windowing import make_windows
from servo_diagnostic_model.features.feature_extractor import extract_features
from servo_diagnostic_model.model.statistical_profile import (
    filter_normal_feature_rows,
    fit_normal_profile,
    save_profile,
)


CsvPath = str | Path


def extract_feature_rows_from_csv(
    csv_path: CsvPath, thresholds: dict[str, Any]
) -> list[dict[str, Any]]:
    """Load a telemetry CSV and extract one feature dictionary per valid window."""

    dataframe = _load_and_prepare_csv(csv_path)
    windows = make_windows(
        dataframe_to_samples(dataframe),
        window_seconds=_positive_float(thresholds, "window_seconds", 5.0),
        step_seconds=_positive_float(thresholds, "window_step_seconds", 1.0),
        min_samples=_positive_int(thresholds, "min_samples_per_window", 10),
    )
    if not windows:
        raise ValueError(
            f"Telemetry CSV produced no valid windows for profile fitting: {csv_path}"
        )

    feature_rows: list[dict[str, Any]] = []
    for window in windows:
        features = extract_features(window, thresholds)
        features.update(_window_metadata(dataframe, window.start_t, window.end_t))
        feature_rows.append(features)
    return feature_rows


def extract_feature_rows_from_csv_files(
    csv_paths: Iterable[CsvPath], thresholds: dict[str, Any]
) -> list[dict[str, Any]]:
    """Extract and combine feature rows from multiple telemetry CSV files."""

    paths = _require_csv_paths(csv_paths)
    feature_rows: list[dict[str, Any]] = []
    for csv_path in paths:
        feature_rows.extend(extract_feature_rows_from_csv(csv_path, thresholds))
    return feature_rows


def read_csv_manifest(manifest_path: CsvPath) -> list[str]:
    """Read telemetry CSV paths from a manifest's required ``path`` column."""

    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV manifest not found: {path}")

    try:
        manifest = pd.read_csv(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"CSV manifest is empty: {path}") from exc
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise ValueError(f"Failed to read CSV manifest '{path}': {exc}") from exc

    if "path" not in manifest.columns:
        raise ValueError(f"CSV manifest must contain a 'path' column: {path}")

    csv_paths = [str(value).strip() for value in manifest["path"] if str(value).strip()]
    if not csv_paths:
        raise ValueError(f"CSV manifest contains no CSV paths: {path}")
    return csv_paths


def _load_and_prepare_csv(csv_path: CsvPath) -> pd.DataFrame:
    try:
        dataframe = load_telemetry(csv_path)
    except FileNotFoundError:
        raise
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise ValueError(f"Failed to load telemetry CSV '{csv_path}': {exc}") from exc

    dataframe = prepare_frame(dataframe)
    validation_errors, _ = validate_dataframe(dataframe)
    if validation_errors:
        raise ValueError(
            f"Telemetry CSV cannot be used for profile fitting '{csv_path}': "
            + "; ".join(validation_errors)
        )
    return dataframe


def _window_metadata(
    dataframe: pd.DataFrame, window_start: float, window_end: float
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    rows = dataframe.loc[
        (dataframe["t"] >= window_start) & (dataframe["t"] < window_end)
    ]
    if "is_artificial_anomaly" in rows.columns:
        metadata["is_artificial_anomaly"] = any(
            _is_truthy(value) for value in rows["is_artificial_anomaly"]
        )
    if "risk_label" in rows.columns:
        labels = [
            str(value).strip().lower()
            for value in rows["risk_label"]
            if not pd.isna(value) and str(value).strip()
        ]
        if labels:
            metadata["risk_label"] = (
                "normal"
                if all(label == "normal" for label in labels)
                else next(label for label in labels if label != "normal")
            )
    return metadata


def _is_truthy(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _filter_profile_rows(
    feature_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    metadata_filtered = [
        row
        for row in feature_rows
        if row.get("is_artificial_anomaly") is not True
        and (
            "risk_label" not in row
            or str(row.get("risk_label")).strip().lower() == "normal"
        )
    ]
    return filter_normal_feature_rows(metadata_filtered)


def _require_csv_paths(csv_paths: Iterable[CsvPath]) -> list[Path]:
    paths = [Path(path) for path in csv_paths]
    if not paths:
        raise ValueError("No CSV paths matched for profile fitting.")
    return paths


def _fit_and_save_profile(
    csv_paths: list[Path],
    output_path: CsvPath,
    thresholds: dict[str, Any],
    feature_names: list[str] | None,
    min_count: int,
) -> dict[str, Any]:
    feature_rows = extract_feature_rows_from_csv_files(csv_paths, thresholds)
    normal_rows = _filter_profile_rows(feature_rows)
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
    profile["meta"].update(
        {
            "source_file_count": len(csv_paths),
            "window_count": len(feature_rows),
            "normal_row_count": len(normal_rows),
            "profile_feature_count": len(profile["global"]),
        }
    )
    save_profile(profile, str(output_path))
    return profile


def fit_normal_profile_from_csv(
    csv_path: CsvPath,
    output_path: CsvPath,
    thresholds: dict[str, Any],
    feature_names: list[str] | None = None,
    min_count: int = 5,
) -> dict[str, Any]:
    """Fit and save a normal profile from normal laboratory CSV telemetry."""

    return fit_normal_profile_from_csv_files(
        [csv_path], output_path, thresholds, feature_names, min_count
    )


def fit_normal_profile_from_csv_files(
    csv_paths: Iterable[CsvPath],
    output_path: CsvPath,
    thresholds: dict[str, Any],
    feature_names: list[str] | None = None,
    min_count: int = 5,
) -> dict[str, Any]:
    """Fit and save a normal profile from multiple laboratory CSV files."""

    paths = _require_csv_paths(csv_paths)
    return _fit_and_save_profile(
        paths, output_path, thresholds, feature_names, min_count
    )


def fit_normal_profile_from_manifest(
    manifest_path: CsvPath,
    output_path: CsvPath,
    thresholds: dict[str, Any],
    feature_names: list[str] | None = None,
    min_count: int = 5,
) -> dict[str, Any]:
    """Fit and save a normal profile from CSV paths listed in a manifest."""

    return fit_normal_profile_from_csv_files(
        read_csv_manifest(manifest_path),
        output_path,
        thresholds,
        feature_names,
        min_count,
    )


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


def _resolve_csv_paths(
    positional_paths: Iterable[str], input_globs: Iterable[str]
) -> list[Path]:
    paths = [Path(path) for path in positional_paths]
    for pattern in input_globs:
        paths.extend(Path(path) for path in sorted(glob.glob(pattern)))

    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_paths.append(path)
    return _require_csv_paths(unique_paths)


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Fit a normal servo telemetry profile from laboratory CSV files."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="CSV input paths followed by the output normal_profile.json path.",
    )
    parser.add_argument(
        "--input-glob",
        action="append",
        default=[],
        help="Glob pattern for CSV inputs. May be repeated.",
    )
    parser.add_argument(
        "--manifest",
        action="append",
        default=[],
        help="CSV manifest containing a path column. May be repeated.",
    )
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
    output_path = args.paths[-1]
    manifest_csv_paths = [
        csv_path
        for manifest_path in args.manifest
        for csv_path in read_csv_manifest(manifest_path)
    ]
    csv_paths = _resolve_csv_paths(
        [*args.paths[:-1], *manifest_csv_paths],
        args.input_glob,
    )
    profile = fit_normal_profile_from_csv_files(
        csv_paths,
        output_path,
        thresholds,
        min_count=args.min_count,
    )
    meta = profile["meta"]
    print(
        f"Saved normal profile to {output_path}: "
        f"{meta['source_file_count']} files, {meta['window_count']} windows, "
        f"{meta['normal_row_count']} normal rows, "
        f"{meta['profile_feature_count']} profile features."
    )


if __name__ == "__main__":
    _main()
