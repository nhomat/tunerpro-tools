"""The only module in this project that turns a suggested grid into bytes.

Everything here operates on an in-memory copy of the original bytes and
returns a *new* bytes object - nothing in this file ever opens a file
for writing, and nothing in this file lets a caller target the same
path it read from. The GUI layer is responsible for actually writing
the returned bytes to a file the user explicitly chose (via a save
dialog defaulting to a different name), after an explicit confirmation
showing the experimental-modification warning.
"""
from __future__ import annotations

from pathlib import Path

from .map_model import MapDefinition, unscale_value


class UnsafeDestinationError(ValueError):
    """Raised when a destination path would overwrite the source file."""


def assert_safe_destination(source_path: str | Path, destination_path: str | Path) -> None:
    """Refuse a destination that resolves to the same file as the source."""
    source = Path(source_path).expanduser().resolve()
    destination = Path(destination_path).expanduser().resolve()
    if source == destination:
        raise UnsafeDestinationError(
            "La destination ne peut pas etre le fichier source. "
            "Choisissez un nouveau nom de fichier pour la copie."
        )


def _clamp_to_width(value: int, width_bytes: int, signed: bool) -> int:
    bits = width_bytes * 8
    if signed:
        low, high = -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
    else:
        low, high = 0, 2 ** bits - 1
    return max(low, min(high, value))


def apply_grid_to_bytes(data: bytes, definition: MapDefinition, new_scaled_grid: list[list[float]]) -> bytes:
    """Return a new bytes object with `new_scaled_grid` written at `definition`'s location.

    `data` is never mutated. Values are converted from scaled/real units
    back to raw integers via the map's own factor/offset, rounded, and
    clamped to what the cell width can represent (never wrapped/masked
    silently) so an out-of-range suggestion is capped rather than
    corrupting an unrelated neighboring cell.
    """
    end = definition.offset + definition.byte_length
    if end > len(data):
        raise ValueError(
            f"Map '{definition.name}' depasse la fin du fichier "
            f"(besoin de {end} octets, fichier de {len(data)} octets)"
        )
    if len(new_scaled_grid) != definition.rows or any(len(row) != definition.columns for row in new_scaled_grid):
        raise ValueError("new_scaled_grid dimensions do not match the map definition")

    buffer = bytearray(data)
    cursor = definition.offset
    for row in new_scaled_grid:
        for value in row:
            raw = _clamp_to_width(
                round(unscale_value(value, definition)), definition.cell_size, definition.signed
            )
            buffer[cursor:cursor + definition.cell_size] = raw.to_bytes(
                definition.cell_size, byteorder=definition.endianness, signed=definition.signed
            )
            cursor += definition.cell_size
    return bytes(buffer)


def write_grid_to_copy(
    source_path: str | Path,
    destination_path: str | Path,
    definition: MapDefinition,
    new_scaled_grid: list[list[float]],
) -> Path:
    """Read `source_path`, apply `new_scaled_grid`, write the result to `destination_path`.

    Raises UnsafeDestinationError if destination_path == source_path.
    The source file is opened read-only and is never touched.
    """
    assert_safe_destination(source_path, destination_path)
    source_path = Path(source_path)
    destination_path = Path(destination_path)
    original_bytes = source_path.read_bytes()
    patched_bytes = apply_grid_to_bytes(original_bytes, definition, new_scaled_grid)
    destination_path.write_bytes(patched_bytes)
    return destination_path
