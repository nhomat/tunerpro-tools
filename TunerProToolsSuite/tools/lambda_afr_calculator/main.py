#!/usr/bin/env python3
"""Lambda AFR Calculator - theoretical AFR <-> Lambda conversions."""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.lambda_afr import (
    FUEL_PROFILES,
    THEORETICAL_DISCLAIMER,
    afr_to_lambda,
    common_conversion_table,
    lambda_to_afr,
)
from tunerpro_tools.logging_utils import log_operation


class LambdaAfrWindow(ToolWindow):
    def __init__(self):
        super().__init__("lambda_afr_calculator", "Lambda AFR Calculator", mode="SIMULATION")

        disclaimer = QLabel(THEORETICAL_DISCLAIMER)
        disclaimer.setObjectName("WarningBanner")
        disclaimer.setWordWrap(True)
        self.content_layout.addWidget(disclaimer)

        fuel_row = QHBoxLayout()
        fuel_row.addWidget(QLabel("Carburant :"))
        self.fuel_combo = QComboBox()
        for profile in FUEL_PROFILES.values():
            self.fuel_combo.addItem(profile.label, profile.key)
        self.fuel_combo.currentIndexChanged.connect(self._refresh_all)
        fuel_row.addWidget(self.fuel_combo)
        fuel_row.addStretch(1)
        self.content_layout.addLayout(fuel_row)

        converters_row = QHBoxLayout()

        afr_box = QGroupBox("AFR -> Lambda")
        afr_form = QFormLayout(afr_box)
        self.afr_input = QDoubleSpinBox()
        self.afr_input.setRange(0.1, 100.0)
        self.afr_input.setValue(14.7)
        self.afr_input.valueChanged.connect(self._refresh_from_afr)
        afr_form.addRow("AFR :", self.afr_input)
        self.afr_result_label = QLabel("-")
        afr_form.addRow("Lambda :", self.afr_result_label)
        converters_row.addWidget(afr_box)

        lambda_box = QGroupBox("Lambda -> AFR")
        lambda_form = QFormLayout(lambda_box)
        self.lambda_input = QDoubleSpinBox()
        self.lambda_input.setRange(0.01, 10.0)
        self.lambda_input.setSingleStep(0.01)
        self.lambda_input.setValue(1.0)
        self.lambda_input.valueChanged.connect(self._refresh_from_lambda)
        lambda_form.addRow("Lambda :", self.lambda_input)
        self.lambda_result_label = QLabel("-")
        lambda_form.addRow("AFR :", self.lambda_result_label)
        converters_row.addWidget(lambda_box)

        self.content_layout.addLayout(converters_row)

        self.content_layout.addWidget(QLabel("Conversions courantes :"))
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Lambda", "AFR"])
        self.content_layout.addWidget(self.table, 1)

        self._refresh_all()

    def _current_fuel(self) -> str:
        return self.fuel_combo.currentData()

    def _refresh_from_afr(self) -> None:
        value = afr_to_lambda(self.afr_input.value(), self._current_fuel())
        self.afr_result_label.setText(f"{value:.4f}")
        log_operation(self.logger, "afr_to_lambda")

    def _refresh_from_lambda(self) -> None:
        value = lambda_to_afr(self.lambda_input.value(), self._current_fuel())
        self.lambda_result_label.setText(f"{value:.4f}")
        log_operation(self.logger, "lambda_to_afr")

    def _refresh_all(self) -> None:
        self._refresh_from_afr()
        self._refresh_from_lambda()
        table_rows = common_conversion_table(self._current_fuel())
        self.table.setRowCount(len(table_rows))
        for row, (lam, afr) in enumerate(table_rows):
            self.table.setItem(row, 0, QTableWidgetItem(f"{lam:.2f}"))
            self.table.setItem(row, 1, QTableWidgetItem(f"{afr:.3f}"))


def main() -> int:
    return run_app(LambdaAfrWindow)


if __name__ == "__main__":
    sys.exit(main())
