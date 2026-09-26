#!/usr/bin/env python3
"""Dashboard - single entry point that launches every other tool.

Each tool is started as an independent external process (its own .exe
once built, or its main.py during development), matching how TunerPro's
Custom Tools menu will launch them - see TunerPro_CustomTools_Setup.txt.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

TOOLS_ROOT = Path(__file__).resolve().parents[1]

from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.widgets.common import show_error

TOOLS = [
    ("BIN Analyzer", "bin_analyzer"),
    ("BIN Compare", "bin_compare"),
    ("Map Viewer", "map_viewer"),
    ("Lambda AFR Calculator", "lambda_afr_calculator"),
    ("Calibration Diff", "calibration_diff"),
    ("Value Converter", "value_converter"),
    ("Checksum Analyzer", "checksum_analyzer"),
    ("BIN Backup Manager", "backup_manager"),
    ("Map Database", "map_database"),
    ("Calibration Session", "session_manager"),
    ("Calibration Workbench", "calibration_workbench"),
    ("Vehicle Simulator", "vehicle_simulator"),
]


class DashboardWindow(ToolWindow):
    def __init__(self):
        super().__init__("dashboard", "TunerPro Tools Suite - Dashboard", mode="ANALYSE")

        intro = QLabel(
            "Selectionnez un outil ci-dessous. Chaque outil s'ouvre dans sa propre "
            "fenetre, comme il le ferait lance depuis le menu Custom Tools de TunerPro."
        )
        intro.setWordWrap(True)
        self.content_layout.addWidget(intro)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        for index, (label, tool_dir) in enumerate(TOOLS):
            button = QPushButton(label)
            button.setMinimumHeight(48)
            button.clicked.connect(lambda _checked=False, d=tool_dir, l=label: self._launch(d, l))
            grid.addWidget(button, index // 2, index % 2)
        self.content_layout.addWidget(grid_widget)
        self.content_layout.addStretch(1)

    def _launch(self, tool_dir: str, label: str) -> None:
        exe_path = TOOLS_ROOT / tool_dir / f"{tool_dir}.exe"
        script_path = TOOLS_ROOT / tool_dir / "main.py"
        try:
            if exe_path.exists():
                subprocess.Popen([str(exe_path)])
            elif script_path.exists():
                subprocess.Popen([sys.executable, str(script_path)])
            else:
                raise FileNotFoundError(f"Aucun executable ou script trouve pour {label}")
        except OSError as exc:
            show_error(self, "Erreur de lancement", f"Impossible de lancer {label} :\n{exc}")
            log_operation(self.logger, "launch_tool", tool_dir, error=str(exc))
            return
        log_operation(self.logger, "launch_tool", tool_dir)
        self.set_status(f"{label} lance.")


def main() -> int:
    return run_app(DashboardWindow)


if __name__ == "__main__":
    sys.exit(main())
