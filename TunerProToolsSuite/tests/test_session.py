from tunerpro_tools.map_model import MapDefinition
from tunerpro_tools.session import CalibrationSession


def test_session_roundtrip(tmp_path):
    session = CalibrationSession(
        name="Session Test",
        original_bin_path="C:/data/example_original.bin",
        modified_bin_path="C:/data/example_modified.bin",
        maps=[MapDefinition(name="RPM", offset=0, rows=4, columns=4)],
        notes="Notes de test",
    )
    session.record("bin_loaded", "example_original.bin")
    session.record("map_added", "RPM")

    path = tmp_path / "session.tpsuite"
    session.save(path)

    loaded = CalibrationSession.load(path)
    assert loaded.name == "Session Test"
    assert loaded.original_bin_path == "C:/data/example_original.bin"
    assert len(loaded.maps) == 1
    assert loaded.maps[0].name == "RPM"
    assert len(loaded.history) == 2
    assert loaded.history[0].action == "bin_loaded"


def test_session_file_is_gzip_compressed(tmp_path):
    session = CalibrationSession(name="Compressed")
    path = tmp_path / "session.tpsuite"
    session.save(path)
    with path.open("rb") as handle:
        magic = handle.read(2)
    assert magic == b"\x1f\x8b"  # gzip magic number
