import pytest

from tunerpro_tools.map_model import MapDefinition, extract_map, scale_value, unscale_value


def test_extract_map_reads_grid_in_row_major_order():
    data = bytes(range(12))  # 3x4 grid, cell_size=1
    definition = MapDefinition(name="Test", offset=0, rows=3, columns=4, cell_size=1)
    result = extract_map(data, definition)
    assert result.raw == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]


def test_extract_map_applies_scaling():
    data = bytes([10, 20])
    definition = MapDefinition(
        name="RPM", offset=0, rows=1, columns=2, cell_size=1, factor=100.0, math_offset=500.0
    )
    result = extract_map(data, definition)
    assert result.scaled == [[1500.0, 2500.0]]


def test_scale_and_unscale_are_inverses():
    definition = MapDefinition(name="X", offset=0, rows=1, columns=1, factor=2.5, math_offset=-10)
    raw_value = 40
    real = scale_value(raw_value, definition)
    assert unscale_value(real, definition) == pytest.approx(raw_value)


def test_extract_map_out_of_range_raises():
    data = bytes(range(4))
    definition = MapDefinition(name="Too big", offset=0, rows=10, columns=10, cell_size=1)
    with pytest.raises(ValueError):
        extract_map(data, definition)


def test_map_definition_rejects_invalid_cell_size():
    with pytest.raises(ValueError):
        MapDefinition(name="Bad", offset=0, rows=1, columns=1, cell_size=3)


def test_map_definition_json_roundtrip(tmp_path):
    definition = MapDefinition(
        name="Ignition", offset=0x100, rows=8, columns=8, cell_size=2,
        endianness="big", signed=True, factor=0.5, math_offset=-64, unit="deg",
    )
    path = tmp_path / "ignition.json"
    definition.save(path)
    loaded = MapDefinition.load(path)
    assert loaded == definition


def test_16bit_big_endian_extraction():
    data = b"\x01\x00\x02\x00"  # big-endian: 0x0100, 0x0200
    definition = MapDefinition(name="X", offset=0, rows=1, columns=2, cell_size=2, endianness="big")
    result = extract_map(data, definition)
    assert result.raw == [[0x0100, 0x0200]]
