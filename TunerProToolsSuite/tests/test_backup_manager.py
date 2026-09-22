import pytest

from tunerpro_tools.backup_manager import backup_file, list_backups, restore_original


def test_backup_file_creates_timestamped_copy_and_preserves_original(tuner_root, tmp_path):
    source = tmp_path / "example_original.bin"
    original_bytes = bytes(range(20))
    source.write_bytes(original_bytes)

    record = backup_file(source, kind="original")

    assert record.backup_path.exists()
    assert record.backup_path.read_bytes() == original_bytes
    assert source.read_bytes() == original_bytes  # untouched
    assert record.backup_path.parent == tuner_root.backups_original_dir


def test_backup_file_missing_source_raises(tuner_root, tmp_path):
    with pytest.raises(FileNotFoundError):
        backup_file(tmp_path / "does_not_exist.bin")


def test_list_backups_returns_created_files(tuner_root, tmp_path):
    source = tmp_path / "a.bin"
    source.write_bytes(b"\x00")
    backup_file(source, kind="modified")
    backups = list_backups(kind="modified")
    assert len(backups) == 1


def test_restore_original_copies_backup_to_destination(tuner_root, tmp_path):
    source = tmp_path / "orig.bin"
    source.write_bytes(b"\xAA\xBB")
    record = backup_file(source, kind="original")

    destination = tmp_path / "restored.bin"
    restore_original(record.backup_path, destination)
    assert destination.read_bytes() == b"\xAA\xBB"


def test_restore_original_refuses_to_overwrite_existing_file(tuner_root, tmp_path):
    source = tmp_path / "orig.bin"
    source.write_bytes(b"\xAA\xBB")
    record = backup_file(source, kind="original")

    destination = tmp_path / "already_there.bin"
    destination.write_bytes(b"\x00")

    with pytest.raises(FileExistsError):
        restore_original(record.backup_path, destination)
