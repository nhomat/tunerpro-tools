"""Lambda <-> AFR conversions.

These are theoretical, stoichiometric-ratio-based conversions only. Real
AFR/Lambda behaviour depends on actual fuel composition, sensor
calibration and engine conditions - this module makes no claim beyond
the arithmetic conversion (see the disclaimer text below, surfaced by
the GUI tool).
"""
from __future__ import annotations

from dataclasses import dataclass

THEORETICAL_DISCLAIMER = (
    "Conversions theoriques uniquement. Les valeurs reelles dependent du "
    "carburant utilise et du contexte moteur (temperature, pression, "
    "qualite du carburant, calibration des sondes)."
)


@dataclass(frozen=True)
class FuelProfile:
    key: str
    label: str
    stoichiometric_afr: float


FUEL_PROFILES: dict[str, FuelProfile] = {
    profile.key: profile
    for profile in (
        FuelProfile("gasoline", "Essence (E0-E10)", 14.7),
        FuelProfile("e85", "E85 (ethanol 85%)", 9.8),
        FuelProfile("e100", "E100 (ethanol pur)", 9.0),
        FuelProfile("diesel", "Diesel", 14.5),
        FuelProfile("methanol", "Methanol", 6.45),
    )
}


def afr_to_lambda(afr: float, fuel_key: str = "gasoline") -> float:
    profile = _profile(fuel_key)
    return afr / profile.stoichiometric_afr


def lambda_to_afr(lam: float, fuel_key: str = "gasoline") -> float:
    profile = _profile(fuel_key)
    return lam * profile.stoichiometric_afr


def _profile(fuel_key: str) -> FuelProfile:
    if fuel_key not in FUEL_PROFILES:
        raise ValueError(f"Unknown fuel profile: {fuel_key}")
    return FUEL_PROFILES[fuel_key]


def common_conversion_table(fuel_key: str = "gasoline") -> list[tuple[float, float]]:
    """Return a handful of commonly referenced lambda values with their AFR."""
    common_lambdas = [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20]
    return [(lam, lambda_to_afr(lam, fuel_key)) for lam in common_lambdas]
