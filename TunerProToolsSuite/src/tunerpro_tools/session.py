"""Calibration Session project format (.tpsuite).

A session bundles references to the original/modified BIN, the map
configurations used, free-form notes, report paths and a modification
history - stored as gzip-compressed JSON so the format stays both
inspectable (it's just JSON) and compact.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .map_model import MapDefinition

SESSION_EXTENSION = ".tpsuite"
SESSION_FORMAT_VERSION = 1


@dataclass
class HistoryEntry:
    timestamp: str
    action: str
    detail: str = ""


@dataclass
class CalibrationSession:
    name: str
    original_bin_path: str | None = None
    modified_bin_path: str | None = None
    maps: list[MapDefinition] = field(default_factory=list)
    notes: str = ""
    report_paths: list[str] = field(default_factory=list)
    history: list[HistoryEntry] = field(default_factory=list)

    def record(self, action: str, detail: str = "") -> None:
        self.history.append(
            HistoryEntry(timestamp=datetime.now().isoformat(timespec="seconds"), action=action, detail=detail)
        )

    def to_dict(self) -> dict:
        return {
            "format_version": SESSION_FORMAT_VERSION,
            "name": self.name,
            "original_bin_path": self.original_bin_path,
            "modified_bin_path": self.modified_bin_path,
            "maps": [m.to_dict() for m in self.maps],
            "notes": self.notes,
            "report_paths": self.report_paths,
            "history": [asdict(h) for h in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationSession":
        session = cls(
            name=data["name"],
            original_bin_path=data.get("original_bin_path"),
            modified_bin_path=data.get("modified_bin_path"),
            maps=[MapDefinition.from_dict(m) for m in data.get("maps", [])],
            notes=data.get("notes", ""),
            report_paths=data.get("report_paths", []),
        )
        session.history = [HistoryEntry(**h) for h in data.get("history", [])]
        return session

    def save(self, path: str | Path) -> None:
        path = Path(path)
        payload = json.dumps(self.to_dict(), indent=2).encode("utf-8")
        with gzip.open(path, "wb") as handle:
            handle.write(payload)

    @classmethod
    def load(cls, path: str | Path) -> "CalibrationSession":
        path = Path(path)
        with gzip.open(path, "rb") as handle:
            data = json.loads(handle.read().decode("utf-8"))
        return cls.from_dict(data)
