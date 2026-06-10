"""Time calculations and window creation for telemetry samples."""

from statistics import median

from .schemas import TelemetrySample, TelemetryWindow


def estimate_sampling_rate(samples: list[TelemetrySample]) -> float | None:
    """Estimate sampling frequency from the median positive time delta."""

    times = sorted(sample.t for sample in samples)
    deltas = [
        current - previous
        for previous, current in zip(times, times[1:])
        if current - previous > 0
    ]
    if not deltas:
        return None
    return 1.0 / median(deltas)


def calculate_duration(samples: list[TelemetrySample]) -> float | None:
    """Calculate recording duration from elapsed sample times."""

    if len(samples) < 2:
        return None
    times = [sample.t for sample in samples]
    return max(times) - min(times)


def make_windows(
    samples: list[TelemetrySample],
    window_seconds: float,
    step_seconds: float,
    min_samples: int = 10,
) -> list[TelemetryWindow]:
    """Create overlapping half-open time windows and skip short windows."""

    if window_seconds <= 0:
        raise ValueError("window_seconds must be greater than zero.")
    if step_seconds <= 0:
        raise ValueError("step_seconds must be greater than zero.")
    if min_samples <= 0:
        raise ValueError("min_samples must be greater than zero.")
    if not samples:
        return []

    ordered = sorted(samples, key=lambda sample: sample.t)
    start = ordered[0].t
    end = ordered[-1].t
    sampling_rate_hz = estimate_sampling_rate(ordered)
    windows: list[TelemetryWindow] = []
    current_start = start

    while current_start + window_seconds <= end:
        current_end = current_start + window_seconds
        window_samples = [
            sample
            for sample in ordered
            if current_start <= sample.t < current_end
        ]
        if len(window_samples) >= min_samples:
            windows.append(
                TelemetryWindow(
                    samples=window_samples,
                    start_t=current_start,
                    end_t=current_end,
                    device_id=_detect_device_id(window_samples),
                    sampling_rate_hz=sampling_rate_hz,
                )
            )
        current_start += step_seconds

    return windows


def _detect_device_id(samples: list[TelemetrySample]) -> str | None:
    device_ids = {sample.device_id for sample in samples if sample.device_id is not None}
    return next(iter(device_ids)) if len(device_ids) == 1 else None
