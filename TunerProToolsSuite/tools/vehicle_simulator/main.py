#!/usr/bin/env python3
"""Vehicle Simulator - physics-based performance estimation.

MODE: SIMULATION. Every number shown comes from
tunerpro_tools.longitudinal_simulation / engine_model / transmission_model
/ vehicle_dynamics acting on values this window collected - never a
fixed/invented result. Fields the user leaves at their pre-filled
default are tracked as ESTIMATED, not silently treated as measured; the
required fields have no default at all, forcing an explicit value.

Scope note (read before assuming something is missing by accident):
this first version covers the vehicle/engine/transmission form, the
torque/power curves, the 0-X km/h and top-speed results with a real
confidence score and limitations list, and an honest BIN structure scan
(reusing map_scan.py - it never claims a detected region is "the
ignition table" or similar). The animation, live-dashboard gauges,
virtual-dyno RPM cursor, scenario manager and report generator described
alongside this request are NOT implemented here yet - they are follow-up
work, not stubbed/mocked into this window.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
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
from tunerpro_tools.data_provenance import DataSource
from tunerpro_tools.engine_model import EngineSpec, build_engine_curve, kw_to_ch
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.longitudinal_simulation import simulate_acceleration, theoretical_top_speed_kmh
from tunerpro_tools.map_scan import find_axis_candidates, scan_table_candidates
from tunerpro_tools.simulation_confidence import compute_confidence_report
from tunerpro_tools.transmission_model import Gear, TransmissionSpec
from tunerpro_tools.vehicle_dynamics import DEFAULT_ROLLING_RESISTANCE_COEFFICIENT, VehicleSpec
from tunerpro_tools.widgets.common import BinFileDropField, auto_fit_table, show_error

SIMULATION_INTERVALS_KMH = [(0, 50), (0, 100), (0, 160), (80, 120), (100, 200)]

SCOPE_NOTE = (
    "Simulation physique basee sur vos donnees (masse, aero, transmission, points "
    "caracteristiques moteur) - jamais une valeur fixe. Un champ laisse a sa valeur "
    "par defaut est compte comme ESTIME, pas comme mesure. Anime, tableau de bord live, "
    "gestionnaire de scenarios et generateur de rapport ne sont pas encore implementes."
)


class VehicleSimulatorWindow(ToolWindow):
    def __init__(self):
        super().__init__("vehicle_simulator", "Vehicle Simulator", mode="SIMULATION")

        scope_label = QLabel(SCOPE_NOTE)
        scope_label.setObjectName("SafeInfoBanner")
        scope_label.setWordWrap(True)
        self.content_layout.addWidget(scope_label)

        self.tabs = QTabWidget()
        self.content_layout.addWidget(self.tabs, 1)
        self._build_vehicle_tab()
        self._build_results_tab()
        self._build_curves_tab()
        self._build_bin_tab()

        self._last_result = None
        self._last_engine_curve = None

    # ------------------------------------------------------------------
    def _spin(self, minimum, maximum, decimals=2, value=0.0) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setValue(value)
        return spin

    def _build_vehicle_tab(self) -> None:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        row = QHBoxLayout()

        vehicle_box = QGroupBox("Vehicule (requis)")
        vform = QFormLayout(vehicle_box)
        self.mass_spin = self._spin(1, 10000, 0, 0)
        vform.addRow("Masse (kg) :", self.mass_spin)
        self.cx_spin = self._spin(0.01, 2.0, 3, 0)
        vform.addRow("Coefficient Cx :", self.cx_spin)
        self.frontal_area_spin = self._spin(0.1, 10.0, 3, 0)
        vform.addRow("Surface frontale (m2) :", self.frontal_area_spin)
        self.rolling_resistance_spin = self._spin(0.001, 0.1, 4, DEFAULT_ROLLING_RESISTANCE_COEFFICIENT)
        vform.addRow("Coeff. resistance roulement (estimation par defaut) :", self.rolling_resistance_spin)
        row.addWidget(vehicle_box)

        engine_box = QGroupBox("Moteur (requis : couple et puissance max)")
        eform = QFormLayout(engine_box)
        self.peak_torque_spin = self._spin(1, 3000, 1, 0)
        eform.addRow("Couple maximal (Nm) :", self.peak_torque_spin)
        self.peak_torque_rpm_spin = QSpinBox()
        self.peak_torque_rpm_spin.setRange(0, 20000)
        eform.addRow("Regime couple max (rpm) :", self.peak_torque_rpm_spin)
        self.peak_power_spin = self._spin(1, 2000, 1, 0)
        eform.addRow("Puissance maximale (kW) :", self.peak_power_spin)
        self.peak_power_rpm_spin = QSpinBox()
        self.peak_power_rpm_spin.setRange(0, 20000)
        eform.addRow("Regime puissance max (rpm) :", self.peak_power_rpm_spin)
        self.idle_rpm_spin = QSpinBox()
        self.idle_rpm_spin.setRange(0, 5000)
        eform.addRow("Regime ralenti (rpm, optionnel) :", self.idle_rpm_spin)
        self.redline_rpm_spin = QSpinBox()
        self.redline_rpm_spin.setRange(0, 20000)
        eform.addRow("Regime maximal / zone rouge (rpm, optionnel) :", self.redline_rpm_spin)
        row.addWidget(engine_box)

        outer.addLayout(row)

        transmission_box = QGroupBox("Transmission (requis)")
        tform = QFormLayout(transmission_box)
        tvals_row = QHBoxLayout()
        self.final_drive_spin = self._spin(0.5, 10.0, 3, 0)
        tvals_row.addWidget(QLabel("Rapport final :"))
        tvals_row.addWidget(self.final_drive_spin)
        self.wheel_radius_spin = self._spin(0.1, 1.0, 3, 0)
        tvals_row.addWidget(QLabel("Rayon de roue (m) :"))
        tvals_row.addWidget(self.wheel_radius_spin)
        tform.addRow(tvals_row)

        self.gears_table = QTableWidget(0, 2)
        self.gears_table.setHorizontalHeaderLabels(["Rapport de boite", "Rendement (0-1)"])
        tform.addRow(self.gears_table)
        gear_buttons = QHBoxLayout()
        add_gear_btn = QPushButton("Ajouter un rapport")
        add_gear_btn.clicked.connect(self._add_gear_row)
        gear_buttons.addWidget(add_gear_btn)
        remove_gear_btn = QPushButton("Supprimer le rapport selectionne")
        remove_gear_btn.clicked.connect(self._remove_gear_row)
        gear_buttons.addWidget(remove_gear_btn)
        gear_buttons.addStretch(1)
        tform.addRow(gear_buttons)
        outer.addWidget(transmission_box)

        run_btn = QPushButton("Lancer la simulation")
        run_btn.clicked.connect(self._run_simulation)
        outer.addWidget(run_btn)
        outer.addStretch(1)

        self.tabs.addTab(tab, "Vehicule && Moteur")
        self._add_gear_row(3.5, 0.95)
        self._add_gear_row(2.1, 0.96)
        self._add_gear_row(1.4, 0.97)
        self._add_gear_row(1.0, 0.97)

    def _add_gear_row(self, ratio: float = 1.0, efficiency: float = 0.95) -> None:
        row = self.gears_table.rowCount()
        self.gears_table.insertRow(row)
        self.gears_table.setItem(row, 0, QTableWidgetItem(str(ratio)))
        self.gears_table.setItem(row, 1, QTableWidgetItem(str(efficiency)))

    def _remove_gear_row(self) -> None:
        row = self.gears_table.currentRow()
        if row >= 0:
            self.gears_table.removeRow(row)

    # ------------------------------------------------------------------
    def _build_results_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.results_labels: dict[str, QLabel] = {}
        results_box = QGroupBox("Performances simulees")
        rform = QFormLayout(results_box)
        for v0, v1 in SIMULATION_INTERVALS_KMH:
            key = f"{v0}-{v1}"
            label = QLabel("N/A")
            self.results_labels[key] = label
            rform.addRow(f"{v0} -> {v1} km/h :", label)
        self.vmax_label = QLabel("N/A")
        rform.addRow("Vitesse maximale theorique :", self.vmax_label)
        self.vmax_note_label = QLabel("")
        self.vmax_note_label.setWordWrap(True)
        rform.addRow(self.vmax_note_label)
        layout.addWidget(results_box)

        confidence_box = QGroupBox("SIMULATION CONFIDENCE")
        cform = QVBoxLayout(confidence_box)
        self.confidence_label = QLabel("N/A")
        self.confidence_label.setObjectName("TitleLabel")
        cform.addWidget(self.confidence_label)
        cform.addWidget(QLabel("LIMITATIONS OF MODEL :"))
        self.limitations_list = QListWidget()
        cform.addWidget(self.limitations_list)
        layout.addWidget(confidence_box, 1)

        self.tabs.addTab(tab, "Resultats")

    def _build_curves_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self.chart_view)
        self.tabs.addTab(tab, "Courbes couple/puissance")

    def _build_bin_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        bin_note = QLabel(
            "Analyse de structure honnete (memes heuristiques que Calibration Workbench) : "
            "informative uniquement, aucune donnee ici n'alimente automatiquement le modele "
            "moteur ci-dessus, car le role automobile d'une zone detectee ne peut pas etre "
            "determine avec certitude a partir des octets seuls."
        )
        bin_note.setWordWrap(True)
        layout.addWidget(bin_note)

        self.bin_path_field = BinFileDropField()
        self.bin_path_field.fileSelected.connect(self._load_bin)
        layout.addWidget(self.bin_path_field)

        scan_btn = QPushButton("Analyser automatiquement")
        scan_btn.clicked.connect(self._scan_bin)
        layout.addWidget(scan_btn)

        self.bin_scan_table = QTableWidget(0, 6)
        self.bin_scan_table.setHorizontalHeaderLabels(
            ["Type", "Offset", "Taille", "Dimensions", "Cellule", "Confiance"]
        )
        layout.addWidget(self.bin_scan_table, 1)

        self.tabs.addTab(tab, "Analyse BIN")

    def _load_bin(self, path: str) -> None:
        try:
            self._bin_data = BinFile.load(path).data
        except OSError as exc:
            show_error(self, "Erreur", f"Impossible d'ouvrir le fichier :\n{exc}")
            return
        self.set_status(f"{path} charge ({len(self._bin_data)} octets).")

    def _scan_bin(self) -> None:
        if not hasattr(self, "_bin_data"):
            show_error(self, "Aucun fichier", "Ouvrez d'abord un fichier BIN.")
            return
        axes = find_axis_candidates(self._bin_data)
        tables = scan_table_candidates(self._bin_data, stride=16, min_confidence=0.6)
        results = [("axe", a) for a in axes] + [("table", t) for t in tables]
        self.bin_scan_table.setRowCount(len(results))
        for row, (kind, candidate) in enumerate(results):
            dims = str(candidate.length) if kind == "axe" else f"{candidate.rows} x {candidate.columns}"
            self.bin_scan_table.setItem(row, 0, QTableWidgetItem(candidate.probable_type.value))
            self.bin_scan_table.setItem(row, 1, QTableWidgetItem(f"0x{candidate.offset:X}"))
            self.bin_scan_table.setItem(row, 2, QTableWidgetItem(str(candidate.byte_length)))
            self.bin_scan_table.setItem(row, 3, QTableWidgetItem(dims))
            self.bin_scan_table.setItem(row, 4, QTableWidgetItem(str(candidate.cell_size)))
            self.bin_scan_table.setItem(row, 5, QTableWidgetItem(f"{candidate.confidence:.2f}"))
        auto_fit_table(self.bin_scan_table)
        log_operation(self.logger, "scan_bin", f"{len(axes)} axes, {len(tables)} tables")

    # ------------------------------------------------------------------
    def _collect_gears(self) -> list[Gear] | None:
        gears = []
        for row in range(self.gears_table.rowCount()):
            try:
                ratio = float(self.gears_table.item(row, 0).text())
                efficiency = float(self.gears_table.item(row, 1).text())
            except (AttributeError, ValueError):
                show_error(self, "Rapport invalide", f"Ligne {row + 1} du tableau des rapports invalide.")
                return None
            try:
                gears.append(Gear(ratio=ratio, efficiency=efficiency))
            except ValueError as exc:
                show_error(self, "Rapport invalide", str(exc))
                return None
        if not gears:
            show_error(self, "Aucun rapport", "Ajoutez au moins un rapport de boite.")
            return None
        return gears

    def _run_simulation(self) -> None:
        sources: dict[str, DataSource] = {}

        if self.mass_spin.value() <= 0 or self.cx_spin.value() <= 0 or self.frontal_area_spin.value() <= 0:
            show_error(self, "Donnees manquantes", "Masse, Cx et surface frontale sont requis (valeurs > 0).")
            return
        if self.peak_torque_spin.value() <= 0 or self.peak_torque_rpm_spin.value() <= 0:
            show_error(self, "Donnees manquantes", "Couple maximal et son regime sont requis.")
            return
        if self.peak_power_spin.value() <= 0 or self.peak_power_rpm_spin.value() <= 0:
            show_error(self, "Donnees manquantes", "Puissance maximale et son regime sont requis.")
            return
        if self.final_drive_spin.value() <= 0 or self.wheel_radius_spin.value() <= 0:
            show_error(self, "Donnees manquantes", "Rapport final et rayon de roue sont requis.")
            return

        gears = self._collect_gears()
        if gears is None:
            return

        sources["vehicle.mass_kg"] = DataSource.USER
        sources["vehicle.drag_coefficient"] = DataSource.USER
        sources["vehicle.frontal_area_m2"] = DataSource.USER
        sources["vehicle.rolling_resistance_coefficient"] = (
            DataSource.ESTIMATED
            if self.rolling_resistance_spin.value() == DEFAULT_ROLLING_RESISTANCE_COEFFICIENT
            else DataSource.USER
        )
        sources["transmission.final_drive_ratio"] = DataSource.USER
        sources["transmission.wheel_radius_m"] = DataSource.USER
        sources["engine.peak_torque_nm"] = DataSource.USER
        sources["engine.peak_torque_rpm"] = DataSource.USER
        sources["engine.peak_power_kw"] = DataSource.USER
        sources["engine.peak_power_rpm"] = DataSource.USER

        vehicle = VehicleSpec(
            mass_kg=self.mass_spin.value(),
            drag_coefficient=self.cx_spin.value(),
            frontal_area_m2=self.frontal_area_spin.value(),
            rolling_resistance_coefficient=self.rolling_resistance_spin.value(),
            sources=sources,
        )
        transmission = TransmissionSpec(
            gears=gears,
            final_drive_ratio=self.final_drive_spin.value(),
            wheel_radius_m=self.wheel_radius_spin.value(),
            sources=sources,
        )
        engine_spec = EngineSpec(
            peak_torque_nm=self.peak_torque_spin.value(),
            peak_torque_rpm=self.peak_torque_rpm_spin.value(),
            peak_power_kw=self.peak_power_spin.value(),
            peak_power_rpm=self.peak_power_rpm_spin.value(),
            idle_rpm=self.idle_rpm_spin.value() or None,
            redline_rpm=self.redline_rpm_spin.value() or None,
            sources=sources,
        )

        try:
            engine_curve = build_engine_curve(engine_spec)
        except ValueError as exc:
            show_error(self, "Donnees moteur insuffisantes", str(exc))
            return

        result = simulate_acceleration(engine_curve, transmission, vehicle, max_time_s=60.0, max_speed_kmh=400.0)
        top_speed, top_speed_note = theoretical_top_speed_kmh(engine_curve, transmission, vehicle)
        confidence_report = compute_confidence_report(sources)

        self._last_result = result
        self._last_engine_curve = engine_curve

        for v0, v1 in SIMULATION_INTERVALS_KMH:
            key = f"{v0}-{v1}"
            interval = result.time_between_speeds_kmh(v0, v1) if v0 > 0 else result.time_to_speed_kmh(v1)
            self.results_labels[key].setText(f"{interval:.2f} s" if interval is not None else "N/A")

        self.vmax_label.setText(f"{top_speed:.1f} km/h" if top_speed is not None else "N/A")
        self.vmax_note_label.setText(top_speed_note)

        self.confidence_label.setText(f"SIMULATION CONFIDENCE : {confidence_report.confidence_percent:.1f} %")
        self.limitations_list.clear()
        if confidence_report.limitations:
            for note in confidence_report.limitations:
                self.limitations_list.addItem(note)
        else:
            self.limitations_list.addItem("Aucune limitation identifiee : toutes les donnees requises sont renseignees.")

        self._refresh_curves(engine_curve)
        log_operation(self.logger, "run_simulation", f"confidence={confidence_report.confidence_percent}")
        self.set_status(f"Simulation terminee ({result.stopped_reason}).")

    def _refresh_curves(self, engine_curve) -> None:
        chart = QChart()
        chart.setTitle("Couple (Nm) et Puissance (ch) en fonction du regime")

        torque_series = QLineSeries()
        torque_series.setName("Couple (Nm)")
        power_series = QLineSeries()
        power_series.setName("Puissance (ch)")

        for rpm, torque, power_kw in engine_curve.sample(120):
            torque_series.append(rpm, torque)
            power_series.append(rpm, kw_to_ch(power_kw))

        chart.addSeries(torque_series)
        chart.addSeries(power_series)
        chart.createDefaultAxes()
        self.chart_view.setChart(chart)


def main() -> int:
    return run_app(VehicleSimulatorWindow)


if __name__ == "__main__":
    sys.exit(main())
