import pytest

from map_optimizer.map_model import MapDefinition, extract_map
from map_optimizer.patch import (
    UnsafeDestinationError,
    apply_grid_to_bytes,
    assert_safe_destination,
    write_grid_to_copy,
)


def test_assert_safe_destination_rejects_same_path(tmp_path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"\x00")
    with pytest.raises(UnsafeDestinationError):
        assert_safe_destination(path, path)


def test_assert_safe_destination_allows_different_path(tmp_path):
    source = tmp_path / "a.bin"
    dest = tmp_path / "b.bin"
    source.write_bytes(b"\x00")
    assert_safe_destination(source, dest)  # should not raise


def test_apply_grid_to_bytes_does_not_mutate_original():
    data = bytes(range(16))
    definition = MapDefinition(name="T", offset=0, rows=2, columns=2, cell_size=1)
    new_grid = [[100.0, 101.0], [102.0, 103.0]]
    patched = apply_grid_to_bytes(data, definition, new_grid)
    assert data == bytes(range(16))  # original untouched
    assert patched != data
    assert list(patched[0:4]) == [100, 101, 102, 103]
    assert patched[4:] == data[4:]  # rest of file untouched


def test_apply_grid_to_bytes_roundtrips_through_extract_map():
    data = bytes(16)
    definition = MapDefinition(name="T", offset=0, rows=2, columns=2, cell_size=1, factor=2.0)
    new_scaled_grid = [[10.0, 20.0], [30.0, 40.0]]  # raw values: 5, 10, 15, 20
    patched = apply_grid_to_bytes(data, definition, new_scaled_grid)
    raw_grid = extract_map(patched, definition)
    assert raw_grid == [[5, 10], [15, 20]]


def test_apply_grid_to_bytes_clamps_out_of_range_values():
    data = bytes(4)
    definition = MapDefinition(name="T", offset=0, rows=1, columns=1, cell_size=1, signed=False)
    patched = apply_grid_to_bytes(data, definition, [[999.0]])
    assert patched[0] == 255  # clamped to uint8 max, not wrapped/masked


def test_apply_grid_to_bytes_rejects_dimension_mismatch():
    data = bytes(16)
    definition = MapDefinition(name="T", offset=0, rows=2, columns=2, cell_size=1)
    with pytest.raises(ValueError):
        apply_grid_to_bytes(data, definition, [[1.0, 2.0, 3.0]])


def test_write_grid_to_copy_creates_new_file_and_preserves_source(tmp_path):
    source = tmp_path / "original.bin"
    source.write_bytes(bytes(16))
    destination = tmp_path / "modified.bin"
    definition = MapDefinition(name="T", offset=0, rows=2, columns=2, cell_size=1)

    write_grid_to_copy(source, destination, definition, [[9.0, 8.0], [7.0, 6.0]])

    assert source.read_bytes() == bytes(16)  # source untouched
    assert destination.exists()
    assert list(destination.read_bytes()[0:4]) == [9, 8, 7, 6]


def test_write_grid_to_copy_refuses_same_path(tmp_path):
    source = tmp_path / "original.bin"
    source.write_bytes(bytes(16))
    definition = MapDefinition(name="T", offset=0, rows=2, columns=2, cell_size=1)
    with pytest.raises(UnsafeDestinationError):
        write_grid_to_copy(source, source, definition, [[1.0, 2.0], [3.0, 4.0]])
