"""Reproducible matplotlib plots for laboratory diagnostic artifacts."""

from __future__ import annotations

import json
import re
import warnings
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


GROUP_ORDER = ["normal", "transition", "elevated_load", "pre_emergency_proxy"]
GROUP_COLORS = {
    "normal": "#4C956C",
    "transition": "#E9C46A",
    "elevated_load": "#F4A261",
    "pre_emergency_proxy": "#D1495B",
}
PHYSICAL_RISKS = ("current", "torque", "velocity", "voltage", "temperature")


def ensure_output_dir(path: str | Path) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def load_diagnostic_summary(path: str | Path) -> pd.DataFrame:
    summary_path = Path(path)
    if not summary_path.is_file():
        raise FileNotFoundError(f"Diagnostic summary does not exist: {summary_path}")
    summary = pd.read_csv(summary_path)
    if summary.empty:
        raise ValueError(f"Diagnostic summary is empty: {summary_path}")
    if "expected_risk_label" not in summary:
        raise ValueError("Diagnostic summary must contain expected_risk_label")
    for column in (
        "mean_health_score",
        "min_health_score",
        "mean_anomaly_score",
        "max_anomaly_score",
    ):
        if column in summary:
            summary[column] = pd.to_numeric(summary[column], errors="coerce")
    return summary


def load_diagnostic_results(path: str | Path) -> dict[str, Any]:
    results_path = Path(path)
    if not results_path.is_file():
        raise FileNotFoundError(f"Diagnostic results do not exist: {results_path}")
    with results_path.open(encoding="utf-8") as file:
        results = json.load(file)
    if not isinstance(results, dict) or not isinstance(results.get("files"), list):
        raise ValueError("Diagnostic results must be an object containing a files list")
    return results


def save_figure(fig: plt.Figure, output_path: str | Path) -> Path:
    path = Path(output_path)
    ensure_output_dir(path.parent)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _ordered_groups(values: Iterable[Any]) -> list[str]:
    present = {str(value) for value in values if pd.notna(value)}
    return [group for group in GROUP_ORDER if group in present] + sorted(
        present.difference(GROUP_ORDER)
    )


def _style_axis(axis: plt.Axes) -> None:
    axis.grid(axis="y", alpha=0.25, linewidth=0.8)
    axis.spines[["top", "right"]].set_visible(False)


def plot_group_anomaly_comparison(
    summary_df: pd.DataFrame, output_path: str | Path
) -> Path:
    required = {"expected_risk_label", "mean_anomaly_score", "max_anomaly_score"}
    if not required.issubset(summary_df):
        raise ValueError(f"Summary is missing columns: {sorted(required - set(summary_df))}")
    grouped = summary_df.groupby("expected_risk_label", sort=False).agg(
        mean_anomaly=("mean_anomaly_score", "mean"),
        max_anomaly=("max_anomaly_score", "max"),
    )
    groups = _ordered_groups(grouped.index)
    x = np.arange(len(groups))
    fig, axis = plt.subplots(figsize=(9, 5.2))
    axis.bar(
        x,
        grouped.loc[groups, "mean_anomaly"],
        width=0.62,
        color=[GROUP_COLORS.get(group, "#6C757D") for group in groups],
        label="Mean Anomaly Score",
    )
    axis.scatter(
        x,
        grouped.loc[groups, "max_anomaly"],
        color="#222222",
        marker="D",
        s=38,
        label="Maximum Anomaly Score",
        zorder=3,
    )
    axis.set(title="Anomaly Score by experiment group", ylabel="Anomaly Score")
    axis.set_xticks(x, [group.replace("_", "\n") for group in groups])
    axis.set_ylim(0, max(1.0, float(grouped["max_anomaly"].max()) * 1.12))
    axis.legend(frameon=False)
    _style_axis(axis)
    fig.tight_layout()
    return save_figure(fig, output_path)


def plot_group_health_comparison(
    summary_df: pd.DataFrame, output_path: str | Path
) -> Path:
    required = {"expected_risk_label", "mean_health_score", "min_health_score"}
    if not required.issubset(summary_df):
        raise ValueError(f"Summary is missing columns: {sorted(required - set(summary_df))}")
    grouped = summary_df.groupby("expected_risk_label", sort=False).agg(
        mean_health=("mean_health_score", "mean"),
        min_health=("min_health_score", "min"),
    )
    groups = _ordered_groups(grouped.index)
    x = np.arange(len(groups))
    fig, axis = plt.subplots(figsize=(9, 5.2))
    axis.bar(
        x,
        grouped.loc[groups, "mean_health"],
        width=0.62,
        color=[GROUP_COLORS.get(group, "#6C757D") for group in groups],
        label="Mean Health Score",
    )
    axis.scatter(
        x,
        grouped.loc[groups, "min_health"],
        color="#222222",
        marker="D",
        s=38,
        label="Minimum Health Score",
        zorder=3,
    )
    axis.set(title="Health Score by experiment group", ylabel="Health Score")
    axis.set_xticks(x, [group.replace("_", "\n") for group in groups])
    axis.set_ylim(0, 100)
    axis.legend(frameon=False)
    _style_axis(axis)
    fig.tight_layout()
    return save_figure(fig, output_path)


def _normalise_filter(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _select_file(results: dict[str, Any], session_filter: str) -> dict[str, Any] | None:
    tokens = _normalise_filter(session_filter)
    for entry in results.get("files", []):
        manifest = entry.get("manifest", {})
        searchable = " ".join(
            str(manifest.get(key, "")) for key in ("session_id", "experiment_id", "path")
        ).lower()
        searchable_tokens = set(_normalise_filter(searchable))
        if tokens and all(token in searchable_tokens for token in tokens):
            return entry
    return None


def _selected_windows(
    results: dict[str, Any], session_filter: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    entry = _select_file(results, session_filter)
    windows = entry.get("windows", []) if entry else []
    return entry, [window for window in windows if isinstance(window, dict)]


def _time_axis(windows: list[dict[str, Any]]) -> np.ndarray:
    starts = pd.to_numeric(
        pd.Series([window.get("window_start") for window in windows]), errors="coerce"
    )
    if starts.notna().any():
        first = float(starts.dropna().iloc[0])
        fallback = pd.Series(np.arange(len(windows), dtype=float), index=starts.index)
        return starts.where(starts.notna(), fallback).to_numpy(dtype=float) - first
    return np.arange(len(windows), dtype=float)


def plot_scores_over_time(
    results: dict[str, Any], session_filter: str, output_path: str | Path
) -> Path | None:
    _, windows = _selected_windows(results, session_filter)
    if not windows:
        warnings.warn(f"No diagnostic windows matched session filter: {session_filter}")
        return None
    time = _time_axis(windows)
    anomaly = pd.to_numeric(
        pd.Series([window.get("anomaly_score") for window in windows]), errors="coerce"
    )
    health = pd.to_numeric(
        pd.Series([window.get("health_score") for window in windows]), errors="coerce"
    )
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.8), sharex=True)
    axes[0].plot(time, anomaly, color="#D1495B", linewidth=1.8, label="Anomaly Score")
    axes[0].set_ylabel("Anomaly Score")
    axes[0].legend(frameon=False)
    axes[1].plot(time, health, color="#277DA1", linewidth=1.8, label="Health Score")
    axes[1].set(xlabel="Time, s", ylabel="Health Score")
    axes[1].legend(frameon=False)
    for axis in axes:
        _style_axis(axis)
    fig.suptitle("E2 R02 diagnostic scores over time")
    fig.tight_layout()
    return save_figure(fig, output_path)


def plot_risks_over_time(
    results: dict[str, Any], session_filter: str, output_path: str | Path
) -> Path | None:
    _, windows = _selected_windows(results, session_filter)
    if not windows:
        warnings.warn(f"No diagnostic windows matched session filter: {session_filter}")
        return None
    risk_names = ("statistical_anomaly", "current", "torque", "velocity", "temperature")
    time = _time_axis(windows)
    fig, axis = plt.subplots(figsize=(10, 5.8))
    plotted = False
    for risk_name in risk_names:
        values = pd.to_numeric(
            pd.Series([window.get("risks", {}).get(risk_name) for window in windows]),
            errors="coerce",
        )
        if values.notna().any():
            axis.plot(time, values, linewidth=1.7, label=risk_name.replace("_", " "))
            plotted = True
    if not plotted:
        plt.close(fig)
        warnings.warn("Selected diagnostic windows contain no requested risk fields")
        return None
    axis.set(
        title="E2 R02 statistical and physical risks over time",
        xlabel="Time, s",
        ylabel="Risk, 0..1",
        ylim=(0, 1.02),
    )
    axis.legend(frameon=False, ncol=2)
    _style_axis(axis)
    fig.tight_layout()
    return save_figure(fig, output_path)


def _feature_series(
    windows: list[dict[str, Any]], preferred_names: tuple[str, ...]
) -> tuple[str | None, pd.Series]:
    for name in preferred_names:
        values = pd.to_numeric(
            pd.Series([window.get("features", {}).get(name) for window in windows]),
            errors="coerce",
        )
        if values.notna().any():
            return name, values
    return None, pd.Series(dtype=float)


def plot_current_torque_over_time(
    results: dict[str, Any], session_filter: str, output_path: str | Path
) -> Path | None:
    _, windows = _selected_windows(results, session_filter)
    if not windows:
        warnings.warn(f"No diagnostic windows matched session filter: {session_filter}")
        return None
    current_name, current = _feature_series(windows, ("current_rms", "current_abs_max"))
    torque_name, torque = _feature_series(windows, ("torque_rms", "torque_abs_max"))
    if current_name is None and torque_name is None:
        warnings.warn("Selected diagnostic windows contain no current or torque features")
        return None
    time = _time_axis(windows)
    fig, current_axis = plt.subplots(figsize=(10, 5.8))
    handles = []
    if current_name:
        handles += current_axis.plot(
            time, current, color="#277DA1", linewidth=1.7, label=current_name
        )
    current_axis.set(xlabel="Time, s", ylabel="Current, A")
    _style_axis(current_axis)
    torque_axis = current_axis.twinx()
    if torque_name:
        handles += torque_axis.plot(
            time, torque, color="#F3722C", linewidth=1.7, label=torque_name
        )
    torque_axis.set_ylabel("Torque, N·m")
    torque_axis.spines["top"].set_visible(False)
    current_axis.legend(handles=handles, labels=[line.get_label() for line in handles], frameon=False)
    current_axis.set_title("E2 R02 current and torque features over time")
    fig.tight_layout()
    return save_figure(fig, output_path)


def _risk_rows(results: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for entry in results.get("files", []):
        label = entry.get("manifest", {}).get("risk_label", "unknown")
        for window in entry.get("windows", []):
            risks = window.get("risks", {})
            row = {"group": label}
            row.update({name: risks.get(name) for name in ("statistical_anomaly", *PHYSICAL_RISKS)})
            rows.append(row)
    frame = pd.DataFrame(rows)
    for column in frame.columns.difference(["group"]):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def plot_statistical_vs_physical_risks(
    summary_or_results: pd.DataFrame | dict[str, Any], output_path: str | Path
) -> Path | None:
    if isinstance(summary_or_results, dict):
        risks = _risk_rows(summary_or_results)
    else:
        risks = summary_or_results.copy()
    required = {"group", "statistical_anomaly"}
    if risks.empty or not required.issubset(risks):
        warnings.warn("No window-level statistical and physical risks are available")
        return None
    physical = [name for name in PHYSICAL_RISKS if name in risks]
    if not physical:
        warnings.warn("No physical risks are available")
        return None
    risks["max_physical_risk"] = risks[physical].max(axis=1, skipna=True)
    grouped = risks.groupby("group", sort=False)[
        ["statistical_anomaly", "max_physical_risk"]
    ].mean()
    groups = _ordered_groups(grouped.index)
    x = np.arange(len(groups))
    width = 0.36
    fig, axis = plt.subplots(figsize=(9, 5.4))
    axis.bar(
        x - width / 2,
        grouped.loc[groups, "statistical_anomaly"],
        width,
        label="Mean statistical anomaly risk",
        color="#D1495B",
    )
    axis.bar(
        x + width / 2,
        grouped.loc[groups, "max_physical_risk"],
        width,
        label="Mean maximum physical risk",
        color="#277DA1",
    )
    axis.set(
        title="Statistical anomaly risk versus physical risks",
        ylabel="Mean risk, 0..1",
        ylim=(0, 1.02),
    )
    axis.set_xticks(x, [group.replace("_", "\n") for group in groups])
    axis.legend(frameon=False)
    _style_axis(axis)
    fig.tight_layout()
    return save_figure(fig, output_path)


def plot_data_quality_cases(
    results: dict[str, Any], output_path: str | Path
) -> Path:
    counts: Counter[str] = Counter()
    for entry in results.get("files", []):
        manifest = entry.get("manifest", {})
        session = str(manifest.get("session_id") or manifest.get("path") or "unknown")
        counts[session] += sum(
            float(window.get("risks", {}).get("data_quality") or 0) > 0
            for window in entry.get("windows", [])
        )
    nonzero = [(session, count) for session, count in counts.items() if count > 0]
    fig, axis = plt.subplots(figsize=(10, max(4.8, len(nonzero) * 0.48)))
    if nonzero:
        sessions, values = zip(*sorted(nonzero, key=lambda item: item[1]))
        axis.barh(sessions, values, color="#6C757D")
        axis.set_xlabel("Windows with nonzero data-quality risk")
        axis.grid(axis="x", alpha=0.25, linewidth=0.8)
    else:
        axis.text(
            0.5,
            0.5,
            "No windows with nonzero data-quality risk",
            ha="center",
            va="center",
            transform=axis.transAxes,
        )
        axis.set_xticks([])
        axis.set_yticks([])
    axis.set_title("Data-quality risk cases")
    axis.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return save_figure(fig, output_path)


def _write_summary(
    summary: pd.DataFrame,
    results: dict[str, Any],
    summary_path: Path,
    results_path: Path,
    outputs: dict[str, str],
    output_path: Path,
    session_filter: str,
) -> Path:
    groups = _ordered_groups(summary["expected_risk_label"])
    risk_rows = _risk_rows(results)
    selected, windows = _selected_windows(results, session_filter)
    selected_session = (
        selected.get("manifest", {}).get("session_id", session_filter) if selected else session_filter
    )
    e2_anomaly = [
        float(window["anomaly_score"])
        for window in windows
        if window.get("anomaly_score") is not None
    ]
    e2_stat = [
        float(window.get("risks", {}).get("statistical_anomaly"))
        for window in windows
        if window.get("risks", {}).get("statistical_anomaly") is not None
    ]
    e2_physical = [
        float(window.get("risks", {}).get(name))
        for window in windows
        for name in PHYSICAL_RISKS
        if window.get("risks", {}).get(name) is not None
    ]
    quality_sessions = int(
        sum(
            any(float(window.get("risks", {}).get("data_quality") or 0) > 0 for window in entry.get("windows", []))
            for entry in results.get("files", [])
        )
    )
    normal_note = (
        "The diagnostic summary does not contain normal-group rows, so the generated group charts "
        "show only the available diagnostic-test groups."
        if "normal" not in groups
        else "The diagnostic summary includes the normal group."
    )
    lines = [
        "# Laboratory Diagnostic Plots",
        "",
        "## Inputs",
        f"- `{summary_path.as_posix()}`",
        f"- `{results_path.as_posix()}`",
        "",
        "## Generated plots",
        *[f"- `{Path(path).name}`" for path in outputs.values()],
        "",
        "## Interpretation",
        "- `group_anomaly_comparison.png`: compares mean and maximum Anomaly Score across available experiment groups.",
        "- The expected group ordering is normal < transition < elevated_load < pre_emergency_proxy.",
        f"- {normal_note}",
        "- `group_health_comparison.png`: shows moderate Health Score differences; scores remain high because the measured physical risks are low.",
        f"- The E2 R02 case study uses session `{selected_session}`.",
        (
            f"- E2 R02 stands out as a statistical deviation: maximum Anomaly Score "
            f"{max(e2_anomaly):.3f} and maximum statistical anomaly risk {max(e2_stat):.3f}."
            if e2_anomaly and e2_stat
            else "- E2 R02 score fields were unavailable."
        ),
        (
            f"- E2 R02 maximum plotted physical risk is {max(e2_physical):.3f}; "
            "this supports interpreting statistical anomaly as an early-deviation indicator, not a hard-limit event."
            if e2_physical
            else "- E2 R02 physical-risk fields were unavailable."
        ),
        f"- Data-quality risk is nonzero in {quality_sessions} session(s).",
        "",
        "## Limitations",
        "- These figures describe the completed laboratory artifacts and do not establish fault prediction.",
        "- The pre-emergency proxy label is an experimental proxy, not a validated emergency prediction.",
        "- Group comparisons depend on the sessions included in the diagnostic summary.",
        "",
        "## Recommended article figures",
        "- Use `group_anomaly_comparison.png` for the group-level statistical-deviation result.",
        "- Use `e2_r02_risks_over_time.png` and `statistical_vs_physical_risks.png` to contrast statistical and physical risks.",
        "- Use `e2_r02_current_torque_over_time.png` as supporting context for the E2 R02 case study.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def build_all_lab_plots(
    summary_path: str | Path,
    results_path: str | Path,
    output_dir: str | Path,
    session_filter: str = "E2 LOAD MED R02",
) -> dict[str, str]:
    summary_file = Path(summary_path)
    results_file = Path(results_path)
    output = ensure_output_dir(output_dir)
    summary = load_diagnostic_summary(summary_file)
    results = load_diagnostic_results(results_file)
    jobs = {
        "group_anomaly_comparison": lambda path: plot_group_anomaly_comparison(summary, path),
        "group_health_comparison": lambda path: plot_group_health_comparison(summary, path),
        "e2_r02_scores_over_time": lambda path: plot_scores_over_time(results, session_filter, path),
        "e2_r02_risks_over_time": lambda path: plot_risks_over_time(results, session_filter, path),
        "e2_r02_current_torque_over_time": lambda path: plot_current_torque_over_time(
            results, session_filter, path
        ),
        "statistical_vs_physical_risks": lambda path: plot_statistical_vs_physical_risks(
            results, path
        ),
        "data_quality_cases": lambda path: plot_data_quality_cases(results, path),
    }
    generated: dict[str, str] = {}
    for name, plotter in jobs.items():
        path = output / f"{name}.png"
        created = plotter(path)
        if created is not None:
            generated[name] = str(created)
    report = _write_summary(
        summary,
        results,
        summary_file,
        results_file,
        generated,
        output / "plots_summary.md",
        session_filter,
    )
    generated["plots_summary"] = str(report)
    return generated
