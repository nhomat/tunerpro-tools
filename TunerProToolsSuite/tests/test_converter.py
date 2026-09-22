import pytest

from tunerpro_tools.converter import (
    convert_all_types,
    convert_value,
    parse_input_value,
)


def test_convert_uint8():
    result = convert_value(255, "UINT8")
    assert result.hex_value == "0xFF"
    assert result.dec_value == 255
    assert result.bin_value == "11111111"


def test_convert_int8_negative():
    result = convert_value(-1, "INT8")
    assert result.hex_value == "0xFF"
    assert result.bin_value == "11111111"


def test_convert_uint16_endianness():
    little = convert_value(0x1234, "UINT16", byte_order="little")
    big = convert_value(0x1234, "UINT16", byte_order="big")
    assert little.hex_value == "0x1234"
    assert little.raw_bytes == b"\x34\x12"
    assert big.hex_value == "0x1234"
    assert big.raw_bytes == b"\x12\x34"


def test_convert_value_out_of_range_raises():
    with pytest.raises(ValueError):
        convert_value(300, "UINT8")


def test_convert_all_types_reports_overflow_as_string():
    results = convert_all_types(70000)
    assert isinstance(results["UINT16"], str)
    assert results["UINT32"].dec_value == 70000


def test_parse_input_value_bases():
    assert parse_input_value("FF", "hex") == 255
    assert parse_input_value("255", "dec") == 255
    assert parse_input_value("11111111", "bin") == 255
