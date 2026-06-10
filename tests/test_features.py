import math

import pytest

from servo_diagnostic_model.data.schemas import TelemetrySample, TelemetryWindow
from servo_diagnostic_model.features.basic_features import (
    clean_values,
    is_valid_number,
    rms,
    slope,
)
from servo_diagnostic_model.features.electrical_features import (
    calculate_current_features,
    calculate_torque_features,
    calculate_voltage_features,
)
from servo_diagnostic_model.features.feature_extractor import extract_features
from servo_diagnostic_model.features.motion_features import (
    calculate_acceleration_features,
    calculate_velocity_features,
    detect_motion_phase,
)
from servo_diagnostic_model.features.status_features import (
    calculate_status_features,
    decode_statusword,
)
from servo_diagnostic_model.features.thermal_features import (
    calculate_temperature_features,
)


def make_window(samples, sampling_rate_hz=1.0):
    return TelemetryWindow(
        samples=samples,
        start_t=0.0,
        end_t=5.0,
        device_id="servo-1",
        sampling_rate_hz=sampling_rate_hz,
    )


def test_is_valid_number():
    assert is_valid_number(1)
    assert is_valid_number(-1.5)
    assert not is_valid_number(None)
    assert not is_valid_number(True)
    assert not is_valid_number(float("nan"))
    assert not is_valid_number(float("inf"))
    assert not is_valid_number("1")


def test_clean_values():
    values = clean_values([1, "2.5", None, "bad", float("nan"), float("inf")])

    assert values == [1.0, 2.5]


def test_rms_positive_values():
    assert rms([1, 1, 1]) == 1.0


def test_rms_negative_values():
    assert rms([-1, 1]) == 1.0


def test_rms_empty():
    assert rms([]) is None


def test_slope_linear_growth():
    assert slope([0, 1, 2], [10, 20, 30]) == 10.0


def test_velocity_features():
    window = make_window(
        [
            TelemetrySample(t=0.0, velocity=-20.0),
            TelemetrySample(t=1.0, velocity=0.0),
            TelemetrySample(t=2.0, velocity=10.0),
        ]
    )

    features = calculate_velocity_features(window)

    assert features["velocity_min"] == -20.0
    assert features["velocity_max"] == 10.0
    assert features["abs_velocity_max"] == 20.0
    assert features["velocity_rms"] == pytest.approx(math.sqrt(500 / 3))
    assert features["motion_ratio"] == pytest.approx(1 / 3)


def test_acceleration_features():
    window = make_window(
        [
            TelemetrySample(t=0.0, velocity=0.0),
            TelemetrySample(t=1.0, velocity=10.0),
            TelemetrySample(t=2.0, velocity=30.0),
        ]
    )

    features = calculate_acceleration_features(window)

    assert features["accel_mean"] == 15.0
    assert features["accel_min"] == 10.0
    assert features["accel_max"] == 20.0
    assert features["abs_accel_max"] == 20.0


def test_current_features_prefers_amperes():
    window = make_window(
        [
            TelemetrySample(t=0.0, current_A=-2.0, current=100.0),
            TelemetrySample(t=1.0, current_A=1.0, current=200.0),
        ]
    )

    features = calculate_current_features(window)

    assert features["current_unit"] == "A"
    assert features["current_mean"] == -0.5
    assert features["current_abs_max"] == 2.0
    assert features["current_rms"] == pytest.approx(math.sqrt(2.5))


def test_torque_features_falls_back_to_relative():
    window = make_window(
        [
            TelemetrySample(t=0.0, torque=-10.0),
            TelemetrySample(t=1.0, torque=20.0),
        ]
    )

    features = calculate_torque_features(window)

    assert features["torque_unit"] == "relative"
    assert features["torque_min"] == -10.0
    assert features["torque_max"] == 20.0
    assert features["torque_abs_max"] == 20.0


def test_voltage_features():
    window = make_window(
        [
            TelemetrySample(t=0.0, dc_bus_voltage=300.0),
            TelemetrySample(t=1.0, dc_bus_voltage=310.0),
        ]
    )

    features = calculate_voltage_features(window)

    assert features["voltage_mean"] == 305.0
    assert features["voltage_min"] == 300.0
    assert features["voltage_max"] == 310.0
    assert features["voltage_range"] == 10.0


def test_temperature_slope():
    window = make_window(
        [
            TelemetrySample(t=0.0, drive_temp=30.0),
            TelemetrySample(t=1.0, drive_temp=32.0),
            TelemetrySample(t=2.0, drive_temp=34.0),
        ]
    )

    features = calculate_temperature_features(window)

    assert features["temp_slope"] == 2.0
    assert features["temp_std"] > 0


def test_decode_statusword():
    decoded = decode_statusword(0x009F)

    assert decoded["statusword_available"]
    assert decoded["ready_to_switch_on"]
    assert decoded["operation_enabled"]
    assert decoded["fault"]
    assert decoded["warning"]


def test_error_flag():
    window = make_window(
        [
            TelemetrySample(t=0.0, error_code=0),
            TelemetrySample(t=1.0, error_code=42),
            TelemetrySample(t=2.0, error_code=42),
        ]
    )

    features = calculate_status_features(window)

    assert features["error_flag"]
    assert features["error_count"] == 2
    assert features["unique_error_codes"] == [42]


def test_fault_flag():
    window = make_window([TelemetrySample(t=0.0, statusword=0x0008)])

    features = calculate_status_features(window)

    assert features["fault_flag"]


def test_motion_phase_stopped():
    features = {
        "sample_count": 10,
        "abs_velocity_max": 0.5,
        "motion_ratio": 0.0,
    }

    assert detect_motion_phase(features) == "stopped"


def test_motion_phase_moving():
    features = {
        "sample_count": 10,
        "abs_velocity_max": 100.0,
        "motion_ratio": 1.0,
        "accel_mean": 0.0,
        "velocity_mean": 100.0,
        "velocity_std": 1.0,
    }

    assert detect_motion_phase(features) == "moving"


def test_extract_features_output_keys_and_missing_data_safety():
    window = make_window(
        [
            TelemetrySample(
                t=0.0,
                velocity=100.0,
                current_A=1.0,
                torque_Nm=2.0,
                dc_bus_voltage=300.0,
                drive_temp=30.0,
                statusword=0x0004,
                error_code=0,
            ),
            TelemetrySample(
                t=1.0,
                velocity=None,
                current_A=None,
                torque_Nm=2.5,
                dc_bus_voltage=301.0,
                drive_temp=31.0,
                statusword=0x000C,
                error_code=7,
            ),
        ]
    )
    required_keys = {
        "window_start",
        "window_end",
        "sample_count",
        "device_id",
        "sampling_rate_hz",
        "velocity_mean",
        "velocity_max",
        "velocity_min",
        "velocity_std",
        "velocity_rms",
        "abs_velocity_max",
        "accel_mean",
        "accel_max",
        "abs_accel_max",
        "current_mean",
        "current_max",
        "current_abs_max",
        "current_rms",
        "current_std",
        "current_unit",
        "torque_mean",
        "torque_max",
        "torque_abs_max",
        "torque_rms",
        "torque_std",
        "torque_unit",
        "voltage_mean",
        "voltage_min",
        "voltage_max",
        "voltage_std",
        "voltage_range",
        "temp_mean",
        "temp_min",
        "temp_max",
        "temp_std",
        "temp_slope",
        "error_flag",
        "error_count",
        "unique_error_codes",
        "statusword_available",
        "fault_flag",
        "warning_flag",
        "operation_enabled_ratio",
        "motion_ratio",
        "hold_ratio",
        "motion_phase",
        "missing_ratio",
        "invalid_ratio",
        "time_gap_count",
        "is_too_short",
    }

    features = extract_features(window)

    assert required_keys <= features.keys()
    assert features["error_flag"]
    assert features["fault_flag"]
    assert features["missing_ratio"] > 0
