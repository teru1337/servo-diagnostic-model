"""Thermal telemetry features."""

from servo_diagnostic_model.data.schemas import TelemetryWindow

from .basic_features import is_valid_number, safe_max, safe_mean, safe_min, safe_std, slope


def calculate_temperature_features(window: TelemetryWindow) -> dict[str, float | None]:
    times: list[float] = []
    temperatures: list[float] = []
    for sample in window.samples:
        if is_valid_number(sample.t) and is_valid_number(sample.drive_temp):
            times.append(float(sample.t))
            temperatures.append(float(sample.drive_temp))
    return {
        "temp_mean": safe_mean(temperatures),
        "temp_min": safe_min(temperatures),
        "temp_max": safe_max(temperatures),
        "temp_std": safe_std(temperatures),
        "temp_slope": slope(times, temperatures),
    }
