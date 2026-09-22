#!/usr/bin/env python3
"""Calibration Diff - compare a map region between two BIN files.

Variation is reported with neutral labels only (faible / moderee /
importante) - never "safe"/"dangerous"/"good"/"bad": see AGENTS.md
section 6 and tunerpro_tools.compare.classify_variation.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.compare import VariationLevel, classify_variation
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.map_model import MapDefinition, extract_map
from tunerpro_tools.widgets.common import BinFileDropField, read_file_with_progress, show_error

_LEVEL_COLORS = {
    VariationLevel.LOW: QColor(40, 70, 40),
    VariationLevel.MODERATE: QColor(90, 80, 30),
    VariationLevel.HIGH: QColor(100, 40, 40),
}


class CalibrationDiffWindow(ToolWindow):
    def __init__(self):
        super().__init__("calibration_diff", "Calibration Diff", mode="ANALYSE")
        self.original_data: bytes | None = None
        self.modified_data: bytes | None = None

        files_box = QGroupBox("Fichiers")
        files_layout = QVBoxLayout(files_box)
        files_layout.addWidget(QLabel("Calibration originale :"))
        self.original_field = BinFileDropField()
        self.original_field.fileSelected.connect(lambda p: self._load(p, is_original=True))
        files_layout.addWidget(self.original_field)
        files_layout.addWidget(QLabel("Calibration modifiee :"))
        self.modified_field = BinFileDropField()
        self.modified_field.fileSelected.connect(lambda p: self._load(p, is_original=False))
        files_layout.addWidget(self.modified_field)
        self.content_layout.addWidget(files_box)

        config_box = QGroupBox("Zone de la map")
        form = QFormLayout(config_box)
        self.offset_spin = QSpinBox()
        self.offset_spin.setMaximum(0x7FFFFFFF)
        self.offset_spin.setDisplayIntegerBase(16)
        self.offset_spin.setPrefix("0x")
        form.addRow("Offset :", self.offset_spin)
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 512)
        self.rows_spin.setValue(16)
        form.addRow("Lignes :", self.rows_spin)
        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(1, 512)
        self.columns_spin.setValue(16)
        form.addRow("Colonnes :", self.columns_spin)
        self.cell_size_combo = QComboBox()
        self.cell_size_combo.addItems(["1", "2", "4"])
        form.addRow("Taille cellule :", self.cell_size_combo)
        self.endianness_combo = QComboBox()
        self.endianness_combo.addItems(["little", "big"])
        form.addRow("Endianess :", self.endianness_combo)
        self.signed_check = QCheckBox("Signe")
        form.addRow(self.signed_check)
        compute_btn = QPushButton("Comparer la zone")
        compute_btn.clicked.connect(self._compute)
        form.addRow(compute_btn)
        self.content_layout.addWidget(config_box)

        summary_box = QGroupBox("Resume")
        summary_layout = QVBoxLayout(summary_box)
        self.cells_modified_label = QLabel("-")
        self.mean_label = QLabel("-")
        self.max_label = QLabel("-")
        self.min_label = QLabel("-")
        for label in (self.cells_modified_label, self.mean_label, self.max_label, self.min_label):
            summary_layout.addWidget(label)
        self.content_layout.addWidget(summary_box)

        self.content_layout.addWidget(QLabel("Heatmap des variations (survol : voir la legende ci-dessous)"))
        self.heatmap = QTableWidget()
        self.content_layout.addWidget(self.heatmap, 1)

        legend_row = QHBoxLayout()
        for level, color in _LEVEL_COLORS.items():
            swatch = QLabel(f"  {level.value}  ")
            swatch.setStyleSheet(f"background-color: {color.name()}; color: white;")
            legend_row.addWidget(swatch)
        legend_row.addStretch(1)
        self.content_layout.addLayout(legend_row)

    def _load(self, path: str, *, is_original: bool) -> None:
        try:
            data = read_file_with_progress(self, path, "Lecture du fichier...")
        except OSError as exc:
            show_error(self, "Erreur", f"Impossible d'ouvrir le fichier :\n{exc}")
            return
        if is_original:
            self.original_data = data
        else:
            self.modified_data = data
        log_operation(self.logger, "open_file", path)

    def _compute(self) -> None:
        if self.original_data is None or self.modified_data is None:
            show_error(self, "Fichiers manquants", "Chargez une calibration originale et une modifiee.")
            return

        definition = MapDefinition(
            name="Zone",
            offset=self.offset_spin.value(),
            rows=self.rows_spin.value(),
            columns=self.columns_spin.value(),
            cell_size=int(self.cell_size_combo.currentText()),
            endianness=self.endianness_combo.currentText(),
            signed=self.signed_check.isChecked(),
        )
        try:
            original_map = extract_map(self.original_data, definition)
            modified_map = extract_map(self.modified_data, definition)
        except ValueError as exc:
            show_error(self, "Configuration invalide", str(exc))
            return

        deltas = []
        self.heatmap.setRowCount(definition.rows)
        self.heatmap.setColumnCount(definition.columns)
        for r in range(definition.rows):
            for c in range(definition.columns):
                original_value = original_map.raw[r][c]
                modified_value = modified_map.raw[r][c]
                delta = modified_value - original_value
                item = QTableWidgetItem(str(delta) if delta else "")
                item.setTextAlignment(Qt.AlignCenter)
                if delta != 0:
                    deltas.append(delta)
                    percent = None if original_value == 0 else (delta / original_value) * 100
                    level = classify_variation(percent, absolute_delta=delta)
                    item.setBackground(QBrush(_LEVEL_COLORS[level]))
                self.heatmap.setItem(r, c, item)

        modified_cells = len(deltas)
        self.cells_modified_label.setText(f"Cellules modifiees : {modified_cells}")
        if deltas:
            self.mean_label.setText(f"Variation moyenne : {sum(deltas) / len(deltas):.2f}")
            self.max_label.setText(f"Variation maximale : {max(deltas)}")
            self.min_label.setText(f"Variation minimale : {min(deltas)}")
        else:
            self.mean_label.setText("Variation moyenne : 0")
            self.max_label.setText("Variation maximale : 0")
            self.min_label.setText("Variation minimale : 0")

        log_operation(self.logger, "calibration_diff")


def main() -> int:
    return run_app(CalibrationDiffWindow)


if __name__ == "__main__":
    sys.exit(main())
