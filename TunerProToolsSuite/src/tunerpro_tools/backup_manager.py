"""BIN Backup Manager core logic.

Rules enforced here (see AGENTS.md / SAFETY.md):
- an original BIN is never overwritten;
- every write-oriented operation happens on a timestamped copy;
- restoring means copying the preserved original back out, never
  mutating it in place.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import get_config


@dataclass(frozen=True)
class BackupRecord:
    original_path: Path
    backup_path: Path
    kind: str  # "original" or "modified"
    timestamp: str


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_file(source: str | Path, *, kind: str = "original") -> BackupRecord:
    """Copy ``source`` into Backups/<kind>/ with a date-time stamped name.

    The source file is opened read-only; it is never touched.
    """
    if kind not in ("original", "modified"):
        raise ValueError("kind must be 'original' or 'modified'")

    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(source)

    config = get_config()
    config.ensure_layout()
    destination_dir = (
        config.backups_original_dir if kind == "original" else config.backups_modified_dir
    )

    timestamp = _timestamp()
    backup_name = f"{source.stem}_{timestamp}{source.suffix}"
    destination = destination_dir / backup_name

    if destination.exists():
        raise FileExistsError(f"Backup already exists: {destination}")

    shutil.copy2(source, destination)

    return BackupRecord(
        original_path=source, backup_path=destination, kind=kind, timestamp=timestamp
    )


def list_backups(kind: str = "original") -> list[Path]:
    config = get_config()
    directory = config.backups_original_dir if kind == "original" else config.backups_modified_dir
    if not directory.exists():
        return []
    return sorted(directory.glob("*"))


def restore_original(backup_path: str | Path, destination: str | Path) -> Path:
    """Copy a preserved backup back out to ``destination``.

    Refuses to silently overwrite an existing, different file at
    ``destination`` - callers must explicitly confirm overwrite by
    deleting/moving it first, keeping "never overwrite accidentally".
    """
    backup_path = Path(backup_path)
    destination = Path(destination)
    if not backup_path.exists():
        raise FileNotFoundError(backup_path)
    if destination.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing file: {destination}. "
            "Move or rename it first, then restore."
        )
    shutil.copy2(backup_path, destination)
    return destination
