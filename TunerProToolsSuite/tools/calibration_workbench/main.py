#!/usr/bin/env python3
"""Calibration Workbench - import, scan, edit, undo/redo, export a BIN.

Ties together the suite's core library into one professional-style
workflow: automatic structure scan (honest confidence, generic labels
only), checksum detection/recompute, manual grid editing with full
undo/redo history, an exact before/after diff, and a GENERATE MODIFIED
BIN export that never touches the source file.

MODE: MODIFICATION DE FICHIER (the Edition tab writes to an in-memory
working copy; nothing reaches disk until GENERATE MODIFIED BIN is used,
and that always asks for a new destination file).
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
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.checksum import ALGORITHMS, detect_checksum
from tunerpro_tools.compare import classify_variation
from tunerpro_tools.config import EXPERIMENTAL_WARNING
from tunerpro_tools.edit_history import EditHistory, UnsafeDestinationError
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.map_model import MapDefinition, extract_map
from tunerpro_tools.map_scan import find_axis_candidates, scan_table_candidates
from tunerpro_tools.widgets.common import (
    BinFileDropField,
    auto_fit_table,
    confirm_destructive_action,
    read_file_with_progress,
    show_error,
)

_LEVEL_COLORS = {
    "faible variation": QColor(40, 70, 40),
    "variation moderee": QColor(90, 80, 30),
    "variation importante": QColor(100, 40, 40),
}


class MapDefinitionPanel(QGroupBox):
    """Offset/rows/columns/etc, reused by the Edition and Comparaison tabs."""

    def __init__(self):
        super().__init__("Definition de la zone")
        form = QFormLayout(self)

        self.name_edit_value = "Zone"
        self.offset_spin = QSpinBox()
        self.offset_spin.setMaximum(0x7FFFFFFF)
        self.offset_spin.setDisplayIntegerBase(16)
        self.offset_spin.setPrefix("0x")
        form.addRow("Offset :", self.offset_spin)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 512)
        self.rows_spin.setValue(8)
        form.addRow("Lignes :", self.rows_spin)

        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(1, 512)
        self.columns_spin.setValue(8)
        form.addRow("Colonnes :", self.columns_spin)

        self.cell_size_combo = QComboBox()
        self.cell_size_combo.addItems(["1", "2", "4"])
        form.addRow("Taille cellule :", self.cell_size_combo)

        self.endianness_combo = QComboBox()
        self.endianness_combo.addItems(["little", "big"])
        form.addRow("Endianess :", self.endianness_combo)

        self.signed_check = QCheckBox("Signe")
        form.addRow(self.signed_check)

        from PySide6.QtWidgets import QDoubleSpinBox

        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(-1e9, 1e9)
        self.factor_spin.setDecimals(6)
        self.factor_spin.setValue(1.0)
        form.addRow("Facteur :", self.factor_spin)

        self.math_offset_spin = QDoubleSpinBox()
        self.math_offset_spin.setRange(-1e9, 1e9)
        self.math_offset_spin.setDecimals(6)
        form.addRow("Offset mathematique :", self.math_offset_spin)

    def definition(self) -> MapDefinition:
        return MapDefinition(
            name=self.name_edit_value,
            offset=self.offset_spin.value(),
            rows=self.rows_spin.value(),
            columns=self.columns_spin.value(),
            cell_size=int(self.cell_size_combo.currentText()),
            endianness=self.endianness_combo.currentText(),
            signed=self.signed_check.isChecked(),
            factor=self.factor_spin.value(),
            math_offset=self.math_offset_spin.value(),
        )

    def apply_offset_dims(self, offset: int, rows: int, columns: int, cell_size: int, endianness: str) -> None:
        self.offset_spin.setValue(offset)
        self.rows_spin.setValue(rows)
        self.columns_spin.setValue(columns)
        self.cell_size_combo.setCurrentText(str(cell_size))
        self.endianness_combo.setCurrentText(endianness)


class CalibrationWorkbenchWindow(ToolWindow):
    def __init__(self):
        super().__init__("calibration_workbench", "Calibration Workbench", mode="MODIFICATION DE FICHIER")
        self.history: EditHistory | None = None
        self.source_path: str | None = None

        warning = QLabel(EXPERIMENTAL_WARNING)
        warning.setObjectName("WarningBanner")
        warning.setWordWrap(True)
        self.content_layout.addWidget(warning)

        self.path_field = BinFileDropField()
        self.path_field.fileSelected.connect(self._load_file)
        self.content_layout.addWidget(self.path_field)

        top_row = QHBoxLayout()
        self.status_label = QLabel("Aucun fichier charge.")
        top_row.addWidget(self.status_label, 1)
        undo_btn = QPushButton("Annuler (Undo)")
        undo_btn.clicked.connect(self._undo)
        top_row.addWidget(undo_btn)
        redo_btn = QPushButton("Retablir (Redo)")
        redo_btn.clicked.connect(self._redo)
        top_row.addWidget(redo_btn)
        generate_btn = QPushButton("GENERATE MODIFIED BIN")
        generate_btn.clicked.connect(self._generate_modified_bin)
        top_row.addWidget(generate_btn)
        self.content_layout.addLayout(top_row)

        self.tabs = QTabWidget()
        self.content_layout.addWidget(self.tabs, 1)
        self._build_analysis_tab()
        self._build_checksum_tab()
        self._build_edition_tab()
        self._build_comparison_tab()
        self._build_history_tab()

    # ------------------------------------------------------------------
    def _load_file(self, path: str) -> None:
        try:
            data = read_file_with_progress(self, path, "Lecture du fichier...")
        except OSError as exc:
            show_error(self, "Erreur", f"Impossible d'ouvrir le fichier :\n{exc}")
            return
        self.history = EditHistory(data)
        self.source_path = path
        log_operation(self.logger, "open_file", path)
        self._refresh_status()

    def _refresh_status(self) -> None:
        if not self.history:
            self.status_label.setText("Aucun fichier charge.")
            return
        diff = self.history.diff_from_original()
        self.status_label.setText(
            f"{self.source_path} - {len(self.history.original_bytes)} octets - "
            f"{diff.difference_count} octet(s) modifie(s) par rapport a l'original - "
            f"{len(self.history.history)} action(s) dans l'historique."
        )
        self._refresh_history_list()

    def _require_history(self) -> EditHistory | None:
        if self.history is None:
            show_error(self, "Aucun fichier", "Ouvrez d'abord un fichier BIN.")
            return None
        return self.history

    def _undo(self) -> None:
        history = self._require_history()
        if not history:
            return
        edit = history.undo()
        if edit is None:
            self.set_status("Rien a annuler.")
        else:
            log_operation(self.logger, "undo", edit.label)
        self._refresh_status()

    def _redo(self) -> None:
        history = self._require_history()
        if not history:
            return
        edit = history.redo()
        if edit is None:
            self.set_status("Rien a retablir.")
        else:
            log_operation(self.logger, "redo", edit.label)
        self._refresh_status()

    def _generate_modified_bin(self) -> None:
        history = self._require_history()
        if not history:
            return
        default_name = str(Path(self.source_path).with_name(Path(self.source_path).stem + "_modified.bin"))
        destination, _ = QFileDialog.getSaveFileName(
            self, "Generer le BIN modifie", default_name, "Fichiers BIN (*.bin);;Tous (*)"
        )
        if not destination:
            return
        if not confirm_destructive_action(
            self, "Confirmer la generation",
            f"{EXPERIMENTAL_WARNING}\n\nDestination : {destination}\n\nContinuer ?",
        ):
            return
        try:
            history.export(destination, source_path=self.source_path)
        except UnsafeDestinationError as exc:
            show_error(self, "Destination refusee", str(exc))
            return
        except OSError as exc:
            show_error(self, "Erreur d'ecriture", str(exc))
            return
        log_operation(self.logger, "generate_modified_bin", destination)
        self.set_status(f"BIN modifie genere : {destination}")

    # ------------------------------------------------------------------
    def _build_analysis_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("Pas d'analyse (octets) :"))
        self.scan_stride_spin = QSpinBox()
        self.scan_stride_spin.setRange(1, 4096)
        self.scan_stride_spin.setValue(16)
        options_row.addWidget(self.scan_stride_spin)
        options_row.addWidget(QLabel("Confiance minimale (table 2D) :"))
        from PySide6.QtWidgets import QDoubleSpinBox

        self.scan_confidence_spin = QDoubleSpinBox()
        self.scan_confidence_spin.setRange(0.0, 1.0)
        self.scan_confidence_spin.setSingleStep(0.05)
        self.scan_confidence_spin.setValue(0.7)
        options_row.addWidget(self.scan_confidence_spin)
        scan_btn = QPushButton("Analyser automatiquement")
        scan_btn.clicked.connect(self._run_scan)
        options_row.addWidget(scan_btn)
        options_row.addStretch(1)
        layout.addLayout(options_row)

        note = QLabel(
            "Chaque resultat est une hypothese geometrique (axe monotone / surface lisse), "
            "jamais un role automobile identifie automatiquement (ignition, injection, etc.) : "
            "cela necessite toujours une validation manuelle (XDF ou expertise)."
        )
        note.setWordWrap(True)
        note.setObjectName("SafeInfoBanner")
        layout.addWidget(note)

        self.scan_table = QTableWidget(0, 7)
        self.scan_table.setHorizontalHeaderLabels(
            ["Type", "Offset", "Taille", "Dimensions", "Cellule", "Endianess", "Confiance"]
        )
        self.scan_table.cellDoubleClicked.connect(self._apply_scan_selection)
        layout.addWidget(self.scan_table, 1)
        layout.addWidget(QLabel("Double-cliquez un resultat pour le charger dans l'onglet Edition."))

        self.tabs.addTab(tab, "Analyse")

    def _run_scan(self) -> None:
        history = self._require_history()
        if not history:
            return
        data = history.current_bytes
        stride = self.scan_stride_spin.value()
        min_confidence = self.scan_confidence_spin.value()

        axes = find_axis_candidates(data)
        tables = scan_table_candidates(data, stride=stride, min_confidence=min_confidence)

        self._scan_results = [("axe", a) for a in axes] + [("table", t) for t in tables]
        self.scan_table.setRowCount(len(self._scan_results))
        for row, (kind, candidate) in enumerate(self._scan_results):
            if kind == "axe":
                dims = f"{candidate.length}"
                size = candidate.byte_length
                probable = candidate.probable_type.value
            else:
                dims = f"{candidate.rows} x {candidate.columns}"
                size = candidate.byte_length
                probable = candidate.probable_type.value
            self.scan_table.setItem(row, 0, QTableWidgetItem(probable))
            self.scan_table.setItem(row, 1, QTableWidgetItem(f"0x{candidate.offset:X}"))
            self.scan_table.setItem(row, 2, QTableWidgetItem(str(size)))
            self.scan_table.setItem(row, 3, QTableWidgetItem(dims))
            self.scan_table.setItem(row, 4, QTableWidgetItem(str(candidate.cell_size)))
            self.scan_table.setItem(row, 5, QTableWidgetItem(candidate.endianness))
            self.scan_table.setItem(row, 6, QTableWidgetItem(f"{candidate.confidence:.2f}"))
        auto_fit_table(self.scan_table)
        log_operation(self.logger, "scan", f"{len(axes)} axes, {len(tables)} tables")
        self.set_status(f"Analyse terminee : {len(axes)} axe(s), {len(tables)} table(s) 2D probable(s).")

    def _apply_scan_selection(self, row: int, _column: int) -> None:
        kind, candidate = self._scan_results[row]
        if kind == "table":
            self.edit_config.apply_offset_dims(
                candidate.offset, candidate.rows, candidate.columns, candidate.cell_size, candidate.endianness
            )
        else:
            self.edit_config.apply_offset_dims(
                candidate.offset, 1, candidate.length, candidate.cell_size, candidate.endianness
            )
        self.tabs.setCurrentIndex(2)
        self._load_edit_grid()

    # ------------------------------------------------------------------
    def _build_checksum_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        detect_row = QHBoxLayout()
        detect_btn = QPushButton("Detecter automatiquement")
        detect_btn.clicked.connect(self._detect_checksum)
        detect_row.addWidget(detect_btn)
        detect_row.addStretch(1)
        layout.addLayout(detect_row)

        self.checksum_detect_table = QTableWidget(0, 5)
        self.checksum_detect_table.setHorizontalHeaderLabels(
            ["Algorithme", "Zone", "Offset stocke", "Ordre octets", "Valeur"]
        )
        layout.addWidget(self.checksum_detect_table)

        form_box = QGroupBox("Verifier / recalculer un checksum")
        form = QFormLayout(form_box)
        self.checksum_algo_combo = QComboBox()
        for algo in ALGORITHMS.values():
            self.checksum_algo_combo.addItem(algo.label, algo.key)
        form.addRow("Algorithme :", self.checksum_algo_combo)
        self.checksum_zone_start_spin = QSpinBox()
        self.checksum_zone_start_spin.setMaximum(0x7FFFFFFF)
        form.addRow("Debut de zone :", self.checksum_zone_start_spin)
        self.checksum_zone_end_spin = QSpinBox()
        self.checksum_zone_end_spin.setMaximum(0x7FFFFFFF)
        form.addRow("Fin de zone :", self.checksum_zone_end_spin)
        self.checksum_offset_spin = QSpinBox()
        self.checksum_offset_spin.setMaximum(0x7FFFFFFF)
        form.addRow("Offset du checksum :", self.checksum_offset_spin)
        self.checksum_byte_order_combo = QComboBox()
        self.checksum_byte_order_combo.addItems(["big", "little"])
        form.addRow("Ordre des octets :", self.checksum_byte_order_combo)

        buttons_row = QHBoxLayout()
        compare_btn = QPushButton("Comparer avant / apres")
        compare_btn.clicked.connect(self._compare_checksum)
        buttons_row.addWidget(compare_btn)
        recompute_btn = QPushButton("Recalculer et ecrire (action explicite)")
        recompute_btn.clicked.connect(self._recompute_checksum)
        buttons_row.addWidget(recompute_btn)
        form.addRow(buttons_row)
        layout.addWidget(form_box)

        self.checksum_result_label = QLabel("Ancien checksum : - | Nouveau checksum : -")
        layout.addWidget(self.checksum_result_label)
        layout.addStretch(1)

        self.tabs.addTab(tab, "Checksum")

    def _detect_checksum(self) -> None:
        history = self._require_history()
        if not history:
            return
        detections = detect_checksum(history.current_bytes)
        self.checksum_detect_table.setRowCount(len(detections))
        for row, detection in enumerate(detections):
            self.checksum_detect_table.setItem(row, 0, QTableWidgetItem(detection.algorithm))
            self.checksum_detect_table.setItem(
                row, 1, QTableWidgetItem(f"0x{detection.zone_start:X}-0x{detection.zone_end:X}")
            )
            self.checksum_detect_table.setItem(row, 2, QTableWidgetItem(f"0x{detection.checksum_offset:X}"))
            self.checksum_detect_table.setItem(row, 3, QTableWidgetItem(detection.byte_order))
            self.checksum_detect_table.setItem(row, 4, QTableWidgetItem(f"0x{detection.value:X}"))
        auto_fit_table(self.checksum_detect_table)
        if detections:
            best = detections[0]
            self.checksum_algo_combo.setCurrentText(ALGORITHMS[best.algorithm].label)
            self.checksum_zone_start_spin.setValue(best.zone_start)
            self.checksum_zone_end_spin.setValue(best.zone_end)
            self.checksum_offset_spin.setValue(best.checksum_offset)
            self.checksum_byte_order_combo.setCurrentText(best.byte_order)
            self.set_status(f"{len(detections)} algorithme(s) identifie(s).")
        else:
            self.set_status("Aucun algorithme de checksum identifie automatiquement.")
        log_operation(self.logger, "detect_checksum", str(len(detections)))

    def _compare_checksum(self) -> None:
        history = self._require_history()
        if not history:
            return
        try:
            before, after = history.checksum_before_after(
                self.checksum_algo_combo.currentData(),
                self.checksum_zone_start_spin.value(),
                self.checksum_zone_end_spin.value(),
                self.checksum_offset_spin.value(),
                byte_order=self.checksum_byte_order_combo.currentText(),
            )
        except ValueError as exc:
            show_error(self, "Parametres invalides", str(exc))
            return
        match_text = "correspond" if after.matches else "NE correspond PAS"
        self.checksum_result_label.setText(
            f"Ancien checksum : {before.stored_hex} (calcule original : {before.computed_hex}) | "
            f"Nouveau checksum stocke : {after.stored_hex} - le checksum stocke {match_text} "
            f"aux donnees actuelles (calcule : {after.computed_hex})"
        )

    def _recompute_checksum(self) -> None:
        history = self._require_history()
        if not history:
            return
        if not confirm_destructive_action(
            self, "Confirmer l'ecriture du checksum",
            "Ceci va ecrire le checksum recalcule dans la copie de travail (pas le fichier original). Continuer ?",
        ):
            return
        try:
            result, edit = history.apply_recomputed_checksum(
                self.checksum_algo_combo.currentData(),
                self.checksum_zone_start_spin.value(),
                self.checksum_zone_end_spin.value(),
                self.checksum_offset_spin.value(),
                byte_order=self.checksum_byte_order_combo.currentText(),
            )
        except ValueError as exc:
            show_error(self, "Parametres invalides", str(exc))
            return
        self.checksum_result_label.setText(f"Nouveau checksum ecrit : {result.computed_hex}")
        log_operation(self.logger, "recompute_checksum", edit.label)
        self._refresh_status()

    # ------------------------------------------------------------------
    def _build_edition_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.edit_config = MapDefinitionPanel()
        layout.addWidget(self.edit_config)

        buttons_row = QHBoxLayout()
        load_btn = QPushButton("Charger la zone")
        load_btn.clicked.connect(self._load_edit_grid)
        buttons_row.addWidget(load_btn)
        apply_btn = QPushButton("Appliquer les modifications")
        apply_btn.clicked.connect(self._apply_edit_grid)
        buttons_row.addWidget(apply_btn)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        layout.addWidget(QLabel("Valeurs converties (double-cliquez une cellule pour la modifier) :"))
        self.edit_table = QTableWidget()
        layout.addWidget(self.edit_table, 1)

        self.tabs.addTab(tab, "Edition manuelle")

    def _load_edit_grid(self) -> None:
        history = self._require_history()
        if not history:
            return
        try:
            definition = self.edit_config.definition()
            map_data = extract_map(history.current_bytes, definition)
        except ValueError as exc:
            show_error(self, "Configuration invalide", str(exc))
            return
        self._edit_definition = definition
        self.edit_table.setRowCount(definition.rows)
        self.edit_table.setColumnCount(definition.columns)
        for r, row in enumerate(map_data.scaled):
            for c, scaled in enumerate(row):
                item = QTableWidgetItem(f"{scaled:.4f}")
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.edit_table.setItem(r, c, item)
        auto_fit_table(self.edit_table, stretch_last=False)

    def _apply_edit_grid(self) -> None:
        history = self._require_history()
        if not history or not hasattr(self, "_edit_definition"):
            show_error(self, "Aucune zone chargee", "Chargez d'abord une zone.")
            return
        definition = self._edit_definition
        try:
            new_grid = []
            for r in range(definition.rows):
                row = []
                for c in range(definition.columns):
                    item = self.edit_table.item(r, c)
                    row.append(float(item.text()))
                new_grid.append(row)
        except (AttributeError, ValueError) as exc:
            show_error(self, "Valeur invalide", f"Cellule invalide : {exc}")
            return

        edit = history.apply_grid(definition, new_grid, label=f"edition:{definition.offset:#x}")
        log_operation(self.logger, "apply_grid_edit", edit.label)
        self._refresh_status()
        self.set_status(f"Modification appliquee ({definition.rows * definition.columns} cellule(s)).")

    # ------------------------------------------------------------------
    def _build_comparison_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        compare_btn = QPushButton("Comparer la zone (original vs actuel)")
        compare_btn.clicked.connect(self._run_comparison)
        layout.addWidget(compare_btn)

        self.comparison_summary_label = QLabel("Aucune comparaison effectuee.")
        layout.addWidget(self.comparison_summary_label)

        self.comparison_table = QTableWidget()
        layout.addWidget(self.comparison_table, 1)

        legend_row = QHBoxLayout()
        for label, color in _LEVEL_COLORS.items():
            swatch = QLabel(f"  {label}  ")
            swatch.setStyleSheet(f"background-color: {color.name()}; color: white;")
            legend_row.addWidget(swatch)
        legend_row.addStretch(1)
        layout.addLayout(legend_row)

        self.tabs.addTab(tab, "Comparaison avant/apres")

    def _run_comparison(self) -> None:
        history = self._require_history()
        if not history or not hasattr(self, "_edit_definition"):
            show_error(self, "Aucune zone", "Chargez d'abord une zone dans l'onglet Edition.")
            return
        definition = self._edit_definition
        try:
            original_map = extract_map(history.original_bytes, definition)
            current_map = extract_map(history.current_bytes, definition)
        except ValueError as exc:
            show_error(self, "Erreur", str(exc))
            return

        self.comparison_table.setRowCount(definition.rows)
        self.comparison_table.setColumnCount(definition.columns)
        deltas = []
        for r in range(definition.rows):
            for c in range(definition.columns):
                original_value, current_value = original_map.raw[r][c], current_map.raw[r][c]
                delta = current_value - original_value
                item = QTableWidgetItem(str(delta) if delta else "")
                item.setTextAlignment(Qt.AlignCenter)
                if delta != 0:
                    deltas.append(delta)
                    percent = None if original_value == 0 else (delta / original_value) * 100
                    level = classify_variation(percent, absolute_delta=delta)
                    item.setBackground(QBrush(_LEVEL_COLORS[level.value]))
                self.comparison_table.setItem(r, c, item)
        self.comparison_table.horizontalHeader().setDefaultSectionSize(56)
        self.comparison_table.verticalHeader().setDefaultSectionSize(28)

        if deltas:
            self.comparison_summary_label.setText(
                f"{len(deltas)} cellule(s) modifiee(s) - variation moyenne : {sum(deltas)/len(deltas):.2f} - "
                f"max : {max(deltas)} - min : {min(deltas)}"
            )
        else:
            self.comparison_summary_label.setText("Aucune difference sur cette zone.")

    # ------------------------------------------------------------------
    def _build_history_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Actions appliquees (dans l'ordre) :"))
        self.history_list = QListWidget()
        layout.addWidget(self.history_list, 1)
        self.tabs.addTab(tab, "Historique")

    def _refresh_history_list(self) -> None:
        self.history_list.clear()
        if not self.history:
            return
        for index, edit in enumerate(self.history.history, start=1):
            self.history_list.addItem(f"{index}. {edit.label} - offset 0x{edit.offset:X} ({edit.length} octet(s))")


def main() -> int:
    return run_app(CalibrationWorkbenchWindow)


if __name__ == "__main__":
    sys.exit(main())
