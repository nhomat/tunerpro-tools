"""Modular checksum algorithms for Checksum Analyzer.

New algorithms are added by writing a function of signature
``(data: bytes) -> int`` and registering it in :data:`ALGORITHMS`; the
GUI tool discovers them from that registry, so no other module needs to
change.

This module never writes anything back into a file - it only computes
and compares. Writing a recomputed checksum into a BIN is a deliberate,
separate, explicit user action (see AGENTS.md / SAFETY.md: never write a
checksum automatically).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


def checksum_xor(data: bytes) -> int:
    result = 0
    for byte in data:
        result ^= byte
    return result


def checksum_sum8(data: bytes) -> int:
    return sum(data) & 0xFF


def checksum_sum16(data: bytes) -> int:
    return sum(data) & 0xFFFF


def checksum_sum32(data: bytes) -> int:
    return sum(data) & 0xFFFFFFFF


def crc8(data: bytes, *, polynomial: int = 0x07, init: int = 0x00) -> int:
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ polynomial) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def crc16_ccitt(data: bytes, *, polynomial: int = 0x1021, init: int = 0xFFFF) -> int:
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ polynomial) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def crc32(data: bytes) -> int:
    import zlib

    return zlib.crc32(data) & 0xFFFFFFFF


@dataclass(frozen=True)
class ChecksumAlgorithm:
    key: str
    label: str
    width_bytes: int
    func: Callable[[bytes], int]


ALGORITHMS: dict[str, ChecksumAlgorithm] = {
    algo.key: algo
    for algo in (
        ChecksumAlgorithm("xor", "XOR (8-bit)", 1, checksum_xor),
        ChecksumAlgorithm("sum8", "SUM (8-bit)", 1, checksum_sum8),
        ChecksumAlgorithm("sum16", "SUM (16-bit)", 2, checksum_sum16),
        ChecksumAlgorithm("sum32", "SUM (32-bit)", 4, checksum_sum32),
        ChecksumAlgorithm("crc8", "CRC8", 1, crc8),
        ChecksumAlgorithm("crc16", "CRC16-CCITT", 2, crc16_ccitt),
        ChecksumAlgorithm("crc32", "CRC32", 4, crc32),
    )
}


@dataclass(frozen=True)
class ChecksumResult:
    algorithm: str
    zone_start: int
    zone_end: int
    computed_value: int
    stored_value: int | None
    matches: bool | None

    @property
    def computed_hex(self) -> str:
        return f"0x{self.computed_value:X}"

    @property
    def stored_hex(self) -> str | None:
        return None if self.stored_value is None else f"0x{self.stored_value:X}"


def compute_checksum(
    data: bytes,
    algorithm_key: str,
    zone_start: int,
    zone_end: int,
    *,
    checksum_offset: int | None = None,
    byte_order: str = "big",
) -> ChecksumResult:
    """Compute ``algorithm_key`` over ``data[zone_start:zone_end]``.

    If ``checksum_offset`` is given, the stored value at that offset is
    read back (using the algorithm's natural width) and compared against
    the freshly computed value. Nothing is written to ``data``.
    """
    if algorithm_key not in ALGORITHMS:
        raise ValueError(f"Unknown checksum algorithm: {algorithm_key}")
    algorithm = ALGORITHMS[algorithm_key]

    if not (0 <= zone_start <= zone_end <= len(data)):
        raise ValueError("Invalid checksum zone bounds")

    zone = data[zone_start:zone_end]
    computed = algorithm.func(zone)

    stored_value = None
    matches = None
    if checksum_offset is not None:
        width = algorithm.width_bytes
        raw = data[checksum_offset:checksum_offset + width]
        if len(raw) == width:
            stored_value = int.from_bytes(raw, byteorder=byte_order, signed=False)
            matches = stored_value == computed

    return ChecksumResult(
        algorithm=algorithm_key,
        zone_start=zone_start,
        zone_end=zone_end,
        computed_value=computed,
        stored_value=stored_value,
        matches=matches,
    )
