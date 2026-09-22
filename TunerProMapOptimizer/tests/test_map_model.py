import pytest

from map_optimizer.map_model import MapDefinition, extract_map, scale_value, unscale_value


def test_extract_map_row_major():
    data = bytes(range(12))
    definition = MapDefinition(name="T", offset=0, rows=3, columns=4, cell_size=1)
    assert extract_map(data, definition) == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]


def test_extract_map_out_of_range_raises():
    with pytest.raises(ValueError):
        extract_map(bytes(4), MapDefinition(name="T", offset=0, rows=10, columns=10, cell_size=1))


def test_scale_unscale_roundtrip():
    definition = MapDefinition(name="T", offset=0, rows=1, columns=1, factor=2.5, math_offset=-10)
    assert unscale_value(scale_value(40, definition), definition) == 40


def test_map_definition_json_roundtrip(tmp_path):
    definition = MapDefinition(name="Ign", offset=0x10, rows=4, columns=4, cell_size=2, endianness="big")
    path = tmp_path / "m.json"
    definition.save(path)
    assert MapDefinition.load(path) == definition


def test_rejects_invalid_cell_size():
    with pytest.raises(ValueError):
        MapDefinition(name="X", offset=0, rows=1, columns=1, cell_size=3)
