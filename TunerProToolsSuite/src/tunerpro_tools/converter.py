"""HEX / DEC / BIN / intN conversions for the Value Converter tool."""
from __future__ import annotations

from dataclasses import dataclass

INT_TYPES: dict[str, tuple[int, bool]] = {
    "UINT8": (1, False),
    "INT8": (1, True),
    "UINT16": (2, False),
    "INT16": (2, True),
    "UINT32": (4, False),
    "INT32": (4, True),
}


@dataclass(frozen=True)
class ConversionResult:
    type_name: str
    width_bytes: int
    signed: bool
    byte_order: str
    hex_value: str
    dec_value: int
    bin_value: str
    raw_bytes: bytes


def _range_for(width_bytes: int, signed: bool) -> tuple[int, int]:
    bits = width_bytes * 8
    if signed:
        return -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
    return 0, 2 ** bits - 1


def convert_value(value: int, type_name: str, *, byte_order: str = "little") -> ConversionResult:
    """Convert an integer into every representation for one integer type."""
    if type_name not in INT_TYPES:
        raise ValueError(f"Unknown type: {type_name}")
    if byte_order not in ("little", "big"):
        raise ValueError("byte_order must be 'little' or 'big'")

    width_bytes, signed = INT_TYPES[type_name]
    low, high = _range_for(width_bytes, signed)
    if not (low <= value <= high):
        raise ValueError(f"{value} is out of range for {type_name} ({low}..{high})")

    raw = value.to_bytes(width_bytes, byteorder=byte_order, signed=signed)
    unsigned_value = int.from_bytes(raw, byteorder=byte_order, signed=False)

    return ConversionResult(
        type_name=type_name,
        width_bytes=width_bytes,
        signed=signed,
        byte_order=byte_order,
        hex_value="0x" + raw.hex().upper() if byte_order == "big" else "0x" + raw[::-1].hex().upper(),
        dec_value=value,
        bin_value=format(unsigned_value, f"0{width_bytes * 8}b"),
        raw_bytes=raw,
    )


def convert_all_types(value: int, *, byte_order: str = "little") -> dict[str, ConversionResult | str]:
    """Convert ``value`` into every type that can represent it, both endiannesses.

    Types the value overflows are reported as an error string rather than
    raising, so the GUI can show a full table in one pass.
    """
    results: dict[str, ConversionResult | str] = {}
    for type_name in INT_TYPES:
        try:
            results[type_name] = convert_value(value, type_name, byte_order=byte_order)
        except ValueError as exc:
            results[type_name] = str(exc)
    return results


def parse_input_value(text: str, base: str) -> int:
    """Parse a user-entered value in the given base ('hex', 'dec', 'bin')."""
    text = text.strip()
    if base == "hex":
        return int(text, 16)
    if base == "dec":
        return int(text, 10)
    if base == "bin":
        return int(text, 2)
    raise ValueError(f"Unknown base: {base}")


def swap_endianness(raw: bytes) -> bytes:
    return raw[::-1]
