#!/usr/bin/env python3
"""Map Viewer - display a table/grid extracted from a BIN as table, 2D or 3D."""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtDataVisualization import (
    Q3DSurface,
    QSurface3DSeries,
    QSurfaceDataItem,
    QSurfaceDataProxy,
)
from PySide6.QtGui import QPainter, QVector3D
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.map_model import MapDefinition, extract_map
from tunerpro_tools.widgets.common import BinFileDropField, read_file_with_progress, show_error


class MapViewerWindow(ToolWindow):
    def __init__(self):
        super().__init__("map_viewer", "Map Viewer", mode="ANALYSE")
        self.data: bytes | None = None
        self.map_data = None

        self.path_field = BinFileDropField()
        self.path_field.fileSelected.connect(self._load_file)
        self.content_layout.addWidget(self.path_field)

        config_box = QGroupBox("Configuration de la map")
        form = QFormLayout(config_box)

        self.name_edit = QLineEdit("Map 1")
        form.addRow("Nom :", self.name_edit)

        self.offset_spin = QSpinBox()
        self.offset_spin.setMaximum(0x7FFFFFFF)
        self.offset_spin.setDisplayIntegerBase(16)
        self.offset_spin.setPrefix("0x")
        form.addRow("Offset de depart :", self.offset_spin)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 512)
        self.rows_spin.setValue(8)
        form.addRow("Nombre de lignes :", self.rows_spin)

        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(1, 512)
        self.columns_spin.setValue(8)
        form.addRow("Nombre de colonnes :", self.columns_spin)

        self.cell_size_combo = QComboBox()
        self.cell_size_combo.addItems(["1", "2", "4"])
        form.addRow("Taille d'une cellule (octets) :", self.cell_size_combo)

        self.endianness_combo = QComboBox()
        self.endianness_combo.addItems(["little", "big"])
        form.addRow("Endianess :", self.endianness_combo)

        self.signed_check = QCheckBox("Signe")
        form.addRow("", self.signed_check)

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

        button_row = QHBoxLayout()
        read_btn = QPushButton("Lire la map")
        read_btn.clicked.connect(self._read_map)
        button_row.addWidget(read_btn)
        save_config_btn = QPushButton("Sauvegarder la config (JSON)")
        save_config_btn.clicked.connect(self._save_config)
        button_row.addWidget(save_config_btn)
        load_config_btn = QPushButton("Charger une config (JSON)")
        load_config_btn.clicked.connect(self._load_config)
        button_row.addWidget(load_config_btn)
        form.addRow(button_row)

        self.content_layout.addWidget(config_box)

        self.tabs = QTabWidget()
        self.content_layout.addWidget(self.tabs, 1)
        self._build_table_tab()
        self._build_chart_tab()
        self._build_surface_tab()

    # ------------------------------------------------------------------
    def _current_definition(self) -> MapDefinition:
        return MapDefinition(
            name=self.name_edit.text() or "Map",
            offset=self.offset_spin.value(),
            rows=self.rows_spin.value(),
            columns=self.columns_spin.value(),
            cell_size=int(self.cell_size_combo.currentText()),
            endianness=self.endianness_combo.currentText(),
            signed=self.signed_check.isChecked(),
            factor=self.factor_spin.value(),
            math_offset=self.math_offset_spin.value(),
            unit=self.unit_edit.text(),
        )

    def _apply_definition(self, definition: MapDefinition) -> None:
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

    def _load_file(self, path: str) -> None:
        try:
            self.data = read_file_with_progress(self, path, "Lecture du fichier...")
        except OSError as exc:
            show_error(self, "Erreur", f"Impossible d'ouvrir le fichier :\n{exc}")
            return
        log_operation(self.logger, "open_file", path)
        self.set_status(f"{path} charge ({len(self.data)} octets).")

    def _read_map(self) -> None:
        if self.data is None:
            show_error(self, "Aucun fichier", "Ouvrez d'abord un fichier BIN.")
            return
        try:
            definition = self._current_definition()
            self.map_data = extract_map(self.data, definition)
        except ValueError as exc:
            show_error(self, "Configuration invalide", str(exc))
            return
        self._refresh_table()
        self._refresh_chart()
        self._refresh_surface()
        log_operation(self.logger, "read_map", definition.name)

    def _save_config(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder la configuration", "map.json", "JSON (*.json)")
        if not path:
            return
        self._current_definition().save(path)
        self.set_status(f"Configuration enregistree : {path}")

    def _load_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Charger une configuration", "", "JSON (*.json)")
        if not path:
            return
        try:
            definition = MapDefinition.load(path)
        except (ValueError, OSError) as exc:
            show_error(self, "Erreur", str(exc))
            return
        self._apply_definition(definition)
        self.set_status(f"Configuration chargee : {path}")

    # ------------------------------------------------------------------
    def _build_table_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.raw_table = QTableWidget()
        self.scaled_table = QTableWidget()
        layout.addWidget(QLabel("Valeurs brutes"))
        layout.addWidget(self.raw_table, 1)
        layout.addWidget(QLabel("Valeurs converties (brute x facteur + offset)"))
        layout.addWidget(self.scaled_table, 1)
        self.tabs.addTab(tab, "Tableau")

    def _refresh_table(self) -> None:
        if not self.map_data:
            return
        for table, matrix, fmt in (
            (self.raw_table, self.map_data.raw, "{}"),
            (self.scaled_table, self.map_data.scaled, "{:.3f}"),
        ):
            table.setRowCount(len(matrix))
            table.setColumnCount(len(matrix[0]) if matrix else 0)
            for r, row in enumerate(matrix):
                for c, value in enumerate(row):
                    table.setItem(r, c, QTableWidgetItem(fmt.format(value)))

    # ------------------------------------------------------------------
    def _build_chart_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self.chart_view)
        self.tabs.addTab(tab, "Graphique 2D")

    def _refresh_chart(self) -> None:
        if not self.map_data:
            return
        chart = QChart()
        chart.setTitle(f"{self.map_data.definition.name} - vue 2D (par ligne)")
        for r, row in enumerate(self.map_data.scaled):
            series = QLineSeries()
            series.setName(f"Ligne {r}")
            for c, value in enumerate(row):
                series.append(c, value)
            chart.addSeries(series)
        chart.createDefaultAxes()
        if len(self.map_data.scaled) > 8:
            chart.legend().hide()
        self.chart_view.setChart(chart)

    # ------------------------------------------------------------------
    def _build_surface_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.surface = None
        self._surface_series = None

        # Q3DSurface opens a native OpenGL window under the hood. That is
        # unavailable on the "offscreen" Qt platform (used for automated
        # tests and some headless/remote setups) and crashes the process
        # if forced, so it is only created when a real display backend is
        # active. Table and 2D chart views remain fully available either way.
        from PySide6.QtWidgets import QApplication

        platform_name = QApplication.instance().platformName() if QApplication.instance() else ""
        if platform_name == "offscreen":
            layout.addWidget(QLabel(
                "Vue 3D indisponible sur cette plateforme d'affichage (offscreen).\n"
                "Utilisez les onglets Tableau ou Graphique 2D, ou lancez l'outil "
                "avec un affichage graphique standard (Windows/bureau)."
            ))
        else:
            self.surface = Q3DSurface()
            container = QWidget.createWindowContainer(self.surface)
            container.setMinimumSize(400, 300)
            layout.addWidget(container)
            self._surface_series = QSurface3DSeries()
            self.surface.addSeries(self._surface_series)

        self.tabs.addTab(tab, "Surface 3D")

    def _refresh_surface(self) -> None:
        if not self.map_data or self._surface_series is None:
            return
        data_array = []
        for r, row in enumerate(self.map_data.scaled):
            row_items = [QSurfaceDataItem(QVector3D(c, value, r)) for c, value in enumerate(row)]
            data_array.append(row_items)
        proxy = QSurfaceDataProxy()
        proxy.resetArray(data_array)
        self._surface_series.setDataProxy(proxy)


def main() -> int:
    return run_app(MapViewerWindow)


if __name__ == "__main__":
    sys.exit(main())
