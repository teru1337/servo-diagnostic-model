"""Numeric checks shared by scoring and explanations."""

import math
from numbers import Real


def is_finite_number(value: object) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def bounded_risk(value: object) -> float:
    if not is_finite_number(value):
        return 0.0
    return min(max(float(value), 0.0), 1.0)
