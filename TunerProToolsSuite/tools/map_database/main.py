#!/usr/bin/env python3
"""Map Database - save/recall MapDefinition configurations.

Never auto-detects or invents maps from a BIN's content: every entry is
saved because a user defined and validated it (see AGENTS.md section
10 - a heuristic detection, if ever added, must show
map_model.PROBABLE_MAP_NOTICE and never be presented as certain).
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
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.map_database import SUGGESTED_MAP_NAMES, MapDatabase
from tunerpro_tools.map_model import MapDefinition
from tunerpro_tools.widgets.common import confirm_destructive_action, show_error


class MapDatabaseWindow(ToolWindow):
    def __init__(self):
        super().__init__("map_database", "Map Database", mode="ANALYSE")
        self.db = MapDatabase()

        body = QHBoxLayout()

        list_box = QGroupBox("Maps enregistrees")
        list_layout = QVBoxLayout(list_box)
        self.map_list = QListWidget()
        self.map_list.currentTextChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self.map_list, 1)
        hint_label = QLabel(
            "Suggestions courantes : " + ", ".join(SUGGESTED_MAP_NAMES) +
            " (a definir manuellement - jamais detectees automatiquement)"
        )
        hint_label.setWordWrap(True)
        list_layout.addWidget(hint_label)
        delete_btn = QPushButton("Supprimer")
        delete_btn.clicked.connect(self._delete_selected)
        list_layout.addWidget(delete_btn)
        body.addWidget(list_box, 1)

        form_box = QGroupBox("Details de la map")
        form = QFormLayout(form_box)
        self.name_edit = QLineEdit()
        form.addRow("Nom :", self.name_edit)
        self.offset_spin = QSpinBox()
        self.offset_spin.setMaximum(0x7FFFFFFF)
        self.offset_spin.setDisplayIntegerBase(16)
        self.offset_spin.setPrefix("0x")
        form.addRow("Offset :", self.offset_spin)
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 512)
        form.addRow("Lignes :", self.rows_spin)
        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(1, 512)
        form.addRow("Colonnes :", self.columns_spin)
        self.cell_size_combo = QComboBox()
        self.cell_size_combo.addItems(["1", "2", "4"])
        form.addRow("Taille cellule :", self.cell_size_combo)
        self.endianness_combo = QComboBox()
        self.endianness_combo.addItems(["little", "big"])
        form.addRow("Endianess :", self.endianness_combo)
        self.signed_check = QCheckBox("Signe")
        form.addRow(self.signed_check)
        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(-1e9, 1e9)
        self.factor_spin.setDecimals(6)
        self.factor_spin.setValue(1.0)
        form.addRow("Facteur :", self.factor_spin)
        self.math_offset_spin = QDoubleSpinBox()
        self.math_offset_spin.setRange(-1e9, 1e9)
        self.math_offset_spin.setDecimals(6)
        form.addRow("Offset mathematique :", self.math_offset_spin)
        self.unit_edit = QLineEdit()
        form.addRow("Unite :", self.unit_edit)
        self.comment_edit = QLineEdit()
        form.addRow("Commentaire :", self.comment_edit)
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._save)
        form.addRow(save_btn)
        body.addWidget(form_box, 1)

        self.content_layout.addLayout(body)
        self._refresh_list()

    def _refresh_list(self) -> None:
        self.map_list.clear()
        for definition in self.db.list_maps():
            self.map_list.addItem(definition.name)

    def _on_selection_changed(self, name: str) -> None:
        if not name:
            return
        definition = self.db.load_map(name)
        if definition is None:
            return
        self.name_edit.setText(definition.name)
        self.offset_spin.setValue(definition.offset)
        self.rows_spin.setValue(definition.rows)
        self.columns_spin.setValue(definition.columns)
        self.cell_size_combo.setCurrentText(str(definition.cell_size))
        self.endianness_combo.setCurrentText(definition.endianness)
        self.signed_check.setChecked(definition.signed)
        self.factor_spin.setValue(definition.factor)
        self.math_offset_spin.setValue(definition.math_offset)
        self.unit_edit.setText(definition.unit)
        self.comment_edit.setText(definition.comment)

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            show_error(self, "Nom requis", "Indiquez un nom pour cette map.")
            return
        try:
            definition = MapDefinition(
                name=name,
                offset=self.offset_spin.value(),
                rows=self.rows_spin.value(),
                columns=self.columns_spin.value(),
                cell_size=int(self.cell_size_combo.currentText()),
                endianness=self.endianness_combo.currentText(),
                signed=self.signed_check.isChecked(),
                factor=self.factor_spin.value(),
                math_offset=self.math_offset_spin.value(),
                unit=self.unit_edit.text(),
                comment=self.comment_edit.text(),
            )
        except ValueError as exc:
            show_error(self, "Configuration invalide", str(exc))
            return
        self.db.save_map(definition)
        log_operation(self.logger, "save_map", name)
        self.set_status(f"Map '{name}' enregistree.")
        self._refresh_list()

    def _delete_selected(self) -> None:
        item = self.map_list.currentItem()
        if item is None:
            show_error(self, "Aucune selection", "Selectionnez une map a supprimer.")
            return
        name = item.text()
        if not confirm_destructive_action(self, "Confirmer la suppression", f"Supprimer la map '{name}' ?"):
            return
        self.db.delete_map(name)
        log_operation(self.logger, "delete_map", name)
        self._refresh_list()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.db.close()
        super().closeEvent(event)


def main() -> int:
    return run_app(MapDatabaseWindow)


if __name__ == "__main__":
    sys.exit(main())
