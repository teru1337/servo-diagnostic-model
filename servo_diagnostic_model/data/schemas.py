"""Internal telemetry data structures."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TelemetrySample:
    """One normalized servo-drive telemetry sample."""

    t: float
    ts: datetime | None = None
    device_id: str | None = None
    statusword: int | None = None
    mode_display: str | None = None
    position: float | None = None
    velocity: float | None = None
    torque: float | None = None
    torque_Nm: float | None = None
    current: float | None = None
    current_A: float | None = None
    dc_bus_voltage: float | None = None
    drive_temp: float | None = None
    error_code: int | None = None


@dataclass
class TelemetryDataset:
    """Normalized telemetry and its validation metadata."""

    samples: list[TelemetrySample] = field(default_factory=list)
    columns_available: dict[str, bool] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    sampling_rate_hz: float | None = None
    duration_s: float | None = None
    device_id: str | None = None


@dataclass
class TelemetryWindow:
    """A time-bounded collection of telemetry samples."""

    samples: list[TelemetrySample]
    start_t: float
    end_t: float
    device_id: str | None = None
    sampling_rate_hz: float | None = None
