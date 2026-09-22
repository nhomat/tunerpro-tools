#!/usr/bin/env python3
"""Checksum Analyzer - compute/compare checksums over a BIN zone.

This tool NEVER writes a recomputed checksum back into a file
automatically - see AGENTS.md section 8. Any such write would require a
separate, explicit user action outside this tool's current scope.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.checksum import ALGORITHMS, compute_checksum
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.widgets.common import BinFileDropField, read_file_with_progress, show_error


class ChecksumAnalyzerWindow(ToolWindow):
    def __init__(self):
        super().__init__("checksum_analyzer", "Checksum Analyzer", mode="ANALYSE")
        self.data: bytes | None = None

        self.path_field = BinFileDropField()
        self.path_field.fileSelected.connect(self._load)
        self.content_layout.addWidget(self.path_field)

        config_box = QGroupBox("Zone et algorithme")
        form = QFormLayout(config_box)

        self.algo_combo = QComboBox()
        for algo in ALGORITHMS.values():
            self.algo_combo.addItem(algo.label, algo.key)
        form.addRow("Algorithme :", self.algo_combo)

        self.zone_start_spin = QSpinBox()
        self.zone_start_spin.setMaximum(0x7FFFFFFF)
        self.zone_start_spin.setDisplayIntegerBase(16)
        self.zone_start_spin.setPrefix("0x")
        form.addRow("Debut de zone :", self.zone_start_spin)

        self.zone_end_spin = QSpinBox()
        self.zone_end_spin.setMaximum(0x7FFFFFFF)
        self.zone_end_spin.setDisplayIntegerBase(16)
        self.zone_end_spin.setPrefix("0x")
        form.addRow("Fin de zone (exclue) :", self.zone_end_spin)

        self.check_stored = QCheckBox("Comparer avec une valeur stockee dans le fichier")
        form.addRow(self.check_stored)

        self.checksum_offset_spin = QSpinBox()
        self.checksum_offset_spin.setMaximum(0x7FFFFFFF)
        self.checksum_offset_spin.setDisplayIntegerBase(16)
        self.checksum_offset_spin.setPrefix("0x")
        form.addRow("Offset du checksum stocke :", self.checksum_offset_spin)

        self.byte_order_combo = QComboBox()
        self.byte_order_combo.addItems(["big", "little"])
        form.addRow("Ordre des octets stockes :", self.byte_order_combo)

        compute_btn = QPushButton("Calculer")
        compute_btn.clicked.connect(self._compute)
        form.addRow(compute_btn)

        self.content_layout.addWidget(config_box)

        result_box = QGroupBox("Resultat")
        result_layout = QVBoxLayout(result_box)
        self.computed_label = QLabel("-")
        self.stored_label = QLabel("-")
        self.match_label = QLabel("-")
        result_layout.addWidget(self.computed_label)
        result_layout.addWidget(self.stored_label)
        result_layout.addWidget(self.match_label)
        self.content_layout.addWidget(result_box)
        self.content_layout.addStretch(1)

    def _load(self, path: str) -> None:
        try:
            self.data = read_file_with_progress(self, path, "Lecture du fichier...")
        except OSError as exc:
            show_error(self, "Erreur", f"Impossible d'ouvrir le fichier :\n{exc}")
            return
        self.zone_end_spin.setValue(len(self.data))
        self.checksum_offset_spin.setValue(max(len(self.data) - 4, 0))
        log_operation(self.logger, "open_file", path)
        self.set_status(f"{path} charge ({len(self.data)} octets).")

    def _compute(self) -> None:
        if self.data is None:
            show_error(self, "Aucun fichier", "Ouvrez d'abord un fichier BIN.")
            return
        checksum_offset = self.checksum_offset_spin.value() if self.check_stored.isChecked() else None
        try:
            result = compute_checksum(
                self.data,
                self.algo_combo.currentData(),
                self.zone_start_spin.value(),
                self.zone_end_spin.value(),
                checksum_offset=checksum_offset,
                byte_order=self.byte_order_combo.currentText(),
            )
        except ValueError as exc:
            show_error(self, "Parametres invalides", str(exc))
            return

        self.computed_label.setText(f"Checksum calcule : {result.computed_hex}")
        if result.stored_value is not None:
            self.stored_label.setText(f"Checksum stocke : {result.stored_hex}")
            self.match_label.setText(
                "Correspondance : OUI" if result.matches else "Correspondance : NON"
            )
        else:
            self.stored_label.setText("Checksum stocke : (non compare)")
            self.match_label.setText("")
        log_operation(self.logger, "compute_checksum", str(Path(self.path_field.path())))


def main() -> int:
    return run_app(ChecksumAnalyzerWindow)


if __name__ == "__main__":
    sys.exit(main())
