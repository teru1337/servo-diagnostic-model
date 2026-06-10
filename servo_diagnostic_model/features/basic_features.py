"""Safe numeric helpers used by feature extraction."""

import math
from collections.abc import Iterable, Sequence
from numbers import Real


def is_valid_number(value: object) -> bool:
    """Return whether value is a finite real number, excluding booleans."""

    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def clean_values(values: Iterable[object] | None) -> list[float]:
    """Convert finite numeric values, including numeric strings, to floats."""

    if values is None:
        return []

    cleaned: list[float] = []
    for value in values:
        if isinstance(value, bool) or value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            cleaned.append(numeric)
    return cleaned


def safe_mean(values: Iterable[object] | None) -> float | None:
    cleaned = clean_values(values)
    return sum(cleaned) / len(cleaned) if cleaned else None


def safe_min(values: Iterable[object] | None) -> float | None:
    cleaned = clean_values(values)
    return min(cleaned) if cleaned else None


def safe_max(values: Iterable[object] | None) -> float | None:
    cleaned = clean_values(values)
    return max(cleaned) if cleaned else None


def safe_std(values: Iterable[object] | None) -> float | None:
    """Return population standard deviation."""

    cleaned = clean_values(values)
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return 0.0
    mean = sum(cleaned) / len(cleaned)
    return math.sqrt(sum((value - mean) ** 2 for value in cleaned) / len(cleaned))


def rms(values: Iterable[object] | None) -> float | None:
    cleaned = clean_values(values)
    if not cleaned:
        return None
    return math.sqrt(sum(value**2 for value in cleaned) / len(cleaned))


def slope(
    times: Sequence[object] | None, values: Sequence[object] | None
) -> float | None:
    """Return least-squares linear slope for valid time/value pairs."""

    if times is None or values is None:
        return None
    pairs: list[tuple[float, float]] = []
    for time, value in zip(times, values):
        cleaned_time = clean_values([time])
        cleaned_value = clean_values([value])
        if cleaned_time and cleaned_value:
            pairs.append((cleaned_time[0], cleaned_value[0]))
    if len(pairs) < 2:
        return None

    mean_time = sum(time for time, _ in pairs) / len(pairs)
    mean_value = sum(value for _, value in pairs) / len(pairs)
    denominator = sum((time - mean_time) ** 2 for time, _ in pairs)
    if denominator == 0:
        return None
    numerator = sum(
        (time - mean_time) * (value - mean_value) for time, value in pairs
    )
    return numerator / denominator


def safe_abs_max(values: Iterable[object] | None) -> float | None:
    cleaned = clean_values(values)
    return max(abs(value) for value in cleaned) if cleaned else None
