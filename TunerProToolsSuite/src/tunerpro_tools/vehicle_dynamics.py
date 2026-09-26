"""Longitudinal forces acting on the vehicle: drag, rolling resistance, grade.

Standard textbook vehicle-dynamics equations - nothing here is specific
to any make/model; every function takes exactly the physical parameters
it needs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .data_provenance import DataSource

STANDARD_AIR_DENSITY_KG_M3 = 1.225
STANDARD_GRAVITY_M_S2 = 9.81

#: A typical passenger-car rolling resistance coefficient, used only as
#: a disclosed ESTIMATED default when the user has no better number -
#: never presented as measured.
DEFAULT_ROLLING_RESISTANCE_COEFFICIENT = 0.015


@dataclass
class VehicleSpec:
    mass_kg: float
    drag_coefficient: float  # Cx
    frontal_area_m2: float
    rolling_resistance_coefficient: float = DEFAULT_ROLLING_RESISTANCE_COEFFICIENT
    air_density_kg_m3: float = STANDARD_AIR_DENSITY_KG_M3
    make: str | None = None
    model: str | None = None
    year: int | None = None
    version: str | None = None
    body_type: str | None = None
    sources: dict[str, DataSource] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mass_kg <= 0:
            raise ValueError("mass_kg must be positive")
        if self.drag_coefficient <= 0:
            raise ValueError("drag_coefficient must be positive")
        if self.frontal_area_m2 <= 0:
            raise ValueError("frontal_area_m2 must be positive")

    def source_of(self, field_name: str) -> DataSource:
        return self.sources.get(field_name, DataSource.UNKNOWN)


def aerodynamic_drag_force_n(speed_ms: float, vehicle: VehicleSpec) -> float:
    """F_drag = 0.5 * rho * Cx * A * v^2."""
    return 0.5 * vehicle.air_density_kg_m3 * vehicle.drag_coefficient * vehicle.frontal_area_m2 * speed_ms ** 2


def rolling_resistance_force_n(vehicle: VehicleSpec, g: float = STANDARD_GRAVITY_M_S2) -> float:
    """F_roll = Crr * m * g (assumed speed-independent, the standard first-order model)."""
    return vehicle.rolling_resistance_coefficient * vehicle.mass_kg * g


def grade_force_n(vehicle: VehicleSpec, grade_percent: float, g: float = STANDARD_GRAVITY_M_S2) -> float:
    """Force opposing motion up a slope of `grade_percent` (rise/run * 100)."""
    angle = math.atan(grade_percent / 100)
    return vehicle.mass_kg * g * math.sin(angle)


def total_resistance_force_n(speed_ms: float, vehicle: VehicleSpec, grade_percent: float = 0.0) -> float:
    return (
        aerodynamic_drag_force_n(speed_ms, vehicle)
        + rolling_resistance_force_n(vehicle)
        + grade_force_n(vehicle, grade_percent)
    )


def acceleration_ms2(net_force_n: float, vehicle: VehicleSpec) -> float:
    return net_force_n / vehicle.mass_kg
