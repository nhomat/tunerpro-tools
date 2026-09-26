import pytest

from tunerpro_tools.checksum import crc32
from tunerpro_tools.edit_history import EditHistory, UnsafeDestinationError
from tunerpro_tools.map_model import MapDefinition


# 1. The original BIN stays intact -------------------------------------------
def test_original_bytes_never_change_after_edits():
    original = bytes(range(64))
    history = EditHistory(original)
    history.apply_patch(4, bytes([99, 98, 97]))
    history.apply_patch(0, bytes([1, 2]))
    assert history.original_bytes == original
    assert history.current_bytes != original


def test_export_never_touches_a_source_file(tmp_path):
    source = tmp_path / "original.bin"
    source.write_bytes(bytes(range(32)))
    history = EditHistory(source.read_bytes())
    history.apply_patch(0, bytes([255, 254]))

    destination = tmp_path / "modified.bin"
    history.export(destination, source_path=source)

    assert source.read_bytes() == bytes(range(32))  # untouched
    assert destination.read_bytes()[0:2] == bytes([255, 254])


def test_export_refuses_same_path_as_source(tmp_path):
    source = tmp_path / "original.bin"
    source.write_bytes(bytes(range(16)))
    history = EditHistory(source.read_bytes())
    history.apply_patch(0, bytes([1]))
    with pytest.raises(UnsafeDestinationError):
        history.export(source, source_path=source)


# 2. Modifications are reproducible -------------------------------------------
def test_same_sequence_of_edits_produces_identical_bytes():
    original = bytes(range(100))
    definition = MapDefinition(name="T", offset=10, rows=2, columns=3, cell_size=1, factor=2.0)

    def run() -> bytes:
        history = EditHistory(original)
        history.apply_grid(definition, [[10.0, 20.0, 30.0], [40.0, 50.0, 60.0]])
        history.apply_patch(0, bytes([7, 7]))
        return history.current_bytes

    assert run() == run()


# 3. The before/after diff is exact -------------------------------------------
def test_diff_from_original_matches_applied_patch_exactly():
    original = bytes([0] * 20)
    history = EditHistory(original)
    history.apply_patch(5, bytes([10, 20, 30]))

    summary = history.diff_from_original()
    offsets = sorted(d.offset for d in summary.differences)
    assert offsets == [5, 6, 7]
    by_offset = {d.offset: d for d in summary.differences}
    assert by_offset[5].modified == 10
    assert by_offset[6].modified == 20
    assert by_offset[7].modified == 30
    assert all(d.original == 0 for d in summary.differences)


def test_diff_from_original_empty_when_undone_back_to_start():
    original = bytes(range(10))
    history = EditHistory(original)
    history.apply_patch(0, bytes([255]))
    history.undo()
    assert history.diff_from_original().difference_count == 0


# 4. Checksums are correctly handled ------------------------------------------
def test_checksum_before_after_reflects_the_modification():
    payload = bytearray(range(32))
    trailer_offset = len(payload)
    data = bytes(payload) + crc32(bytes(payload)).to_bytes(4, "big")

    history = EditHistory(data)
    before, after_stale = history.checksum_before_after(
        "crc32", 0, trailer_offset, trailer_offset, byte_order="big"
    )
    assert before.matches is True
    assert after_stale.matches is True  # no edit yet, so still consistent

    history.apply_patch(0, bytes([99]))  # change payload without fixing the checksum
    _, after_edit = history.checksum_before_after(
        "crc32", 0, trailer_offset, trailer_offset, byte_order="big"
    )
    assert after_edit.matches is False  # stale checksum correctly detected as mismatched


def test_apply_recomputed_checksum_writes_a_value_that_verifies():
    payload = bytearray(range(32))
    trailer_offset = len(payload)
    data = bytes(payload) + b"\x00\x00\x00\x00"  # wrong/placeholder checksum

    history = EditHistory(data)
    history.apply_patch(0, bytes([123]))  # modify the payload
    result, edit = history.apply_recomputed_checksum(
        "crc32", 0, trailer_offset, trailer_offset, byte_order="big"
    )
    assert edit.offset == trailer_offset

    # independently recompute over the final working bytes and confirm it verifies
    final_before, final_after = history.checksum_before_after(
        "crc32", 0, trailer_offset, trailer_offset, byte_order="big"
    )
    assert final_after.matches is True


# 5. Undo/redo works ------------------------------------------------------------
def test_undo_restores_previous_bytes_exactly():
    original = bytes(range(20))
    history = EditHistory(original)
    history.apply_patch(2, bytes([200, 201]))
    assert history.current_bytes != original
    history.undo()
    assert history.current_bytes == original
    assert history.can_undo is False
    assert history.can_redo is True


def test_redo_reapplies_the_undone_edit():
    original = bytes(range(20))
    history = EditHistory(original)
    history.apply_patch(2, bytes([200, 201]))
    modified = history.current_bytes
    history.undo()
    history.redo()
    assert history.current_bytes == modified


def test_new_edit_after_undo_clears_redo_stack():
    original = bytes(range(20))
    history = EditHistory(original)
    history.apply_patch(0, bytes([1]))
    history.undo()
    history.apply_patch(5, bytes([2]))  # a new edit while redo was available
    assert history.can_redo is False
    assert history.redo() is None


def test_multiple_undo_redo_sequence():
    original = bytes(range(10))
    history = EditHistory(original)
    history.apply_patch(0, bytes([100]))
    history.apply_patch(1, bytes([101]))
    history.apply_patch(2, bytes([102]))

    history.undo()
    history.undo()
    assert history.current_bytes[0] == 100
    assert history.current_bytes[1] == 1  # original value, second edit undone
    history.redo()
    assert history.current_bytes[1] == 101
    history.undo()
    history.undo()
    assert history.current_bytes == original


def test_history_lists_applied_edits_in_order():
    history = EditHistory(bytes(10))
    history.apply_patch(0, bytes([1]), label="first")
    history.apply_patch(1, bytes([2]), label="second")
    labels = [edit.label for edit in history.history]
    assert labels == ["first", "second"]
    history.undo()
    assert [edit.label for edit in history.history] == ["first"]


# 6. Export produces a valid file ------------------------------------------------
def test_export_writes_exactly_the_current_working_bytes(tmp_path):
    history = EditHistory(bytes(range(50)))
    history.apply_patch(10, bytes([1, 2, 3]))
    destination = tmp_path / "out.bin"
    history.export(destination)
    assert destination.read_bytes() == history.current_bytes
    assert len(destination.read_bytes()) == 50


def test_apply_grid_out_of_range_raises():
    history = EditHistory(bytes(10))
    definition = MapDefinition(name="T", offset=0, rows=10, columns=10, cell_size=1)
    with pytest.raises(ValueError):
        history.apply_grid(definition, [[0] * 10] * 10)


def test_apply_patch_out_of_range_raises():
    history = EditHistory(bytes(10))
    with pytest.raises(ValueError):
        history.apply_patch(8, bytes([1, 2, 3]))
