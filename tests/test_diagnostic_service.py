import json
from pathlib import Path

from servo_diagnostic_model.api.diagnostic_service import (
    diagnose_csv,
    diagnose_dataset,
    diagnose_window,
    load_json_config,
)
from servo_diagnostic_model.api.schemas import REQUIRED_RESULT_FIELDS
from servo_diagnostic_model.data.schemas import (
    TelemetryDataset,
    TelemetrySample,
    TelemetryWindow,
)
from servo_diagnostic_model.data.windowing import estimate_sampling_rate


CONFIG_DIR = Path("servo_diagnostic_model/config")


def _configs():
    return (
        load_json_config(str(CONFIG_DIR / "limits.json")),
        load_json_config(str(CONFIG_DIR / "weights.json")),
        load_json_config(str(CONFIG_DIR / "thresholds.json")),
    )


def _samples(error_code=0):
    return [
        TelemetrySample(
            t=index / 10,
            device_id="servo-1",
            statusword=4,
            velocity=100.0,
            torque_Nm=0.5,
            current_A=1.0,
            dc_bus_voltage=310.0,
            drive_temp=35.0,
            error_code=error_code if index == 20 else 0,
        )
        for index in range(61)
    ]


def _window(error_code=0):
    samples = _samples(error_code)[:50]
    return TelemetryWindow(
        samples=samples,
        start_t=0.0,
        end_t=5.0,
        device_id="servo-1",
        sampling_rate_hz=estimate_sampling_rate(samples),
    )


def test_diagnose_window_returns_required_json_fields():
    result = diagnose_window(_window(), *_configs())

    assert REQUIRED_RESULT_FIELDS <= result.keys()


def test_diagnose_window_normal_is_not_critical():
    result = diagnose_window(_window(), *_configs())

    assert result["state"] != "critical"


def test_diagnose_window_with_error_code_is_critical():
    result = diagnose_window(_window(error_code=42), *_configs())

    assert result["state"] == "critical"


def test_diagnose_dataset_returns_window_results():
    samples = _samples()
    dataset = TelemetryDataset(samples=samples, device_id="servo-1")

    results = diagnose_dataset(dataset, *_configs())

    assert results
    assert all(REQUIRED_RESULT_FIELDS <= result.keys() for result in results)


def test_diagnose_csv_works_with_small_csv(tmp_path):
    csv_path = tmp_path / "telemetry.csv"
    rows = [
        "t,device_id,statusword,velocity,current_A,torque_Nm,dc_bus_voltage,drive_temp,error_code"
    ]
    rows.extend(
        f"{index / 10},servo-1,4,100,1,0.5,310,35,0" for index in range(61)
    )
    csv_path.write_text("\n".join(rows), encoding="utf-8")

    results = diagnose_csv(
        str(csv_path),
        str(CONFIG_DIR / "limits.json"),
        str(CONFIG_DIR / "weights.json"),
        str(CONFIG_DIR / "thresholds.json"),
    )

    assert results


def test_diagnostic_result_is_json_serializable():
    result = diagnose_window(_window(), *_configs())

    json.dumps(result)


def test_recommendations_exists_and_is_list():
    result = diagnose_window(_window(), *_configs())

    assert isinstance(result["recommendations"], list)
    assert result["recommendations"]
    assert result["recommendations"][0]["category"] == "normal_operation"


def test_error_window_returns_critical_recommendation():
    result = diagnose_window(_window(error_code=42), *_configs())

    assert any(
        recommendation["category"] == "drive_error"
        and recommendation["priority"] == "critical"
        for recommendation in result["recommendations"]
    )


def test_anomaly_score_is_zero_without_normal_profile():
    result = diagnose_window(_window(), *_configs())

    assert result["anomaly_score"] == 0.0
    assert result["debug"]["anomaly"]["available"] is False
