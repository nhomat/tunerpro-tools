"""Read-only analysis of binary calibration files.

Nothing in this module ever opens a file for writing. Loading a
:class:`BinFile` reads the bytes into memory once; every analysis
function below operates on that in-memory copy.
"""
from __future__ import annotations

import math
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ByteStats:
    size: int
    unique_values: int
    minimum: int
    maximum: int
    mean: float
    entropy: float
    histogram: tuple[int, ...]  # 256 buckets, one per byte value


@dataclass(frozen=True)
class SearchMatch:
    offset: int
    length: int

    @property
    def offset_hex(self) -> str:
        return f"0x{self.offset:X}"


class BinFile:
    """An immutable, in-memory view of a ``.bin`` file."""

    def __init__(self, path: str | Path, data: bytes):
        self.path = Path(path)
        self.data = data

    @classmethod
    def load(cls, path: str | Path) -> "BinFile":
        path = Path(path)
        with path.open("rb") as handle:
            data = handle.read()
        return cls(path, data)

    @property
    def size(self) -> int:
        return len(self.data)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def compute_stats(self) -> ByteStats:
        data = self.data
        if not data:
            return ByteStats(0, 0, 0, 0, 0.0, 0.0, tuple([0] * 256))

        histogram = [0] * 256
        for byte in data:
            histogram[byte] += 1

        size = len(data)
        unique_values = sum(1 for count in histogram if count > 0)
        minimum = min(data)
        maximum = max(data)
        mean = sum(data) / size

        entropy = 0.0
        for count in histogram:
            if count == 0:
                continue
            probability = count / size
            entropy -= probability * math.log2(probability)

        return ByteStats(
            size=size,
            unique_values=unique_values,
            minimum=minimum,
            maximum=maximum,
            mean=mean,
            entropy=entropy,
            histogram=tuple(histogram),
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search_bytes(self, needle: bytes) -> list[SearchMatch]:
        """Find every (possibly overlapping) occurrence of ``needle``."""
        if not needle:
            return []
        matches = []
        start = 0
        data = self.data
        while True:
            index = data.find(needle, start)
            if index == -1:
                break
            matches.append(SearchMatch(offset=index, length=len(needle)))
            start = index + 1
        return matches

    def search_value(
        self,
        value: int,
        *,
        width: int = 1,
        signed: bool = False,
        byte_order: str = "little",
    ) -> list[SearchMatch]:
        """Find every occurrence of an 8/16/32-bit value at any offset."""
        if width not in (1, 2, 4):
            raise ValueError("width must be 1, 2 or 4 bytes")
        needle = value.to_bytes(width, byteorder=byte_order, signed=signed)
        return self.search_bytes(needle)

    # ------------------------------------------------------------------
    # Offsets / hex view
    # ------------------------------------------------------------------
    def hex_dump(self, offset: int = 0, length: int | None = None, width: int = 16) -> str:
        """Return a classic hex-editor style dump starting at ``offset``."""
        end = self.size if length is None else min(self.size, offset + length)
        lines = []
        for row_start in range(offset, end, width):
            row = self.data[row_start:min(row_start + width, end)]
            hex_part = " ".join(f"{b:02X}" for b in row)
            hex_part = hex_part.ljust(width * 3 - 1)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
            lines.append(f"{row_start:08X}  {hex_part}  |{ascii_part}|")
        return "\n".join(lines)

    def read_at(
        self,
        offset: int,
        *,
        width: int = 1,
        signed: bool = False,
        byte_order: str = "little",
    ) -> int:
        chunk = self.data[offset:offset + width]
        if len(chunk) != width:
            raise IndexError(f"offset 0x{offset:X} + width {width} is out of range")
        return int.from_bytes(chunk, byteorder=byte_order, signed=signed)


def offset_repr(offset: int) -> tuple[str, str]:
    """Return ``(hex, decimal)`` string representations of an offset."""
    return f"0x{offset:X}", str(offset)
