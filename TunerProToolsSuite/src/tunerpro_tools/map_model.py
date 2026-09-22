"""Map definition and data extraction for Map Viewer / Map Database.

A "map" here is purely a user-declared reading recipe (offset, rows,
columns, cell size, endianness, sign, scaling). This module never
guesses map boundaries from file content and presents heuristic
detections (if any are ever added) as unconfirmed - see
``PROBABLE_MAP_NOTICE``.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROBABLE_MAP_NOTICE = "Probable map - validation manuelle necessaire."

CELL_SIZES = (1, 2, 4)
ENDIANNESS = ("little", "big")


@dataclass
class MapDefinition:
    """A fully user-specified way to read a 1D or 2D table out of a BIN."""

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
    comment: str = ""
    is_heuristic: bool = False

    def __post_init__(self) -> None:
        if self.cell_size not in CELL_SIZES:
            raise ValueError(f"cell_size must be one of {CELL_SIZES}")
        if self.endianness not in ENDIANNESS:
            raise ValueError(f"endianness must be one of {ENDIANNESS}")
        if self.rows <= 0 or self.columns <= 0:
            raise ValueError("rows and columns must be positive")

    @property
    def cell_count(self) -> int:
        return self.rows * self.columns

    @property
    def byte_length(self) -> int:
        return self.cell_count * self.cell_size

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MapDefinition":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "MapDefinition":
        return cls.from_dict(json.loads(text))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "MapDefinition":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def scale_value(raw_value: int, definition: MapDefinition) -> float:
    """Real value = raw value * factor + math_offset."""
    return raw_value * definition.factor + definition.math_offset


def unscale_value(real_value: float, definition: MapDefinition) -> float:
    if definition.factor == 0:
        raise ValueError("factor cannot be zero")
    return (real_value - definition.math_offset) / definition.factor


@dataclass(frozen=True)
class MapData:
    definition: MapDefinition
    raw: list[list[int]]
    scaled: list[list[float]]


def extract_map(data: bytes, definition: MapDefinition) -> MapData:
    """Read ``definition`` out of ``data`` without modifying it."""
    end = definition.offset + definition.byte_length
    if end > len(data):
        raise ValueError(
            f"Map '{definition.name}' extends past end of file "
            f"(needs {end} bytes, file has {len(data)})"
        )

    raw_rows: list[list[int]] = []
    scaled_rows: list[list[float]] = []
    cursor = definition.offset
    for _ in range(definition.rows):
        raw_row = []
        scaled_row = []
        for _ in range(definition.columns):
            chunk = data[cursor:cursor + definition.cell_size]
            value = int.from_bytes(
                chunk, byteorder=definition.endianness, signed=definition.signed
            )
            raw_row.append(value)
            scaled_row.append(scale_value(value, definition))
            cursor += definition.cell_size
        raw_rows.append(raw_row)
        scaled_rows.append(scaled_row)

    return MapData(definition=definition, raw=raw_rows, scaled=scaled_rows)
