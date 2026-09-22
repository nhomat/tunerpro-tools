#!/usr/bin/env python3
"""Generate the suite's fictitious test BIN files.

IMPORTANT (see AGENTS.md section 16): these are entirely synthetic byte
patterns produced by a seeded pseudo-random generator. They do NOT come
from, and do not represent, any real vehicle calibration. They exist
only to exercise BIN Analyzer, BIN Compare, Map Viewer and Checksum
Analyzer with known, reproducible content.

Run:
    python3 generate_examples.py

Produces, next to this script:
    example_original.bin
    example_modified.bin
    example_map_rpm.json
    example_map_fuel.json
    example_manifest.json   (documents every planted difference, for tests)
"""
from __future__ import annotations

import json
import random
import zlib
from pathlib import Path

HEADER_TEXT = (
    b"TUNERPRO TOOLS SUITE - SYNTHETIC EXAMPLE FILE - "
    b"NOT A REAL VEHICLE CALIBRATION - FOR TESTING ONLY\x00"
)

FILE_SIZE = 4096
RPM_MAP_OFFSET = 0x100   # 16 x 16, uint8
RPM_MAP_ROWS = 16
RPM_MAP_COLUMNS = 16
FUEL_MAP_OFFSET = 0x200  # 8 x 8, uint16 little-endian
FUEL_MAP_ROWS = 8
FUEL_MAP_COLUMNS = 8
FUEL_MAP_CELL_SIZE = 2
CHECKSUM_OFFSET = FILE_SIZE - 4  # last 4 bytes: CRC32 of everything before

RANDOM_SEED = 20260921  # fixed seed -> fully reproducible synthetic content

#: Planted, known modifications applied to build example_modified.bin from
#: example_original.bin. Kept explicit (rather than random) so BIN Compare
#: / Calibration Diff / Checksum Analyzer behaviour can be asserted exactly
#: in tests/test_examples.py.
PLANTED_DIFFERENCES = [
    # (offset, new_value) - inside the RPM map: a few cells bumped up.
    (RPM_MAP_OFFSET + 5, None),   # filled in at generation time (+5)
    (RPM_MAP_OFFSET + 40, None),  # (+12)
    # inside the Fuel map (low byte of one 16-bit cell)
    (FUEL_MAP_OFFSET + 10, None),  # (-3, clamped)
    # in the unstructured filler region, far from any map
    (0x300, None),  # (+1)
]
PLANTED_DELTAS = [5, 12, -3, 1]


def _build_original() -> bytearray:
    data = bytearray(FILE_SIZE)
    data[0:len(HEADER_TEXT)] = HEADER_TEXT

    rng = random.Random(RANDOM_SEED)

    # RPM map: ascending values with light synthetic noise, uint8.
    cursor = RPM_MAP_OFFSET
    for row in range(RPM_MAP_ROWS):
        for col in range(RPM_MAP_COLUMNS):
            value = (row * RPM_MAP_COLUMNS + col) % 256
            data[cursor] = value
            cursor += 1

    # Fuel map: uint16 little-endian, synthetic curve.
    cursor = FUEL_MAP_OFFSET
    for row in range(FUEL_MAP_ROWS):
        for col in range(FUEL_MAP_COLUMNS):
            value = (100 + row * 50 + col * 7) & 0xFFFF
            data[cursor:cursor + 2] = value.to_bytes(2, "little")
            cursor += 2

    # Filler region: deterministic pseudo-random bytes for entropy/search tests.
    filler_start = FUEL_MAP_OFFSET + FUEL_MAP_ROWS * FUEL_MAP_COLUMNS * FUEL_MAP_CELL_SIZE
    for offset in range(filler_start, CHECKSUM_OFFSET):
        data[offset] = rng.randrange(0, 256)

    # A known needle for the "search bytes" feature.
    needle = bytes([0xDE, 0xAD, 0xBE, 0xEF])
    needle_offset = 0x0A0
    data[needle_offset:needle_offset + len(needle)] = needle

    checksum = zlib.crc32(bytes(data[:CHECKSUM_OFFSET])) & 0xFFFFFFFF
    data[CHECKSUM_OFFSET:CHECKSUM_OFFSET + 4] = checksum.to_bytes(4, "big")

    return data


def _build_modified(original: bytearray) -> bytearray:
    modified = bytearray(original)
    for (offset, _), delta in zip(PLANTED_DIFFERENCES, PLANTED_DELTAS):
        modified[offset] = (modified[offset] + delta) & 0xFF
    # The checksum trailer is deliberately left untouched, so Checksum
    # Analyzer can demonstrate a detected mismatch on the modified file.
    return modified


def generate(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    original = _build_original()
    modified = _build_modified(original)

    (output_dir / "example_original.bin").write_bytes(bytes(original))
    (output_dir / "example_modified.bin").write_bytes(bytes(modified))

    manifest = {
        "warning": "Fichier fictif, ne represente aucun vehicule reel.",
        "file_size": FILE_SIZE,
        "rpm_map": {
            "offset": RPM_MAP_OFFSET, "rows": RPM_MAP_ROWS, "columns": RPM_MAP_COLUMNS,
            "cell_size": 1, "endianness": "little", "signed": False,
        },
        "fuel_map": {
            "offset": FUEL_MAP_OFFSET, "rows": FUEL_MAP_ROWS, "columns": FUEL_MAP_COLUMNS,
            "cell_size": FUEL_MAP_CELL_SIZE, "endianness": "little", "signed": False,
        },
        "search_needle_hex": "DEADBEEF",
        "search_needle_offset": 0x0A0,
        "checksum_offset": CHECKSUM_OFFSET,
        "checksum_algorithm": "crc32",
        "checksum_zone": [0, CHECKSUM_OFFSET],
        "checksum_byte_order": "big",
        "planted_differences": [
            {"offset": offset, "delta": delta}
            for (offset, _), delta in zip(PLANTED_DIFFERENCES, PLANTED_DELTAS)
        ],
    }
    (output_dir / "example_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    rpm_map = {
        "name": "RPM", "offset": RPM_MAP_OFFSET, "rows": RPM_MAP_ROWS, "columns": RPM_MAP_COLUMNS,
        "cell_size": 1, "endianness": "little", "signed": False, "factor": 1.0, "math_offset": 0.0,
        "unit": "rpm", "comment": "Map d'exemple synthetique", "is_heuristic": False,
    }
    fuel_map = {
        "name": "Fuel", "offset": FUEL_MAP_OFFSET, "rows": FUEL_MAP_ROWS, "columns": FUEL_MAP_COLUMNS,
        "cell_size": FUEL_MAP_CELL_SIZE, "endianness": "little", "signed": False, "factor": 0.1,
        "math_offset": 0.0, "unit": "mg/cyc", "comment": "Map d'exemple synthetique",
        "is_heuristic": False,
    }
    (output_dir / "example_map_rpm.json").write_text(json.dumps(rpm_map, indent=2), encoding="utf-8")
    (output_dir / "example_map_fuel.json").write_text(json.dumps(fuel_map, indent=2), encoding="utf-8")

    return manifest


if __name__ == "__main__":
    manifest = generate(Path(__file__).resolve().parent)
    print("Fichiers d'exemple generes :")
    for name in (
        "example_original.bin", "example_modified.bin",
        "example_map_rpm.json", "example_map_fuel.json", "example_manifest.json",
    ):
        print(f"  - {name}")
