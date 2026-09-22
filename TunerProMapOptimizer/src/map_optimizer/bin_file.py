"""Minimal read-only BIN file access (mirrors tunerpro_tools.bin_file)."""
from __future__ import annotations

from pathlib import Path


class BinFile:
    def __init__(self, path: str | Path, data: bytes):
        self.path = Path(path)
        self.data = data

    @classmethod
    def load(cls, path: str | Path) -> "BinFile":
        path = Path(path)
        with path.open("rb") as handle:
            return cls(path, handle.read())

    @property
    def size(self) -> int:
        return len(self.data)
