"""Honest confidence scoring and limitations reporting for a simulation.

The confidence percentage is a plain weighted average over the fields
that actually feed the physics (see data_provenance.SOURCE_WEIGHT) -
never a number chosen to "look right". Anything not BIN/USER-sourced
shows up in `list_limitations` with a concrete description of what it
affects, so "92% confidence" always comes with a reason a reader can
check.
"""
from __future__ import annotations

from dataclasses import dataclass

from .data_provenance import SOURCE_WEIGHT, DataSource

#: Fields required for the physics to run at all, and what each affects
#: when its source is ESTIMATED or UNKNOWN. This is the single place
#: that defines both the confidence weighting and the limitations text -
#: change it here and both stay in sync.
REQUIRED_FIELDS: dict[str, str] = {
    "vehicle.mass_kg": "l'acceleration et le temps aux 100 km/h dependent directement de la masse.",
    "vehicle.drag_coefficient": "la resistance a l'air (donc la vitesse maximale) est estimee.",
    "vehicle.frontal_area_m2": "la resistance a l'air (donc la vitesse maximale) est estimee.",
    "vehicle.rolling_resistance_coefficient": (
        "un coefficient de resistance au roulement generique est utilise, "
        "precision reduite a basse/moyenne vitesse."
    ),
    "transmission.final_drive_ratio": "la correspondance regime moteur / vitesse est estimee.",
    "transmission.wheel_radius_m": "la correspondance regime moteur / vitesse est estimee.",
    "engine.peak_torque_nm": "la courbe de couple entiere repose sur une valeur non confirmee.",
    "engine.peak_torque_rpm": "la position du pic de couple sur la courbe est incertaine.",
    "engine.peak_power_kw": "la courbe de puissance entiere repose sur une valeur non confirmee.",
    "engine.peak_power_rpm": "la position du pic de puissance sur la courbe est incertaine.",
}


@dataclass(frozen=True)
class ConfidenceReport:
    confidence: float  # 0..1
    limitations: tuple[str, ...]
    sources: dict[str, DataSource]

    @property
    def confidence_percent(self) -> float:
        return round(self.confidence * 100, 1)


def compute_confidence_report(
    sources: dict[str, DataSource], *, required_fields: dict[str, str] = None
) -> ConfidenceReport:
    """Build a ConfidenceReport from a flat `{field_name: DataSource}` map.

    Any field in `required_fields` missing from `sources` is treated as
    DataSource.UNKNOWN (never silently assumed fine). Extra keys in
    `sources` beyond `required_fields` are ignored for scoring (they may
    be purely descriptive fields like "vehicle.make").
    """
    fields = required_fields if required_fields is not None else REQUIRED_FIELDS

    weights = []
    limitations = []
    for field_name, impact in fields.items():
        source = sources.get(field_name, DataSource.UNKNOWN)
        weights.append(SOURCE_WEIGHT[source])
        if source in (DataSource.ESTIMATED, DataSource.UNKNOWN):
            prefix = "Estimee" if source is DataSource.ESTIMATED else "Inconnue"
            limitations.append(f"{field_name} ({prefix.lower()}) : {impact}")

    confidence = sum(weights) / len(weights) if weights else 0.0
    return ConfidenceReport(confidence=round(confidence, 4), limitations=tuple(limitations), sources=dict(sources))
