"""Where a simulation input value came from - the backbone of the honesty
contract for the vehicle simulator (see AGENTS.md / SAFETY.md: never
invent a value silently).

Every VehicleSpec/EngineSpec field is paired with one of these in that
spec's ``sources`` dict, and simulation_confidence.py turns the whole
set into a single confidence score plus a human-readable limitations
list - never a fabricated percentage.
"""
from __future__ import annotations

from enum import Enum


class DataSource(str, Enum):
    BIN = "donnee du fichier BIN"
    USER = "renseignee par l'utilisateur"
    CALCULATED = "calculee par le modele"
    ESTIMATED = "estimee (valeur par defaut disclosee)"
    UNKNOWN = "inconnue"


#: Relative trust weight per source, used by simulation_confidence.py.
#: BIN and USER are both "real" data (1.0); CALCULATED is a deterministic
#: consequence of real data (0.9, small penalty for compounding); ESTIMATED
#: is a disclosed default standing in for missing data (0.5); UNKNOWN
#: contributes nothing (0.0) - it is never silently treated as "fine".
SOURCE_WEIGHT: dict[DataSource, float] = {
    DataSource.BIN: 1.0,
    DataSource.USER: 1.0,
    DataSource.CALCULATED: 0.9,
    DataSource.ESTIMATED: 0.5,
    DataSource.UNKNOWN: 0.0,
}
