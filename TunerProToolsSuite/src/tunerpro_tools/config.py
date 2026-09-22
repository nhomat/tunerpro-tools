"""Centralized configuration and filesystem layout for the suite.

All tools resolve their working directories (logs, backups, reports,
projects) through this module instead of hard-coding paths, so the
layout only needs to change in one place.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

APP_NAME = "TunerPro Tools Suite"
APP_VERSION = "0.1.0"

#: Experimental-modification warning shown by every write-capable tool.
EXPERIMENTAL_WARNING = (
    "Cette modification est experimentale. Verifiez la compatibilite du "
    "fichier, du calculateur et du materiel avant toute utilisation reelle."
)


def _default_root() -> Path:
    """Return the suite's data root.

    On Windows this is ``C:\\TunerProToolsSuite``, matching the installer
    layout described in INSTALLATION.md. Elsewhere (development, CI, this
    Linux build environment) it falls back to a folder next to the
    source tree so the tools remain runnable without an installer.
    """
    env_root = os.environ.get("TUNERPRO_TOOLS_ROOT")
    if env_root:
        return Path(env_root)
    if os.name == "nt":
        return Path("C:/TunerProToolsSuite")
    return Path(__file__).resolve().parents[2] / "runtime_data"


@dataclass
class SuiteConfig:
    """Resolved, ready-to-use directory layout for one suite installation."""

    root: Path = field(default_factory=_default_root)

    @property
    def tools_dir(self) -> Path:
        return self.root / "Tools"

    @property
    def config_dir(self) -> Path:
        return self.root / "Config"

    @property
    def backups_dir(self) -> Path:
        return self.root / "Backups"

    @property
    def backups_original_dir(self) -> Path:
        return self.backups_dir / "original"

    @property
    def backups_modified_dir(self) -> Path:
        return self.backups_dir / "modified"

    @property
    def backups_reports_dir(self) -> Path:
        return self.backups_dir / "reports"

    @property
    def reports_dir(self) -> Path:
        return self.root / "Reports"

    @property
    def projects_dir(self) -> Path:
        return self.root / "Projects"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def map_database_path(self) -> Path:
        return self.config_dir / "map_database.sqlite3"

    def ensure_layout(self) -> None:
        """Create every directory the suite expects, idempotently."""
        for directory in (
            self.tools_dir,
            self.config_dir,
            self.backups_original_dir,
            self.backups_modified_dir,
            self.backups_reports_dir,
            self.reports_dir,
            self.projects_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def as_dict(self) -> dict:
        data = asdict(self)
        data["root"] = str(self.root)
        return data


_CONFIG: SuiteConfig | None = None


def get_config() -> SuiteConfig:
    """Return the process-wide :class:`SuiteConfig`, creating it on first use."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = SuiteConfig()
        _CONFIG.ensure_layout()
    return _CONFIG


def load_default_config_file() -> dict:
    """Load ``config/default_config.json`` shipped alongside the source tree."""
    default_path = Path(__file__).resolve().parents[2] / "config" / "default_config.json"
    if not default_path.exists():
        return {}
    with default_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
