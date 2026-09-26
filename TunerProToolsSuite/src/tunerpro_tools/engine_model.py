"""Engine torque/power model built from disclosed characteristic points.

No shape is invented: the torque-vs-RPM curve is a monotone cubic
spline (see interpolation.py) through exactly the points the caller
provides (typically: idle, peak torque, peak power converted to a
torque value, redline). Between those points the curve is a disclosed
mathematical model, not a measurement - every EngineModel carries the
source of each defining point and an overall `model_confidence` that
drops when points are estimated rather than known.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .data_provenance import SOURCE_WEIGHT, DataSource
from .interpolation import MonotoneCubicSpline, build_monotone_cubic_spline

CH_PER_KW = 1.35962  # metric horsepower per kilowatt


def power_kw_from_torque_nm(torque_nm: float, rpm: float) -> float:
    """P(kW) = T(N.m) * omega(rad/s) / 1000, omega = rpm * 2*pi/60."""
    return torque_nm * rpm * 2 * math.pi / 60 / 1000


def torque_nm_from_power_kw(power_kw: float, rpm: float) -> float:
    if rpm <= 0:
        raise ValueError("rpm must be positive")
    return power_kw * 1000 / (rpm * 2 * math.pi / 60)


def kw_to_ch(power_kw: float) -> float:
    return power_kw * CH_PER_KW


def ch_to_kw(power_ch: float) -> float:
    return power_ch / CH_PER_KW


@dataclass
class EngineSpec:
    """User/BIN-declared engine characteristics. Any field may be None
    (meaning unknown) except those actually used to build a curve."""

    displacement_l: float | None = None
    cylinders: int | None = None
    architecture: str | None = None  # e.g. "inline-4", "V6" - descriptive only
    aspiration: str | None = None  # "atmospheric" / "turbo" / "supercharged"
    peak_torque_nm: float | None = None
    peak_torque_rpm: float | None = None
    peak_power_kw: float | None = None
    peak_power_rpm: float | None = None
    redline_rpm: float | None = None
    idle_rpm: float | None = None
    bore_mm: float | None = None
    stroke_mm: float | None = None
    compression_ratio: float | None = None
    fuel_type: str | None = None
    thermal_efficiency: float | None = None  # 0..1, when known/estimated
    sources: dict[str, DataSource] = field(default_factory=dict)

    def source_of(self, field_name: str) -> DataSource:
        return self.sources.get(field_name, DataSource.UNKNOWN)


@dataclass(frozen=True)
class EngineCurve:
    """A built torque/power curve plus the confidence of the points it rests on."""

    torque_spline: MonotoneCubicSpline
    rpm_min: float
    rpm_max: float
    defining_points: tuple[tuple[float, float, str], ...]  # (rpm, torque_nm, label)
    model_confidence: float  # 0..1, based on how many defining points were real data

    def torque_nm(self, rpm: float) -> float:
        return self.torque_spline(rpm)

    def power_kw(self, rpm: float) -> float:
        return power_kw_from_torque_nm(self.torque_nm(rpm), rpm)

    def sample(self, count: int = 100) -> list[tuple[float, float, float]]:
        """[(rpm, torque_nm, power_kw), ...] evenly spaced across the curve's range."""
        return [(rpm, torque, power_kw_from_torque_nm(torque, rpm)) for rpm, torque in self.torque_spline.sample(count)]

    def peak_power_kw(self) -> tuple[float, float]:
        """Returns (rpm, power_kw) of the highest power point on the sampled curve."""
        samples = self.sample(400)
        rpm, torque, power = max(samples, key=lambda s: s[2])
        return rpm, power


def build_engine_curve(spec: EngineSpec) -> EngineCurve:
    """Build the torque curve for `spec`.

    Requires, at minimum, peak_torque_nm/peak_torque_rpm AND
    peak_power_kw/peak_power_rpm (the two points every production engine
    is characterized by) - raises ValueError naming exactly what is
    missing rather than silently substituting a guess. idle_rpm and
    redline_rpm are used as additional endpoint anchors when known; when
    not, the curve's domain is simply bounded by the two required points
    (still valid, just narrower - the caller/UI should say so).
    """
    missing = [
        name for name, value in (
            ("peak_torque_nm", spec.peak_torque_nm),
            ("peak_torque_rpm", spec.peak_torque_rpm),
            ("peak_power_kw", spec.peak_power_kw),
            ("peak_power_rpm", spec.peak_power_rpm),
        )
        if value is None
    ]
    if missing:
        raise ValueError(
            "Impossible de construire une courbe moteur : donnees manquantes : " + ", ".join(missing)
        )

    torque_at_peak_power = torque_nm_from_power_kw(spec.peak_power_kw, spec.peak_power_rpm)

    points: list[tuple[float, float, str]] = [
        (spec.peak_torque_rpm, spec.peak_torque_nm, "couple maximal"),
        (spec.peak_power_rpm, torque_at_peak_power, "puissance maximale (couple derive)"),
    ]
    point_sources = [spec.source_of("peak_torque_nm"), spec.source_of("peak_power_kw")]

    if spec.idle_rpm is not None and spec.idle_rpm < spec.peak_torque_rpm:
        # a real engine doesn't produce peak torque at idle; disclose a
        # conservative estimate (60% of peak) rather than inventing a
        # precise number, and mark it as such.
        points.insert(0, (spec.idle_rpm, spec.peak_torque_nm * 0.6, "ralenti (estimation)"))
        point_sources.insert(0, DataSource.ESTIMATED)

    if spec.redline_rpm is not None and spec.redline_rpm > spec.peak_power_rpm:
        # torque past the power peak is falling; disclose a conservative
        # taper (70% of peak torque) rather than a precise invented value.
        points.append((spec.redline_rpm, spec.peak_torque_nm * 0.7, "regime maximal (estimation)"))
        point_sources.append(DataSource.ESTIMATED)

    spline = build_monotone_cubic_spline([(rpm, torque) for rpm, torque, _ in points])

    weights = [SOURCE_WEIGHT[source] for source in point_sources]
    model_confidence = sum(weights) / len(weights) if weights else 0.0

    return EngineCurve(
        torque_spline=spline,
        rpm_min=points[0][0],
        rpm_max=points[-1][0],
        defining_points=tuple(points),
        model_confidence=round(model_confidence, 4),
    )
