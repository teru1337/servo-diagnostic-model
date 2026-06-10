import json

import pytest

from servo_diagnostic_model.model.anomaly_score import (
    calculate_anomaly_score,
    robust_feature_score,
    select_profile_for_phase,
)
from servo_diagnostic_model.model.statistical_profile import (
    calculate_feature_stats,
    calculate_mad,
    filter_normal_feature_rows,
    fit_normal_profile,
    infer_numeric_feature_names,
    load_profile,
    save_profile,
)


def _rows():
    return [
        {
            "motion_phase": "holding" if index < 5 else "moving",
            "current_rms": 1.0 + index * 0.1,
            "voltage_std": 0.2 + index * 0.01,
            "error_flag": False,
            "fault_flag": False,
            "missing_ratio": 0.0,
            "invalid_ratio": 0.0,
        }
        for index in range(10)
    ]


def test_calculate_mad():
    assert calculate_mad([1, 1, 2, 2, 100]) == 1.0
    assert calculate_mad([1, 1, 1]) == 0.0


def test_calculate_feature_stats():
    stats = calculate_feature_stats([1, 2, 3])

    assert stats["median"] == 2.0
    assert stats["mad"] == 1.0
    assert stats["mean"] == 2.0
    assert stats["count"] == 3


def test_infer_numeric_feature_names_excludes_flags_and_service_fields():
    names = infer_numeric_feature_names(_rows())

    assert names == ["current_rms", "voltage_std"]


def test_fit_normal_profile_creates_global_profile():
    profile = fit_normal_profile(_rows(), min_count=5)

    assert "current_rms" in profile["global"]
    assert profile["global"]["current_rms"]["count"] == 10


def test_fit_normal_profile_creates_by_motion_phase_profile():
    profile = fit_normal_profile(_rows(), min_count=5)

    assert "holding" in profile["by_motion_phase"]
    assert "moving" in profile["by_motion_phase"]
    assert profile["by_motion_phase"]["holding"]["current_rms"]["count"] == 5


def test_filter_normal_feature_rows():
    rows = _rows() + [
        {"current_rms": 99.0, "error_flag": True},
        {"current_rms": 99.0, "fault_flag": True},
        {"current_rms": 99.0, "missing_ratio": 0.2},
    ]

    assert len(filter_normal_feature_rows(rows)) == 10


def test_save_profile_and_load_profile(tmp_path):
    profile = fit_normal_profile(_rows(), min_count=5)
    path = tmp_path / "profile.json"

    save_profile(profile, str(path))

    assert load_profile(str(path)) == profile


def test_robust_feature_score_returns_zero_at_median():
    stats = {"median": 10.0, "mad": 2.0, "std": 3.0}

    assert robust_feature_score(10.0, stats) == 0.0


def test_robust_feature_score_clamps_high_anomaly():
    stats = {"median": 10.0, "mad": 1.0, "std": 1.0}

    assert robust_feature_score(100.0, stats) == 1.0


def test_robust_feature_score_handles_zero_mad():
    stats = {"median": 10.0, "mad": 0.0, "std": 2.0}

    assert robust_feature_score(12.0, stats, z_limit=5.0) == pytest.approx(0.2)
    assert robust_feature_score(10.0, {"median": 10.0, "mad": 0.0, "std": 0.0}) == 0.0


def test_calculate_anomaly_score_with_no_profile():
    result = calculate_anomaly_score({"current_rms": 1.0})

    assert result == {
        "anomaly_score": 0.0,
        "feature_scores": {},
        "profile_used": None,
        "available": False,
    }


def test_calculate_anomaly_score_with_global_profile():
    profile = {"global": {"current_rms": {"median": 1.0, "mad": 0.1, "std": 0.1}}}

    result = calculate_anomaly_score({"current_rms": 1.5}, profile)

    assert result["profile_used"] == "global"
    assert result["available"] is True
    assert result["anomaly_score"] == pytest.approx(1.0)


def test_calculate_anomaly_score_with_phase_profile():
    profile = {
        "global": {"current_rms": {"median": 1.0, "mad": 1.0}},
        "by_motion_phase": {
            "holding": {"current_rms": {"median": 5.0, "mad": 1.0}}
        },
    }

    result = calculate_anomaly_score(
        {"motion_phase": "holding", "current_rms": 5.0},
        profile,
    )

    assert result["profile_used"] == "by_motion_phase.holding"
    assert result["anomaly_score"] == 0.0


def test_fallback_from_missing_phase_profile_to_global():
    profile = {
        "global": {"current_rms": {"median": 1.0, "mad": 1.0}},
        "by_motion_phase": {},
    }

    selected, name = select_profile_for_phase(profile, "moving")

    assert selected == profile["global"]
    assert name == "global"


def test_anomaly_result_is_json_serializable():
    profile = {"global": {"current_rms": {"median": 1.0, "mad": 0.1}}}

    json.dumps(calculate_anomaly_score({"current_rms": 1.5}, profile))
