"""Undo/redo, before/after diff, checksum recompute and BIN export.

The only state this module ever mutates is its own in-memory working
copy (``EditHistory.current_bytes``). The bytes the history was created
from (``EditHistory.original_bytes``) are stored once and never written
to again by anything in this module - exporting always requires an
explicit destination path, and refuses one that resolves to the source
file (see ``export``), matching the rest of the suite's "never overwrite
an original BIN" rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .checksum import ChecksumResult, compute_checksum
from .compare import CompareSummary, compare_bytes
from .map_model import MapDefinition, unscale_value


class UnsafeDestinationError(ValueError):
    """Raised when an export destination would overwrite the source file."""


def _clamp_to_width(value: int, width_bytes: int, signed: bool) -> int:
    bits = width_bytes * 8
    if signed:
        low, high = -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
    else:
        low, high = 0, 2 ** bits - 1
    return max(low, min(high, value))


@dataclass(frozen=True)
class Edit:
    """One applied, reversible byte-range change."""

    offset: int
    old_bytes: bytes
    new_bytes: bytes
    label: str = ""

    @property
    def length(self) -> int:
        return len(self.new_bytes)


class EditHistory:
    """Tracks an in-memory working copy of a BIN plus its undo/redo stacks."""

    def __init__(self, original_bytes: bytes):
        self._original = bytes(original_bytes)
        self._working = bytearray(original_bytes)
        self._undo_stack: list[Edit] = []
        self._redo_stack: list[Edit] = []

    # ------------------------------------------------------------------
    @property
    def original_bytes(self) -> bytes:
        return self._original

    @property
    def current_bytes(self) -> bytes:
        return bytes(self._working)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def history(self) -> tuple[Edit, ...]:
        """Every edit currently applied, oldest first (i.e. the undo stack)."""
        return tuple(self._undo_stack)

    # ------------------------------------------------------------------
    def apply_patch(self, offset: int, new_bytes: bytes, *, label: str = "") -> Edit:
        """Apply a raw byte-range write to the working copy. Returns the Edit for it."""
        end = offset + len(new_bytes)
        if offset < 0 or end > len(self._working):
            raise ValueError(f"Patch at 0x{offset:X}..0x{end:X} is out of range")
        old_bytes = bytes(self._working[offset:end])
        self._working[offset:end] = new_bytes
        edit = Edit(offset=offset, old_bytes=old_bytes, new_bytes=bytes(new_bytes), label=label)
        self._undo_stack.append(edit)
        self._redo_stack.clear()  # a fresh edit invalidates any previously undone redo history
        return edit

    def apply_grid(
        self, definition: MapDefinition, new_scaled_grid: list[list[float]], *, label: str = ""
    ) -> Edit:
        """Convert `new_scaled_grid` to raw bytes via `definition` and apply it as one patch."""
        if len(new_scaled_grid) != definition.rows or any(
            len(row) != definition.columns for row in new_scaled_grid
        ):
            raise ValueError("new_scaled_grid dimensions do not match the map definition")

        raw = bytearray(definition.byte_length)
        cursor = 0
        for row in new_scaled_grid:
            for value in row:
                raw_value = _clamp_to_width(
                    round(unscale_value(value, definition)), definition.cell_size, definition.signed
                )
                raw[cursor:cursor + definition.cell_size] = raw_value.to_bytes(
                    definition.cell_size, byteorder=definition.endianness, signed=definition.signed
                )
                cursor += definition.cell_size

        return self.apply_patch(definition.offset, bytes(raw), label=label or f"grid:{definition.name}")

    def apply_recomputed_checksum(
        self, algorithm_key: str, zone_start: int, zone_end: int, checksum_offset: int, *, byte_order: str = "big"
    ) -> tuple[ChecksumResult, Edit]:
        """Recompute a checksum over the CURRENT working bytes and write it in, as one undoable edit.

        This only ever runs when explicitly called (a deliberate, named
        action - see AGENTS.md/SAFETY.md: never write a checksum
        automatically as a side effect of something else).
        """
        result = compute_checksum(
            self.current_bytes, algorithm_key, zone_start, zone_end,
            checksum_offset=checksum_offset, byte_order=byte_order,
        )
        from .checksum import ALGORITHMS

        width = ALGORITHMS[algorithm_key].width_bytes
        new_bytes = result.computed_value.to_bytes(width, byteorder=byte_order, signed=False)
        edit = self.apply_patch(checksum_offset, new_bytes, label=f"checksum:{algorithm_key}")
        return result, edit

    # ------------------------------------------------------------------
    def undo(self) -> Edit | None:
        if not self._undo_stack:
            return None
        edit = self._undo_stack.pop()
        self._working[edit.offset:edit.offset + edit.length] = edit.old_bytes
        self._redo_stack.append(edit)
        return edit

    def redo(self) -> Edit | None:
        if not self._redo_stack:
            return None
        edit = self._redo_stack.pop()
        self._working[edit.offset:edit.offset + edit.length] = edit.new_bytes
        self._undo_stack.append(edit)
        return edit

    # ------------------------------------------------------------------
    def diff_from_original(self) -> CompareSummary:
        """Exact byte-level diff between the untouched original and the current working copy."""
        return compare_bytes(self._original, self.current_bytes)

    def checksum_before_after(
        self, algorithm_key: str, zone_start: int, zone_end: int, checksum_offset: int, *, byte_order: str = "big"
    ) -> tuple[ChecksumResult, ChecksumResult]:
        """Compute the same checksum over the original vs. the current bytes, for side-by-side display."""
        before = compute_checksum(
            self._original, algorithm_key, zone_start, zone_end,
            checksum_offset=checksum_offset, byte_order=byte_order,
        )
        after = compute_checksum(
            self.current_bytes, algorithm_key, zone_start, zone_end,
            checksum_offset=checksum_offset, byte_order=byte_order,
        )
        return before, after

    def export(self, destination_path: str | Path, *, source_path: str | Path | None = None) -> Path:
        """Write the current working copy to `destination_path`.

        If `source_path` is given, refuses a destination that resolves to
        the same file (the source BIN is never overwritten by this call).
        """
        destination = Path(destination_path)
        if source_path is not None:
            source = Path(source_path).expanduser().resolve()
            if destination.expanduser().resolve() == source:
                raise UnsafeDestinationError(
                    "La destination ne peut pas etre le fichier source. "
                    "Choisissez un nouveau nom de fichier pour l'export."
                )
        destination.write_bytes(self.current_bytes)
        return destination
