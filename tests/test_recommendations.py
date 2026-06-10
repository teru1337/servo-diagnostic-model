import json

from servo_diagnostic_model.recommendations.rule_based import (
    deduplicate_recommendations,
    generate_recommendations,
    limit_recommendations,
    make_recommendation,
    sort_recommendations,
)


REQUIRED_FIELDS = {
    "priority",
    "category",
    "action",
    "reason",
    "source_risks",
    "target_role",
}


def _generate(state="warning", risks=None, features=None, thresholds=None):
    return generate_recommendations(
        state,
        risks or {},
        features or {},
        [],
        thresholds,
    )


def _find(recommendations, category):
    return next(item for item in recommendations if item["category"] == category)


def test_normal_recommendation():
    recommendations = _generate(state="normal")

    assert recommendations[0]["priority"] == "low"
    assert recommendations[0]["category"] == "normal_operation"
    assert REQUIRED_FIELDS <= recommendations[0].keys()


def test_unknown_data_quality_recommendation():
    recommendation = _find(_generate(state="unknown"), "data_quality")

    assert recommendation["priority"] == "high"
    assert recommendation["is_blocking"] is True


def test_reduced_data_quality_recommendation():
    recommendation = _find(
        _generate(risks={"data_quality": 0.5}),
        "data_quality",
    )

    assert recommendation["priority"] == "medium"
    assert recommendation["target_role"] == "admin"


def test_error_recommendation():
    recommendation = _find(
        _generate(risks={"error": 1.0}, features={"unique_error_codes": [42]}),
        "drive_error",
    )

    assert recommendation["priority"] == "critical"
    assert "42" in recommendation["reason"]


def test_fault_recommendation():
    recommendation = _find(
        _generate(features={"fault_flag": True}),
        "statusword_fault",
    )

    assert recommendation["priority"] == "critical"


def test_warning_flag_recommendation():
    recommendation = _find(
        _generate(features={"warning_flag": True}),
        "statusword_fault",
    )

    assert recommendation["priority"] == "high"


def test_voltage_recommendation():
    recommendation = _find(
        _generate(risks={"voltage": 0.75}),
        "power_supply",
    )

    assert "DC bus" in recommendation["action"]


def test_temperature_critical_recommendation():
    recommendation = _find(
        _generate(risks={"temperature": 0.75}),
        "thermal",
    )

    assert recommendation["priority"] == "high"
    assert "cooling" in recommendation["action"]


def test_temperature_observation_recommendation():
    recommendation = _find(
        _generate(risks={"temperature": 0.5}),
        "thermal",
    )

    assert recommendation["priority"] == "medium"
    assert "trend" in recommendation["action"]


def test_mechanical_current_and_torque_recommendation():
    recommendation = _find(
        _generate(risks={"current": 0.8, "torque": 0.9}),
        "mechanical_load",
    )

    assert recommendation["source_risks"] == ["current", "torque"]
    assert "jamming" in recommendation["action"]


def test_statistical_anomaly_recommendation():
    recommendation = _find(
        _generate(risks={"statistical_anomaly": 0.75}),
        "statistical_anomaly",
    )

    assert recommendation["priority"] == "high"
    assert "features" in recommendation["action"]


def test_statistical_anomaly_observation_recommendation():
    recommendation = _find(
        _generate(risks={"statistical_anomaly": 0.5}),
        "statistical_anomaly",
    )

    assert recommendation["priority"] == "medium"
    assert "trend" in recommendation["action"]


def test_velocity_recommendation():
    recommendation = _find(
        _generate(risks={"velocity": 0.75}),
        "motion_instability",
    )

    assert "speed profile" in recommendation["action"]


def test_recommendation_sorting_by_priority():
    recommendations = [
        make_recommendation("low", "normal_operation", "a", "a", [], "operator"),
        make_recommendation("critical", "drive_error", "b", "b", ["error"], "engineer"),
        make_recommendation("medium", "thermal", "c", "c", ["temperature"], "operator"),
        make_recommendation("high", "power_supply", "d", "d", ["voltage"], "engineer"),
    ]

    sorted_recommendations = sort_recommendations(recommendations)

    assert [item["priority"] for item in sorted_recommendations] == [
        "critical",
        "high",
        "medium",
        "low",
    ]


def test_recommendation_limiting():
    recommendations = _generate(
        risks={
            "error": 1.0,
            "statusword": 1.0,
            "voltage": 1.0,
            "temperature": 1.0,
        },
        thresholds={"max_recommendations": 2},
    )

    assert len(recommendations) == 2


def test_recommendation_deduplication():
    recommendations = [
        make_recommendation(
            "high", "mechanical_load", "a", "a", ["current"], "engineer"
        ),
        make_recommendation(
            "high", "mechanical_load", "b", "b", ["torque"], "engineer"
        ),
    ]

    deduplicated = deduplicate_recommendations(recommendations)

    assert len(deduplicated) == 1
    assert deduplicated[0]["source_risks"] == ["current", "torque"]


def test_recommendations_are_json_serializable():
    recommendations = _generate(
        risks={"voltage": 0.8, "temperature": 0.8, "data_quality": 0.6}
    )

    json.dumps(recommendations)


def test_limit_recommendations_helper():
    recommendations = [{"category": str(index)} for index in range(4)]

    assert limit_recommendations(recommendations, max_count=2) == recommendations[:2]
