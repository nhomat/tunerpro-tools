"""Map definition and extraction - same design as the main TunerPro Tools Suite.

Kept intentionally read-only: extract_map() never writes to `data`. This
module has no knowledge of "optimization" - it only knows how to read a
grid out of a BIN given a user-supplied recipe.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

CELL_SIZES = (1, 2, 4)
ENDIANNESS = ("little", "big")


@dataclass
class MapDefinition:
    name: str
    offset: int
    rows: int
    columns: int
    cell_size: int = 1
    endianness: str = "little"
    signed: bool = False
    factor: float = 1.0
    math_offset: float = 0.0
    unit: str = ""

    def __post_init__(self) -> None:
        if self.cell_size not in CELL_SIZES:
            raise ValueError(f"cell_size must be one of {CELL_SIZES}")
        if self.endianness not in ENDIANNESS:
            raise ValueError(f"endianness must be one of {ENDIANNESS}")
        if self.rows <= 0 or self.columns <= 0:
            raise ValueError("rows and columns must be positive")

    @property
    def byte_length(self) -> int:
        return self.rows * self.columns * self.cell_size

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MapDefinition":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "MapDefinition":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def scale_value(raw_value: int, definition: MapDefinition) -> float:
    return raw_value * definition.factor + definition.math_offset


def unscale_value(real_value: float, definition: MapDefinition) -> int:
    if definition.factor == 0:
        raise ValueError("factor cannot be zero")
    return round((real_value - definition.math_offset) / definition.factor)


def extract_map(data: bytes, definition: MapDefinition) -> list[list[int]]:
    """Read the raw integer grid for `definition` out of `data`."""
    end = definition.offset + definition.byte_length
    if end > len(data):
        raise ValueError(
            f"Map '{definition.name}' depasse la fin du fichier "
            f"(besoin de {end} octets, fichier de {len(data)} octets)"
        )
    rows: list[list[int]] = []
    cursor = definition.offset
    for _ in range(definition.rows):
        row = []
        for _ in range(definition.columns):
            chunk = data[cursor:cursor + definition.cell_size]
            row.append(int.from_bytes(chunk, byteorder=definition.endianness, signed=definition.signed))
            cursor += definition.cell_size
        rows.append(row)
    return rows
