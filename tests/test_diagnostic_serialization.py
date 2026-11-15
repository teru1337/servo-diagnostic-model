"""Check the JSON boundary for diagnostic feature values."""

from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path

from servo_diagnostic_model.api.diagnostic_service import _to_json_compatible


def test_json_boundary_preserves_nested_values_and_normalizes_special_types():
    @dataclass
    class Reading:
        time: datetime
        value: float

    value = {1: [Reading(datetime(2026, 1, 1), float("inf")),
                 (date(2026, 1, 1), Path("profile.json"), True, None, 2, 2.5)]}
    safe = _to_json_compatible(value)
    assert safe == {"1": [{"time": "2026-01-01T00:00:00", "value": None},
                          ["2026-01-01", "profile.json", True, None, 2, 2.5]]}
    assert type(safe["1"][1][4]) is int
    assert json.loads(json.dumps(safe, allow_nan=False)) == safe
