import json
from pathlib import Path

import pytest

from servo_diagnostic_model.model.physical_risks import (
    calculate_current_risk,
    calculate_data_quality_risk,
    calculate_error_risk,
    calculate_physical_risks,
    calculate_statusword_risk,
    calculate_temperature_risk,
    calculate_torque_risk,
    calculate_velocity_risk,
    calculate_voltage_risk,
    clamp,
    inverse_linear_risk,
    linear_risk,
    safe_divide,
)


@pytest.fixture
def limits():
    path = Path("servo_diagnostic_model/config/limits.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_clamp():
    assert clamp(-1.0) == 0.0
    assert clamp(0.5) == 0.5
    assert clamp(2.0) == 1.0


def test_safe_divide():
    assert safe_divide(6.0, 3.0) == 2.0
    assert safe_divide(1.0, 0.0, default=0.25) == 0.25
    assert safe_divide(None, 2.0, default=0.25) == 0.25
    assert safe_divide(1.0, float("nan"), default=0.25) == 0.25


def test_linear_risk():
    assert linear_risk(50.0, 50.0, 100.0) == 0.0
    assert linear_risk(75.0, 50.0, 100.0) == 0.5
    assert linear_risk(100.0, 50.0, 100.0) == 1.0


def test_inverse_linear_risk():
    assert inverse_linear_risk(300.0, 300.0, 200.0) == 0.0
    assert inverse_linear_risk(250.0, 300.0, 200.0) == 0.5
    assert inverse_linear_risk(200.0, 300.0, 200.0) == 1.0


def test_current_risk_normal():
    features = {"current_rms": 1.0, "current_abs_max": 2.0, "current_unit": "A"}
    limits = {"rated_current_A": 4.0, "max_current_A": 8.0}

    assert calculate_current_risk(features, limits) == 0.25


def test_current_risk_clamped():
    features = {
        "current_rms": 100.0,
        "current_abs_max": 200.0,
        "current_unit": "A",
    }
    limits = {"rated_current_A": 4.0, "max_current_A": 8.0}

    assert calculate_current_risk(features, limits) == 1.0


def test_torque_risk_normal():
    features = {"torque_rms": 1.0, "torque_abs_max": 2.0, "torque_unit": "Nm"}
    limits = {"rated_torque_Nm": 4.0, "max_torque_Nm": 10.0}

    assert calculate_torque_risk(features, limits) == 0.25


def test_velocity_risk_normal():
    assert calculate_velocity_risk(
        {"abs_velocity_max": 3000.0}, {"max_velocity_rpm": 6000.0}
    ) == 0.5


def test_voltage_low_risk():
    features = {"voltage_min": 260.0, "voltage_max": 300.0, "voltage_std": 0.0}
    limits = {
        "dc_bus_min_safe": 280.0,
        "dc_bus_min_critical": 240.0,
        "dc_bus_max_safe": 340.0,
        "dc_bus_max_critical": 380.0,
        "voltage_std_limit": 5.0,
    }

    assert calculate_voltage_risk(features, limits) == 0.5


def test_voltage_high_risk():
    features = {"voltage_min": 300.0, "voltage_max": 360.0, "voltage_std": 0.0}
    limits = {
        "dc_bus_min_safe": 280.0,
        "dc_bus_min_critical": 240.0,
        "dc_bus_max_safe": 340.0,
        "dc_bus_max_critical": 380.0,
        "voltage_std_limit": 5.0,
    }

    assert calculate_voltage_risk(features, limits) == 0.5


def test_voltage_unstable_risk():
    features = {"voltage_min": 300.0, "voltage_max": 310.0, "voltage_std": 4.0}
    limits = {
        "dc_bus_min_safe": 280.0,
        "dc_bus_min_critical": 240.0,
        "dc_bus_max_safe": 340.0,
        "dc_bus_max_critical": 380.0,
        "voltage_std_limit": 5.0,
    }

    assert calculate_voltage_risk(features, limits) == 0.8


def test_temperature_safe():
    features = {"temp_max": 50.0, "temp_slope": 0.0}
    limits = {"temp_safe": 55.0, "temp_critical": 85.0, "temp_slope_limit": 0.2}

    assert calculate_temperature_risk(features, limits) == 0.0


def test_temperature_critical():
    features = {"temp_max": 90.0, "temp_slope": 0.0}
    limits = {"temp_safe": 55.0, "temp_critical": 85.0, "temp_slope_limit": 0.2}

    assert calculate_temperature_risk(features, limits) == 1.0


def test_temperature_slope_risk():
    features = {"temp_max": 50.0, "temp_slope": 0.1}
    limits = {"temp_safe": 55.0, "temp_critical": 85.0, "temp_slope_limit": 0.2}

    assert calculate_temperature_risk(features, limits) == 0.5


def test_error_risk():
    assert calculate_error_risk({"error_flag": True}) == 1.0
    assert calculate_error_risk({"error_flag": False}) == 0.0


def test_statusword_fault_risk():
    assert calculate_statusword_risk(
        {"statusword_available": True, "fault_flag": True}
    ) == 1.0


def test_statusword_warning_risk():
    assert calculate_statusword_risk(
        {"statusword_available": True, "fault_flag": False, "warning_flag": True}
    ) == 0.6


def test_data_quality_risk():
    features = {
        "missing_ratio": 0.15,
        "invalid_ratio": 0.0,
        "time_gap_count": 0,
        "is_too_short": False,
        "current_rms": 1.0,
        "torque_rms": 1.0,
        "abs_velocity_max": 1.0,
        "voltage_min": 300.0,
        "temp_max": 30.0,
        "statusword_available": True,
        "error_flag": False,
    }
    limits = {
        "missing_ratio_limit": 0.3,
        "invalid_ratio_limit": 0.2,
        "time_gap_count_limit": 3,
    }

    assert calculate_data_quality_risk(features, limits) == 0.5


def test_missing_statusword_increases_data_quality_risk():
    features = {
        "current_rms": 1.0,
        "torque_rms": 1.0,
        "abs_velocity_max": 1.0,
        "voltage_min": 300.0,
        "temp_max": 30.0,
        "statusword_available": False,
        "error_flag": False,
    }

    assert calculate_data_quality_risk(features, {}) > 0.0


def test_missing_feature_safety():
    risks = calculate_physical_risks({}, {})

    assert risks["current"] == 0.0
    assert risks["torque"] == 0.0
    assert risks["velocity"] == 0.0
    assert risks["voltage"] == 0.0
    assert risks["temperature"] == 0.0
    assert risks["data_quality"] == 1.0


def test_calculate_physical_risks_returns_required_keys(limits):
    risks = calculate_physical_risks({}, limits)

    assert set(risks) == {
        "current",
        "torque",
        "velocity",
        "voltage",
        "temperature",
        "statusword",
        "error",
        "data_quality",
        "statistical_anomaly",
    }


def test_all_returned_risks_are_in_range(limits):
    features = {
        "current_rms": 1e9,
        "current_abs_max": 1e9,
        "current_unit": "A",
        "torque_rms": 1e9,
        "torque_abs_max": 1e9,
        "torque_unit": "Nm",
        "abs_velocity_max": 1e9,
        "voltage_min": -1e9,
        "voltage_max": 1e9,
        "voltage_std": 1e9,
        "temp_max": 1e9,
        "temp_slope": 1e9,
        "error_flag": True,
        "statusword_available": True,
        "fault_flag": True,
        "missing_ratio": 1e9,
        "invalid_ratio": 1e9,
        "time_gap_count": 1e9,
        "is_too_short": True,
    }

    risks = calculate_physical_risks(features, limits)

    assert all(0.0 <= risk <= 1.0 for risk in risks.values())
