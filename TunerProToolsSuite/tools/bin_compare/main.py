#!/usr/bin/env python3
"""BIN Compare - byte-level diff between two BIN files. Read-only tool."""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtCharts import QChart, QChartView, QScatterSeries
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.bin_file import BinFile
from tunerpro_tools.compare import compare_bytes, differences_to_csv, differences_to_html, filter_differences
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.widgets.common import BinFileDropField, auto_fit_table, read_file_with_progress, show_error


class BinCompareWindow(ToolWindow):
    def __init__(self):
        super().__init__("bin_compare", "BIN Compare", mode="ANALYSE")
        self.original: BinFile | None = None
        self.modified: BinFile | None = None
        self.summary = None
        self.current_differences: list = []

        files_box = QGroupBox("Fichiers")
        files_layout = QVBoxLayout(files_box)
        files_layout.addWidget(QLabel("Original BIN :"))
        self.original_field = BinFileDropField()
        self.original_field.fileSelected.connect(lambda p: self._load(p, is_original=True))
        files_layout.addWidget(self.original_field)
        files_layout.addWidget(QLabel("Modified BIN :"))
        self.modified_field = BinFileDropField()
        self.modified_field.fileSelected.connect(lambda p: self._load(p, is_original=False))
        files_layout.addWidget(self.modified_field)

        compare_row = QHBoxLayout()
        compare_btn = QPushButton("Comparer")
        compare_btn.clicked.connect(self.run_comparison)
        compare_row.addWidget(compare_btn)
        self.summary_label = QLabel("Aucune comparaison effectuee.")
        compare_row.addWidget(self.summary_label, 1)
        files_layout.addLayout(compare_row)
        self.content_layout.addWidget(files_box)

        self.tabs = QTabWidget()
        self.content_layout.addWidget(self.tabs, 1)
        self._build_table_tab()
        self._build_hex_tab()
        self._build_graph_tab()

    # ------------------------------------------------------------------
    def _load(self, path: str, *, is_original: bool) -> None:
        try:
            data = read_file_with_progress(self, path, "Lecture du fichier...")
            bin_file = BinFile(path, data)
        except OSError as exc:
            show_error(self, "Erreur", f"Impossible d'ouvrir le fichier :\n{exc}")
            return
        if is_original:
            self.original = bin_file
        else:
            self.modified = bin_file
        log_operation(self.logger, "open_file", path)
        self.set_status(f"{path} charge.")

    def run_comparison(self) -> None:
        if not self.original or not self.modified:
            show_error(self, "Fichiers manquants", "Selectionnez un Original BIN et un Modified BIN.")
            return
        self.summary = compare_bytes(self.original.data, self.modified.data)
        self.current_differences = list(self.summary.differences)
        size_note = "" if self.summary.size_matches else " (tailles differentes)"
        self.summary_label.setText(
            f"Taille : {self.summary.original_size} -> {self.summary.modified_size} octets{size_note} | "
            f"{self.summary.difference_count} difference(s)"
        )
        self._refresh_table()
        self._refresh_hex()
        self._refresh_graph()
        log_operation(self.logger, "compare", f"{self.original.path} vs {self.modified.path}")

    # ------------------------------------------------------------------
    def _build_table_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Delta minimum (valeur absolue) :"))
        self.min_delta_spin = QSpinBox()
        self.min_delta_spin.setMaximum(255)
        filter_row.addWidget(self.min_delta_spin)
        apply_filter_btn = QPushButton("Appliquer le filtre")
        apply_filter_btn.clicked.connect(self._refresh_table)
        filter_row.addWidget(apply_filter_btn)
        filter_row.addStretch(1)

        prev_btn = QPushButton("<< Precedent")
        prev_btn.clicked.connect(lambda: self._navigate(-1))
        next_btn = QPushButton("Suivant >>")
        next_btn.clicked.connect(lambda: self._navigate(1))
        filter_row.addWidget(prev_btn)
        filter_row.addWidget(next_btn)
        layout.addLayout(filter_row)

        self.diff_table = QTableWidget(0, 4)
        self.diff_table.setHorizontalHeaderLabels(["Offset", "Original", "Modified", "Difference"])
        self.diff_table.cellClicked.connect(self._on_row_selected)
        layout.addWidget(self.diff_table, 1)

        export_row = QHBoxLayout()
        export_csv_btn = QPushButton("Exporter CSV")
        export_csv_btn.clicked.connect(self._export_csv)
        export_html_btn = QPushButton("Exporter HTML")
        export_html_btn.clicked.connect(self._export_html)
        export_row.addWidget(export_csv_btn)
        export_row.addWidget(export_html_btn)
        export_row.addStretch(1)
        layout.addLayout(export_row)

        self.tabs.addTab(tab, "Differences")

    def _refresh_table(self) -> None:
        if not self.summary:
            return
        min_delta = self.min_delta_spin.value()
        self.current_differences = filter_differences(
            self.summary.differences, min_abs_delta=min_delta if min_delta > 0 else None
        )
        self.diff_table.setRowCount(len(self.current_differences))
        for row, diff in enumerate(self.current_differences):
            self.diff_table.setItem(row, 0, QTableWidgetItem(diff.offset_hex))
            self.diff_table.setItem(row, 1, QTableWidgetItem(str(diff.original)))
            self.diff_table.setItem(row, 2, QTableWidgetItem(str(diff.modified)))
            sign = "+" if diff.delta >= 0 else ""
            self.diff_table.setItem(row, 3, QTableWidgetItem(f"{sign}{diff.delta}"))
        auto_fit_table(self.diff_table)
        self._selected_index = -1

    def _navigate(self, direction: int) -> None:
        if not self.current_differences:
            return
        self._selected_index = getattr(self, "_selected_index", -1) + direction
        self._selected_index = max(0, min(self._selected_index, len(self.current_differences) - 1))
        self.diff_table.selectRow(self._selected_index)
        self._on_row_selected(self._selected_index, 0)

    def _on_row_selected(self, row: int, _column: int) -> None:
        self._selected_index = row
        if 0 <= row < len(self.current_differences):
            offset = self.current_differences[row].offset
            self.hex_offset_spin.setValue(offset)
            self._refresh_hex()
            self.tabs.setCurrentIndex(1)

    def _export_csv(self) -> None:
        if not self.current_differences:
            show_error(self, "Rien a exporter", "Effectuez une comparaison d'abord.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter en CSV", "bin_compare.csv")
        if not path:
            return
        Path(path).write_text(differences_to_csv(tuple(self.current_differences)), encoding="utf-8")
        self.set_status(f"CSV exporte : {path}")
        log_operation(self.logger, "export_csv", path)

    def _export_html(self) -> None:
        if not self.current_differences:
            show_error(self, "Rien a exporter", "Effectuez une comparaison d'abord.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter en HTML", "bin_compare.html")
        if not path:
            return
        Path(path).write_text(differences_to_html(tuple(self.current_differences)), encoding="utf-8")
        self.set_status(f"HTML exporte : {path}")
        log_operation(self.logger, "export_html", path)

    # ------------------------------------------------------------------
    def _build_hex_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        row = QHBoxLayout()
        row.addWidget(QLabel("Offset :"))
        self.hex_offset_spin = QSpinBox()
        self.hex_offset_spin.setMaximum(0x7FFFFFFF)
        self.hex_offset_spin.setDisplayIntegerBase(16)
        self.hex_offset_spin.setPrefix("0x")
        self.hex_offset_spin.valueChanged.connect(self._refresh_hex)
        row.addWidget(self.hex_offset_spin)
        row.addStretch(1)
        layout.addLayout(row)

        # A QSplitter (rather than a plain side-by-side layout) lets the
        # user drag the divider when one side needs more room - fixes the
        # cramped/truncated hex columns reported on smaller windows.
        splitter = QSplitter(Qt.Horizontal)

        original_pane = QWidget()
        original_layout = QVBoxLayout(original_pane)
        original_layout.setContentsMargins(0, 0, 0, 0)
        original_layout.addWidget(QLabel("Original"))
        self.original_hex_view = QPlainTextEdit()
        self.original_hex_view.setReadOnly(True)
        self.original_hex_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.original_hex_view.setFont(QFont("Consolas", 10))
        original_layout.addWidget(self.original_hex_view)
        splitter.addWidget(original_pane)

        modified_pane = QWidget()
        modified_layout = QVBoxLayout(modified_pane)
        modified_layout.setContentsMargins(0, 0, 0, 0)
        modified_layout.addWidget(QLabel("Modified"))
        self.modified_hex_view = QPlainTextEdit()
        self.modified_hex_view.setReadOnly(True)
        self.modified_hex_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.modified_hex_view.setFont(QFont("Consolas", 10))
        modified_layout.addWidget(self.modified_hex_view)
        splitter.addWidget(modified_pane)

        splitter.setSizes([1, 1])
        layout.addWidget(splitter, 1)

        self.tabs.addTab(tab, "Vue hexadecimale")

    def _refresh_hex(self) -> None:
        offset = self.hex_offset_spin.value()
        if self.original:
            self.original_hex_view.setPlainText(self.original.hex_dump(offset=offset, length=512))
        if self.modified:
            self.modified_hex_view.setPlainText(self.modified.hex_dump(offset=offset, length=512))

    # ------------------------------------------------------------------
    def _build_graph_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.graph_view = QChartView()
        self.graph_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self.graph_view)
        self.tabs.addTab(tab, "Vue graphique")

    def _refresh_graph(self) -> None:
        if not self.summary:
            return
        chart = QChart()
        chart.setTitle("Zones modifiees (offset vs delta)")
        chart.legend().hide()
        series = QScatterSeries()
        series.setMarkerSize(6)
        for diff in self.summary.differences:
            series.append(diff.offset, diff.delta)
        chart.addSeries(series)
        chart.createDefaultAxes()
        self.graph_view.setChart(chart)


def main() -> int:
    return run_app(BinCompareWindow)


if __name__ == "__main__":
    sys.exit(main())
