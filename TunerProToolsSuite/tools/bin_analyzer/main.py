#!/usr/bin/env python3
"""BIN Analyzer - inspect a .bin file: stats, entropy, hex view, search.

Read-only tool. Opening a file never modifies it.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.bin_file import BinFile
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.report import save_analysis_report_html, save_analysis_report_json
from tunerpro_tools.widgets.common import BinFileDropField, read_file_with_progress, show_error


class BinAnalyzerWindow(ToolWindow):
    def __init__(self):
        super().__init__("bin_analyzer", "BIN Analyzer", mode="ANALYSE")
        self.bin_file: BinFile | None = None

        self.path_field = BinFileDropField()
        self.path_field.fileSelected.connect(self.load_file)
        self.content_layout.addWidget(self.path_field)

        self.tabs = QTabWidget()
        self.content_layout.addWidget(self.tabs, 1)

        self._build_stats_tab()
        self._build_hex_tab()
        self._build_search_tab()

        self.add_shortcut("Ctrl+O", self._browse_file, "Ouvrir")
        self.add_shortcut("Ctrl+G", lambda: self.offset_spin.setFocus(), "Aller a l'offset")

    # ------------------------------------------------------------------
    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un BIN", "", "Fichiers BIN (*.bin);;Tous (*)")
        if path:
            self.path_field.set_path(path)

    def load_file(self, path: str) -> None:
        try:
            data = read_file_with_progress(self, path, "Lecture du fichier...")
            self.bin_file = BinFile(path, data)
        except OSError as exc:
            show_error(self, "Erreur", f"Impossible d'ouvrir le fichier :\n{exc}")
            log_operation(self.logger, "open_file", path, error=str(exc))
            return

        log_operation(self.logger, "open_file", path)
        self.set_status(f"{path} charge ({self.bin_file.size} octets).")
        self.offset_spin.setMaximum(max(self.bin_file.size - 1, 0))
        self._refresh_stats()
        self._refresh_hex()

    # ------------------------------------------------------------------
    def _build_stats_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_box = QGroupBox("Statistiques generales")
        form = QFormLayout(form_box)
        self.size_label = QLabel("-")
        self.count_label = QLabel("-")
        self.unique_label = QLabel("-")
        self.minmax_label = QLabel("-")
        self.mean_label = QLabel("-")
        self.entropy_label = QLabel("-")
        form.addRow("Taille du fichier :", self.size_label)
        form.addRow("Nombre d'octets :", self.count_label)
        form.addRow("Valeurs uniques :", self.unique_label)
        form.addRow("Min / Max :", self.minmax_label)
        form.addRow("Moyenne :", self.mean_label)
        form.addRow("Entropie :", self.entropy_label)
        layout.addWidget(form_box)

        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setMinimumHeight(280)
        layout.addWidget(self.chart_view, 1)

        export_row = QHBoxLayout()
        export_html_btn = QPushButton("Save Analysis Report (HTML)")
        export_html_btn.clicked.connect(lambda: self._save_report("html"))
        export_json_btn = QPushButton("Save Analysis Report (JSON)")
        export_json_btn.clicked.connect(lambda: self._save_report("json"))
        export_row.addWidget(export_html_btn)
        export_row.addWidget(export_json_btn)
        export_row.addStretch(1)
        layout.addLayout(export_row)

        self.tabs.addTab(tab, "Statistiques")

    def _refresh_stats(self) -> None:
        if not self.bin_file:
            return
        stats = self.bin_file.compute_stats()
        self.size_label.setText(f"{stats.size} octets")
        self.count_label.setText(str(stats.size))
        self.unique_label.setText(str(stats.unique_values))
        self.minmax_label.setText(f"{stats.minimum} / {stats.maximum}")
        self.mean_label.setText(f"{stats.mean:.2f}")
        self.entropy_label.setText(f"{stats.entropy:.4f} bits/octet")

        chart = QChart()
        chart.setTitle("Histogramme des octets (regroupe par 16)")
        chart.legend().hide()
        bar_set = QBarSet("Occurrences")
        buckets = [0] * 16
        for value, count in enumerate(stats.histogram):
            buckets[value // 16] += count
        bar_set.append(buckets)
        series = QBarSeries()
        series.append(bar_set)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append([f"{i*16:02X}" for i in range(16)])
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        self.chart_view.setChart(chart)

    def _save_report(self, kind: str) -> None:
        if not self.bin_file:
            show_error(self, "Aucun fichier", "Ouvrez d'abord un fichier BIN.")
            return
        stats = self.bin_file.compute_stats()
        default_name = f"{Path(self.bin_file.path).stem}_report.{kind}"
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le rapport", default_name)
        if not path:
            return
        if kind == "html":
            save_analysis_report_html(self.bin_file.path, stats, path)
        else:
            save_analysis_report_json(self.bin_file.path, stats, path)
        log_operation(self.logger, f"save_report_{kind}", path)
        self.set_status(f"Rapport enregistre : {path}")

    # ------------------------------------------------------------------
    def _build_hex_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        goto_row = QHBoxLayout()
        goto_row.addWidget(QLabel("Aller a l'offset :"))
        self.offset_spin = QSpinBox()
        self.offset_spin.setMaximum(0x7FFFFFFF)
        self.offset_spin.setDisplayIntegerBase(16)
        self.offset_spin.setPrefix("0x")
        goto_row.addWidget(self.offset_spin)
        self.offset_decimal_label = QLabel("(decimal : 0)")
        self.offset_spin.valueChanged.connect(
            lambda v: self.offset_decimal_label.setText(f"(decimal : {v})")
        )
        goto_row.addWidget(self.offset_decimal_label)
        goto_btn = QPushButton("Aller")
        goto_btn.clicked.connect(self._refresh_hex)
        goto_row.addWidget(goto_btn)
        goto_row.addStretch(1)
        layout.addLayout(goto_row)

        self.hex_view = QPlainTextEdit()
        self.hex_view.setReadOnly(True)
        self.hex_view.setFont(QFont("Consolas", 10))
        layout.addWidget(self.hex_view, 1)

        self.tabs.addTab(tab, "Vue hexadecimale")

    def _refresh_hex(self) -> None:
        if not self.bin_file:
            return
        offset = self.offset_spin.value()
        self.hex_view.setPlainText(self.bin_file.hex_dump(offset=offset, length=4096))

    # ------------------------------------------------------------------
    def _build_search_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        options_box = QGroupBox("Recherche")
        grid = QGridLayout(options_box)

        grid.addWidget(QLabel("Mode :"), 0, 0)
        self.search_mode = QComboBox()
        self.search_mode.addItems(["Sequence d'octets (hex)", "Valeur 8-bit", "Valeur 16-bit", "Valeur 32-bit"])
        grid.addWidget(self.search_mode, 0, 1)

        grid.addWidget(QLabel("Valeur :"), 1, 0)
        self.search_value_edit = QLineEdit()
        self.search_value_edit.setPlaceholderText("ex: DEADBEEF ou 4660")
        grid.addWidget(self.search_value_edit, 1, 1)

        self.search_signed = QComboBox()
        self.search_signed.addItems(["Non signe", "Signe"])
        grid.addWidget(self.search_signed, 1, 2)

        search_btn = QPushButton("Rechercher")
        search_btn.clicked.connect(self._run_search)
        grid.addWidget(search_btn, 1, 3)

        layout.addWidget(options_box)

        self.results_table = QTableWidget(0, 2)
        self.results_table.setHorizontalHeaderLabels(["Offset (hex)", "Offset (decimal)"])
        self.results_table.cellDoubleClicked.connect(self._jump_to_result)
        layout.addWidget(self.results_table, 1)

        export_btn = QPushButton("Exporter les resultats (CSV)")
        export_btn.clicked.connect(self._export_search_results)
        layout.addWidget(export_btn)

        self.tabs.addTab(tab, "Recherche")

    def _run_search(self) -> None:
        if not self.bin_file:
            show_error(self, "Aucun fichier", "Ouvrez d'abord un fichier BIN.")
            return
        mode = self.search_mode.currentText()
        text = self.search_value_edit.text().strip()
        signed = self.search_signed.currentText() == "Signe"
        try:
            if mode.startswith("Sequence"):
                needle = bytes.fromhex(text.replace(" ", ""))
                matches = self.bin_file.search_bytes(needle)
            else:
                width = {"Valeur 8-bit": 1, "Valeur 16-bit": 2, "Valeur 32-bit": 4}[mode]
                value = int(text, 0)
                matches = self.bin_file.search_value(value, width=width, signed=signed)
        except ValueError as exc:
            show_error(self, "Entree invalide", str(exc))
            return

        self.results_table.setRowCount(len(matches))
        for row, match in enumerate(matches):
            self.results_table.setItem(row, 0, QTableWidgetItem(match.offset_hex))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(match.offset)))
        self.set_status(f"{len(matches)} resultat(s) trouve(s).")
        log_operation(self.logger, "search", str(self.bin_file.path))

    def _jump_to_result(self, row: int, _column: int) -> None:
        item = self.results_table.item(row, 1)
        if item:
            self.offset_spin.setValue(int(item.text()))
            self._refresh_hex()
            self.tabs.setCurrentIndex(1)

    def _export_search_results(self) -> None:
        if self.results_table.rowCount() == 0:
            show_error(self, "Rien a exporter", "Effectuez une recherche d'abord.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter les resultats", "search_results.csv")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("Offset (hex),Offset (decimal)\n")
            for row in range(self.results_table.rowCount()):
                hex_val = self.results_table.item(row, 0).text()
                dec_val = self.results_table.item(row, 1).text()
                handle.write(f"{hex_val},{dec_val}\n")
        self.set_status(f"Resultats exportes : {path}")


def main() -> int:
    return run_app(BinAnalyzerWindow)


if __name__ == "__main__":
    sys.exit(main())
