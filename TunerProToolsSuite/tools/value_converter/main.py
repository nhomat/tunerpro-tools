#!/usr/bin/env python3
"""Value Converter - HEX / DEC / BIN / intN, little/big endian."""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.converter import INT_TYPES, convert_all_types, parse_input_value
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.widgets.common import show_error


class ValueConverterWindow(ToolWindow):
    def __init__(self):
        super().__init__("value_converter", "Value Converter", mode="ANALYSE")

        input_box = QGroupBox("Valeur d'entree")
        input_layout = QHBoxLayout(input_box)
        input_layout.addWidget(QLabel("Base :"))
        self.base_combo = QComboBox()
        self.base_combo.addItems(["hex", "dec", "bin"])
        input_layout.addWidget(self.base_combo)
        input_layout.addWidget(QLabel("Valeur :"))
        self.value_edit = QLineEdit("FF")
        self.value_edit.returnPressed.connect(self._convert)
        input_layout.addWidget(self.value_edit, 1)
        input_layout.addWidget(QLabel("Endianess :"))
        self.endian_combo = QComboBox()
        self.endian_combo.addItems(["little", "big"])
        input_layout.addWidget(self.endian_combo)
        convert_btn = QPushButton("Convertir")
        convert_btn.clicked.connect(self._convert)
        input_layout.addWidget(convert_btn)
        self.content_layout.addWidget(input_box)

        self.table = QTableWidget(len(INT_TYPES), 4)
        self.table.setHorizontalHeaderLabels(["Type", "HEX", "DEC", "BIN"])
        for row, type_name in enumerate(INT_TYPES):
            self.table.setItem(row, 0, QTableWidgetItem(type_name))
        self.content_layout.addWidget(self.table, 1)

        self._convert()

    def _convert(self) -> None:
        try:
            value = parse_input_value(self.value_edit.text(), self.base_combo.currentText())
        except ValueError as exc:
            show_error(self, "Entree invalide", str(exc))
            return

        byte_order = self.endian_combo.currentText()
        results = convert_all_types(value, byte_order=byte_order)
        for row, type_name in enumerate(INT_TYPES):
            result = results[type_name]
            if isinstance(result, str):
                self.table.setItem(row, 1, QTableWidgetItem("-"))
                self.table.setItem(row, 2, QTableWidgetItem("hors plage"))
                self.table.setItem(row, 3, QTableWidgetItem("-"))
            else:
                self.table.setItem(row, 1, QTableWidgetItem(result.hex_value))
                self.table.setItem(row, 2, QTableWidgetItem(str(result.dec_value)))
                self.table.setItem(row, 3, QTableWidgetItem(result.bin_value))
        log_operation(self.logger, "convert_value")
        self.set_status(f"Valeur convertie : {value}")


def main() -> int:
    return run_app(ValueConverterWindow)


if __name__ == "__main__":
    sys.exit(main())
