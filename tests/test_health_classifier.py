import json
from pathlib import Path

import pytest

from servo_diagnostic_model.model.classifier import (
    classify_state,
    has_risk_above,
    risk_level_from_state,
)
from servo_diagnostic_model.model.explanation import (
    generate_explanation,
    get_main_causes,
    severity_from_risk,
)
from servo_diagnostic_model.model.health_score import (
    apply_hard_limits,
    calculate_health_score,
)


@pytest.fixture
def weights():
    return json.loads(
        Path("servo_diagnostic_model/config/weights.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def thresholds():
    return json.loads(
        Path("servo_diagnostic_model/config/thresholds.json").read_text(
            encoding="utf-8"
        )
    )


def test_health_score_all_zero_risks(weights):
    risks = {key: 0.0 for key in weights}

    assert calculate_health_score(risks, weights) == 100.0


def test_health_score_all_one_risks(weights):
    risks = {key: 1.0 for key in weights}

    assert calculate_health_score(risks, weights) == pytest.approx(0.0)


def test_health_score_range_clamp():
    assert calculate_health_score({"current": -100.0}, {"current": 1.0}) == 100.0
    assert calculate_health_score({"current": 100.0}, {"current": 1.0}) == 0.0


def test_missing_weight_safety():
    score = calculate_health_score(
        {"current": 0.5, "temperature": 1.0},
        {"current": 1.0},
    )

    assert score == 50.0


def test_hard_limit_by_error_flag():
    assert apply_hard_limits(100.0, {}, {"error_flag": True}) == 40.0


def test_hard_limit_by_fault_flag():
    assert apply_hard_limits(100.0, {}, {"fault_flag": True}) == 40.0


def test_hard_limit_by_temperature_risk():
    assert apply_hard_limits(100.0, {"temperature": 1.0}, {}) == 50.0


def test_hard_limit_by_voltage_risk():
    assert apply_hard_limits(100.0, {"voltage": 1.0}, {}) == 50.0


def test_hard_limit_by_data_quality_risk():
    assert apply_hard_limits(100.0, {"data_quality": 1.0}, {}) == 60.0


def test_classifier_normal(thresholds):
    assert classify_state(95.0, 0.1, {}, thresholds, {}) == "normal"


def test_classifier_observation(thresholds):
    assert classify_state(80.0, 0.1, {}, thresholds, {}) == "observation"


def test_classifier_warning(thresholds):
    assert classify_state(60.0, 0.1, {}, thresholds, {}) == "warning"


def test_classifier_critical_by_health_score(thresholds):
    assert classify_state(40.0, 0.1, {}, thresholds, {}) == "critical"


def test_classifier_critical_by_error_flag(thresholds):
    assert classify_state(95.0, 0.1, {}, thresholds, {"error_flag": True}) == "critical"


def test_classifier_critical_by_fault_flag(thresholds):
    assert classify_state(95.0, 0.1, {}, thresholds, {"fault_flag": True}) == "critical"


def test_classifier_critical_by_anomaly_score(thresholds):
    assert classify_state(95.0, 0.8, {}, thresholds, {}) == "critical"


def test_classifier_critical_by_error_risk(thresholds):
    assert classify_state(95.0, 0.1, {"error": 1.0}, thresholds, {}) == "critical"


def test_classifier_critical_by_statusword_risk(thresholds):
    assert classify_state(95.0, 0.1, {"statusword": 1.0}, thresholds, {}) == "critical"


def test_has_risk_above_with_exclusion():
    risks = {"current": 0.8, "data_quality": 1.0}

    assert has_risk_above(risks, 0.75)
    assert not has_risk_above(risks, 0.9, exclude=["data_quality"])


@pytest.mark.parametrize(
    ("state", "risk_level"),
    [
        ("normal", "low"),
        ("observation", "medium"),
        ("warning", "high"),
        ("critical", "critical"),
        ("unknown", "unknown"),
        ("invalid", "unknown"),
    ],
)
def test_risk_level_from_state(state, risk_level):
    assert risk_level_from_state(state) == risk_level


@pytest.mark.parametrize(
    ("risk", "severity"),
    [
        (0.0, "low"),
        (0.3, "observation"),
        (0.5, "warning"),
        (0.75, "critical"),
        (5.0, "critical"),
    ],
)
def test_severity_from_risk(risk, severity):
    assert severity_from_risk(risk) == severity


def test_get_main_causes_selects_top_risks():
    causes = get_main_causes(
        {"current": 0.8, "temperature": 0.6, "voltage": 0.2},
        {},
        top_n=3,
        min_risk=0.3,
    )

    assert [cause["risk_key"] for cause in causes] == ["current", "temperature"]
    assert causes[0]["severity"] == "critical"


@pytest.mark.parametrize(
    "state", ["normal", "observation", "warning", "critical", "unknown"]
)
def test_generate_explanation_returns_non_empty_list_for_each_state(state):
    causes = get_main_causes({"current": 0.8}, {})

    explanation = generate_explanation(
        state,
        health_score=75.0,
        anomaly_score=0.2,
        risks={"current": 0.8},
        features={},
        main_causes=causes,
    )

    assert explanation
    assert all(isinstance(message, str) and message for message in explanation)
