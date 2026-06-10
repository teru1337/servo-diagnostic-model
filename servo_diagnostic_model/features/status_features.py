"""CiA 402 statusword and error-code features."""

from typing import Any

from servo_diagnostic_model.data.schemas import TelemetryWindow

from .basic_features import is_valid_number


def decode_statusword(statusword: int | None) -> dict[str, bool]:
    if not is_valid_number(statusword):
        return {
            "statusword_available": False,
            "ready_to_switch_on": False,
            "switched_on": False,
            "operation_enabled": False,
            "fault": False,
            "voltage_enabled": False,
            "warning": False,
        }
    value = int(statusword)
    return {
        "statusword_available": True,
        "ready_to_switch_on": bool(value & 0x0001),
        "switched_on": bool(value & 0x0002),
        "operation_enabled": bool(value & 0x0004),
        "fault": bool(value & 0x0008),
        "voltage_enabled": bool(value & 0x0010),
        "warning": bool(value & 0x0080),
    }


def calculate_status_features(window: TelemetryWindow) -> dict[str, Any]:
    decoded = [
        decode_statusword(sample.statusword)
        for sample in window.samples
        if is_valid_number(sample.statusword)
    ]
    nonzero_errors = [
        int(sample.error_code)
        for sample in window.samples
        if is_valid_number(sample.error_code) and int(sample.error_code) != 0
    ]
    return {
        "error_flag": bool(nonzero_errors),
        "error_count": len(nonzero_errors),
        "unique_error_codes": sorted(set(nonzero_errors)),
        "statusword_available": bool(decoded),
        "fault_flag": any(item["fault"] for item in decoded),
        "warning_flag": any(item["warning"] for item in decoded),
        "operation_enabled_ratio": (
            sum(item["operation_enabled"] for item in decoded) / len(decoded)
            if decoded
            else None
        ),
        "fault_count": sum(item["fault"] for item in decoded),
        "warning_count": sum(item["warning"] for item in decoded),
    }
