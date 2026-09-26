"""Gear ratios and the RPM <-> wheel speed relationship.

Pure kinematics: engine_omega = wheel_omega * gear_ratio * final_drive.
No assumption about the engine or vehicle beyond what's passed in.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .data_provenance import DataSource


@dataclass
class Gear:
    ratio: float
    efficiency: float = 0.95  # driveline mechanical efficiency for this gear, 0..1
    wheel_radius_m: float | None = None  # overrides TransmissionSpec.wheel_radius_m if set

    def __post_init__(self) -> None:
        if self.ratio <= 0:
            raise ValueError("gear ratio must be positive")
        if not (0 < self.efficiency <= 1):
            raise ValueError("efficiency must be in (0, 1]")


@dataclass
class TransmissionSpec:
    gears: list[Gear]
    final_drive_ratio: float
    wheel_radius_m: float
    sources: dict[str, DataSource] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.gears:
            raise ValueError("at least one gear is required")
        if self.final_drive_ratio <= 0:
            raise ValueError("final_drive_ratio must be positive")
        if self.wheel_radius_m <= 0:
            raise ValueError("wheel_radius_m must be positive")

    def wheel_radius_for(self, gear_index: int) -> float:
        gear = self.gears[gear_index]
        return gear.wheel_radius_m if gear.wheel_radius_m is not None else self.wheel_radius_m


def engine_rpm_for_speed(speed_ms: float, gear_index: int, transmission: TransmissionSpec) -> float:
    """RPM the engine turns at for a given road speed, in `gear_index`."""
    wheel_radius = transmission.wheel_radius_for(gear_index)
    wheel_omega = speed_ms / wheel_radius
    engine_omega = wheel_omega * transmission.gears[gear_index].ratio * transmission.final_drive_ratio
    return engine_omega * 60 / (2 * math.pi)


def speed_for_engine_rpm(rpm: float, gear_index: int, transmission: TransmissionSpec) -> float:
    """Inverse of engine_rpm_for_speed: road speed (m/s) at a given engine RPM."""
    wheel_radius = transmission.wheel_radius_for(gear_index)
    engine_omega = rpm * 2 * math.pi / 60
    wheel_omega = engine_omega / (transmission.gears[gear_index].ratio * transmission.final_drive_ratio)
    return wheel_omega * wheel_radius


def wheel_torque_nm(engine_torque_nm: float, gear_index: int, transmission: TransmissionSpec) -> float:
    """Torque delivered at the wheel, after gear/final-drive multiplication and driveline losses."""
    gear = transmission.gears[gear_index]
    return engine_torque_nm * gear.ratio * transmission.final_drive_ratio * gear.efficiency


def traction_force_n(wheel_torque_nm_value: float, gear_index: int, transmission: TransmissionSpec) -> float:
    """Force at the contact patch (N) from wheel torque and wheel radius."""
    return wheel_torque_nm_value / transmission.wheel_radius_for(gear_index)
