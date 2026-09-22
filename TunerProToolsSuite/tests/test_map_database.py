from tunerpro_tools.map_database import MapDatabase
from tunerpro_tools.map_model import MapDefinition


def test_save_and_load_map(tmp_path):
    db_path = tmp_path / "maps.sqlite3"
    definition = MapDefinition(
        name="RPM", offset=0x1000, rows=16, columns=16, cell_size=2,
        endianness="big", signed=False, factor=0.25, math_offset=0, unit="rpm",
    )
    with MapDatabase(db_path) as db:
        db.save_map(definition)

    with MapDatabase(db_path) as db:
        loaded = db.load_map("RPM")
    assert loaded == definition


def test_list_maps_sorted_by_name(tmp_path):
    db_path = tmp_path / "maps.sqlite3"
    with MapDatabase(db_path) as db:
        db.save_map(MapDefinition(name="Zeta", offset=0, rows=1, columns=1))
        db.save_map(MapDefinition(name="Alpha", offset=0, rows=1, columns=1))
        names = [m.name for m in db.list_maps()]
    assert names == ["Alpha", "Zeta"]


def test_save_map_upserts_existing_entry(tmp_path):
    db_path = tmp_path / "maps.sqlite3"
    with MapDatabase(db_path) as db:
        db.save_map(MapDefinition(name="Fuel", offset=0, rows=1, columns=1, factor=1.0))
        db.save_map(MapDefinition(name="Fuel", offset=0, rows=1, columns=1, factor=2.0))
        loaded = db.load_map("Fuel")
    assert loaded.factor == 2.0


def test_delete_map(tmp_path):
    db_path = tmp_path / "maps.sqlite3"
    with MapDatabase(db_path) as db:
        db.save_map(MapDefinition(name="Temp", offset=0, rows=1, columns=1))
        assert db.delete_map("Temp") is True
        assert db.load_map("Temp") is None
        assert db.delete_map("Temp") is False
