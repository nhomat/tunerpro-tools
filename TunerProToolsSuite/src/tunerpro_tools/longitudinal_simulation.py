"""Time-stepped longitudinal acceleration simulation and top-speed solver.

Every number in a SimulationSample is derived, at that instant, from the
engine curve + transmission + vehicle dynamics modules - nothing here
is a lookup table of "expected" results. Numerical safety (requirement:
never surface NaN/Infinity) is enforced by construction: forces come
from bounded physical formulas, RPM is clamped to the engine curve's
domain, and the integration loop has an explicit time/speed cutoff.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .engine_model import EngineCurve
from .transmission_model import TransmissionSpec, engine_rpm_for_speed, traction_force_n, wheel_torque_nm
from .vehicle_dynamics import VehicleSpec, acceleration_ms2, total_resistance_force_n

MS_PER_KMH = 1 / 3.6


@dataclass(frozen=True)
class SimulationSample:
    t_s: float
    speed_ms: float
    rpm: float
    gear_index: int
    acceleration_ms2: float
    engine_torque_nm: float
    engine_power_kw: float
    traction_force_n: float
    resistance_force_n: float

    @property
    def speed_kmh(self) -> float:
        return self.speed_ms / MS_PER_KMH


@dataclass(frozen=True)
class SimulationResult:
    samples: tuple[SimulationSample, ...]
    stopped_reason: str  # "top_speed_reached" | "time_limit" | "no_forward_force"

    def time_to_speed_kmh(self, target_kmh: float) -> float | None:
        target_ms = target_kmh * MS_PER_KMH
        for sample in self.samples:
            if sample.speed_ms >= target_ms:
                return sample.t_s
        return None

    def time_between_speeds_kmh(self, v0_kmh: float, v1_kmh: float) -> float | None:
        t0 = self.time_to_speed_kmh(v0_kmh)
        t1 = self.time_to_speed_kmh(v1_kmh)
        if t0 is None or t1 is None:
            return None
        return t1 - t0

    def max_speed_kmh(self) -> float:
        return max((s.speed_kmh for s in self.samples), default=0.0)


def _select_gear(
    speed_ms: float, gear_index: int, transmission: TransmissionSpec, engine: EngineCurve
) -> int:
    """Upshift when the current gear would push RPM past the engine's redline."""
    rpm = engine_rpm_for_speed(speed_ms, gear_index, transmission)
    while rpm > engine.rpm_max and gear_index < len(transmission.gears) - 1:
        gear_index += 1
        rpm = engine_rpm_for_speed(speed_ms, gear_index, transmission)
    return gear_index


def simulate_acceleration(
    engine: EngineCurve,
    transmission: TransmissionSpec,
    vehicle: VehicleSpec,
    *,
    dt_s: float = 0.02,
    max_time_s: float = 60.0,
    max_speed_kmh: float = 400.0,
    grade_percent: float = 0.0,
    launch_speed_ms: float = 0.01,
) -> SimulationResult:
    """Simulate a standing-start full-throttle run using Euler integration.

    Gear shifts happen automatically at the engine curve's rpm_max
    (see `_select_gear`); this is a disclosed, simplified shift strategy
    (shift at redline), not a claim of optimal shift points.
    """
    if dt_s <= 0:
        raise ValueError("dt_s must be positive")

    max_speed_ms = max_speed_kmh * MS_PER_KMH
    samples: list[SimulationSample] = []
    t = 0.0
    speed = launch_speed_ms
    gear_index = 0
    stopped_reason = "time_limit"
    stall_steps = 0

    while t <= max_time_s:
        gear_index = _select_gear(speed, gear_index, transmission, engine)
        rpm = engine_rpm_for_speed(speed, gear_index, transmission)
        rpm_clamped = min(max(rpm, engine.rpm_min), engine.rpm_max)

        torque = engine.torque_nm(rpm_clamped)
        power = engine.power_kw(rpm_clamped)
        wheel_torque = wheel_torque_nm(torque, gear_index, transmission)
        drive_force = traction_force_n(wheel_torque, gear_index, transmission)
        resistance = total_resistance_force_n(speed, vehicle, grade_percent)
        net_force = drive_force - resistance
        accel = acceleration_ms2(net_force, vehicle)

        samples.append(
            SimulationSample(
                t_s=round(t, 6),
                speed_ms=speed,
                rpm=rpm_clamped,
                gear_index=gear_index,
                acceleration_ms2=accel,
                engine_torque_nm=torque,
                engine_power_kw=power,
                traction_force_n=drive_force,
                resistance_force_n=resistance,
            )
        )

        if speed >= max_speed_ms:
            stopped_reason = "top_speed_reached"
            break

        if accel <= 1e-4:
            stall_steps += 1
            if stall_steps > 25 or (gear_index == len(transmission.gears) - 1 and accel <= 0):
                stopped_reason = "no_forward_force"
                break
        else:
            stall_steps = 0

        speed = max(0.0, speed + accel * dt_s)
        t += dt_s

    return SimulationResult(samples=tuple(samples), stopped_reason=stopped_reason)


def theoretical_top_speed_kmh(
    engine: EngineCurve, transmission: TransmissionSpec, vehicle: VehicleSpec, *, grade_percent: float = 0.0
) -> tuple[float | None, str]:
    """Find where traction force in the highest gear equals total resistance.

    Returns (top_speed_kmh, note). `top_speed_kmh` is None only when no
    speed in the engine's RPM range produces enough traction to overcome
    resistance at all (never a fabricated fallback number).
    """
    top_gear = len(transmission.gears) - 1
    rpm_values = [engine.rpm_min + i * (engine.rpm_max - engine.rpm_min) / 400 for i in range(401)]

    best_speed_ms = 0.0
    ever_exceeded = False
    for rpm in rpm_values:
        speed_ms = _speed_for_rpm(rpm, top_gear, transmission)
        torque = engine.torque_nm(rpm)
        wheel_torque = wheel_torque_nm(torque, top_gear, transmission)
        drive_force = traction_force_n(wheel_torque, top_gear, transmission)
        resistance = total_resistance_force_n(speed_ms, vehicle, grade_percent)
        if drive_force >= resistance:
            ever_exceeded = True
            best_speed_ms = max(best_speed_ms, speed_ms)

    if not ever_exceeded:
        return None, "Aucun regime du rapport le plus long ne fournit assez de force motrice : vitesse maximale indeterminee avec ces donnees."

    note = "Vitesse maximale limitee par l'equilibre force motrice / resistance dans le rapport le plus long."
    return round(best_speed_ms / MS_PER_KMH, 2), note


def _speed_for_rpm(rpm: float, gear_index: int, transmission: TransmissionSpec) -> float:
    from .transmission_model import speed_for_engine_rpm

    return speed_for_engine_rpm(rpm, gear_index, transmission)
