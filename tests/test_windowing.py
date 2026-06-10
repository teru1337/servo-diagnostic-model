import pytest

from servo_diagnostic_model.data.schemas import TelemetrySample
from servo_diagnostic_model.data.windowing import (
    calculate_duration,
    estimate_sampling_rate,
    make_windows,
)


def samples_at(*times: float) -> list[TelemetrySample]:
    return [TelemetrySample(t=time, device_id="servo-1") for time in times]


def test_estimate_sampling_rate_uses_median_positive_delta():
    samples = samples_at(0.0, 0.1, 0.2, 5.2, 5.3)

    assert estimate_sampling_rate(samples) == pytest.approx(10.0)


def test_estimate_sampling_rate_short_data():
    assert estimate_sampling_rate(samples_at(0.0)) is None


def test_calculate_duration():
    assert calculate_duration(samples_at(3.0, 1.0, 2.0)) == 2.0


def test_calculate_duration_short_data():
    assert calculate_duration(samples_at(1.0)) is None


def test_make_windows_creates_overlapping_windows():
    samples = samples_at(*(index / 10 for index in range(101)))

    windows = make_windows(
        samples,
        window_seconds=5.0,
        step_seconds=1.0,
        min_samples=10,
    )

    assert [(window.start_t, window.end_t) for window in windows] == [
        (0.0, 5.0),
        (1.0, 6.0),
        (2.0, 7.0),
        (3.0, 8.0),
        (4.0, 9.0),
        (5.0, 10.0),
    ]
    assert all(len(window.samples) == 50 for window in windows)
    assert all(window.device_id == "servo-1" for window in windows)
    assert all(window.sampling_rate_hz == pytest.approx(10.0) for window in windows)


def test_make_windows_short_data_returns_empty_list():
    samples = samples_at(0.0, 0.1, 0.2)

    assert make_windows(samples, window_seconds=5.0, step_seconds=1.0) == []


@pytest.mark.parametrize(
    ("window_seconds", "step_seconds", "min_samples"),
    [(0.0, 1.0, 1), (1.0, 0.0, 1), (1.0, 1.0, 0)],
)
def test_make_windows_rejects_invalid_parameters(
    window_seconds, step_seconds, min_samples
):
    with pytest.raises(ValueError):
        make_windows(
            samples_at(0.0, 1.0),
            window_seconds=window_seconds,
            step_seconds=step_seconds,
            min_samples=min_samples,
        )
