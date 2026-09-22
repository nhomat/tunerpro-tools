"""Local SQLite-backed store of :class:`MapDefinition` records.

Purely a save/recall tool for map configurations the user has defined
and validated themselves. It never invents or auto-populates maps from
a BIN's content (see AGENTS.md section 10).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import get_config
from .map_model import MapDefinition

_SCHEMA = """
CREATE TABLE IF NOT EXISTS maps (
    name TEXT PRIMARY KEY,
    offset INTEGER NOT NULL,
    rows INTEGER NOT NULL,
    columns INTEGER NOT NULL,
    cell_size INTEGER NOT NULL,
    endianness TEXT NOT NULL,
    signed INTEGER NOT NULL,
    factor REAL NOT NULL,
    math_offset REAL NOT NULL,
    unit TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    is_heuristic INTEGER NOT NULL DEFAULT 0
);
"""


class MapDatabase:
    """Thin wrapper around a SQLite file storing named map configurations."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else get_config().map_database_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.execute(_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "MapDatabase":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def save_map(self, definition: MapDefinition) -> None:
        self._connection.execute(
            """
            INSERT INTO maps (
                name, offset, rows, columns, cell_size, endianness, signed,
                factor, math_offset, unit, comment, is_heuristic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                offset=excluded.offset,
                rows=excluded.rows,
                columns=excluded.columns,
                cell_size=excluded.cell_size,
                endianness=excluded.endianness,
                signed=excluded.signed,
                factor=excluded.factor,
                math_offset=excluded.math_offset,
                unit=excluded.unit,
                comment=excluded.comment,
                is_heuristic=excluded.is_heuristic
            """,
            (
                definition.name,
                definition.offset,
                definition.rows,
                definition.columns,
                definition.cell_size,
                definition.endianness,
                int(definition.signed),
                definition.factor,
                definition.math_offset,
                definition.unit,
                definition.comment,
                int(definition.is_heuristic),
            ),
        )
        self._connection.commit()

    def load_map(self, name: str) -> MapDefinition | None:
        row = self._connection.execute(
            "SELECT * FROM maps WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_definition(row)

    def list_maps(self) -> list[MapDefinition]:
        rows = self._connection.execute("SELECT * FROM maps ORDER BY name").fetchall()
        return [self._row_to_definition(row) for row in rows]

    def delete_map(self, name: str) -> bool:
        cursor = self._connection.execute("DELETE FROM maps WHERE name = ?", (name,))
        self._connection.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_definition(row: tuple) -> MapDefinition:
        (
            name, offset, rows, columns, cell_size, endianness, signed,
            factor, math_offset, unit, comment, is_heuristic,
        ) = row
        return MapDefinition(
            name=name,
            offset=offset,
            rows=rows,
            columns=columns,
            cell_size=cell_size,
            endianness=endianness,
            signed=bool(signed),
            factor=factor,
            math_offset=math_offset,
            unit=unit,
            comment=comment,
            is_heuristic=bool(is_heuristic),
        )


#: A handful of map names commonly referenced in tuning documentation,
#: seeded as EMPTY placeholders the user fills in themselves - never
#: auto-detected offsets. See AGENTS.md section 10.
SUGGESTED_MAP_NAMES = ("RPM", "Load", "Ignition", "Fuel", "Temperature")
