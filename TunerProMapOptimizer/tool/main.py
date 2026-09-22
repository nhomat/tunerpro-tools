#!/usr/bin/env python3
"""Map Optimizer Assistant - Lissage (smoothing/outliers) + Tuning (interpolation).

Lissage tab: MODE SIMULATION. Suggests smoothing and flags isolated
cells; never writes anything.

Tuning tab: fills a table from user-supplied anchor points via
interpolation, then can write the result to a NEW file copy only -
never the source file - after an explicit confirmation showing the
experimental-modification warning. MODE MODIFICATION DE FICHIER applies
only to that one write action.

See src/map_optimizer/optimizer.py and src/map_optimizer/patch.py for
exactly what each function does and does not do - neither this window
nor the modules behind it ever estimate horsepower/torque/AFR/knock
margin, or choose target values on their own.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QBrush, QColor, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from map_optimizer.bin_file import BinFile
from map_optimizer.map_model import MapDefinition, extract_map
from map_optimizer.optimizer import TuningTarget, generate_suggestions, generate_tuning_suggestion
from map_optimizer.patch import UnsafeDestinationError, write_grid_to_copy
from map_optimizer.theme import apply_dark_theme
from map_optimizer.widgets.common import BinFileDropField, show_error

LISSAGE_DISCLAIMER = (
    "Cet onglet suggere un lissage et signale des cellules isolees, sur la base "
    "des donnees du fichier uniquement. Il n'evalue ni la puissance, ni le couple, "
    "ni la richesse, ni le risque de cliquetis. Rien n'est jamais ecrit automatiquement."
)

TUNING_DISCLAIMER = (
    "Cet onglet interpole UNIQUEMENT les valeurs que vous saisissez vous-meme ci-dessous "
    "(vos points de reference) - il n'invente aucune valeur et n'evalue ni la puissance, ni "
    "le couple, ni la richesse, ni le risque de cliquetis. Aucune ecriture n'a lieu sans "
    "confirmation explicite, et toujours dans une COPIE, jamais le fichier source.\n\n"
    "Cette modification est experimentale. Verifiez la compatibilite du fichier, du "
    "calculateur et du materiel avant toute utilisation reelle."
)


class MapConfigPanel(QGroupBox):
    """Shared BIN + map geometry configuration, reused by both tabs."""

    def __init__(self):
        super().__init__("Fichier et configuration de la map")
        layout = QVBoxLayout(self)

        self.path_field = BinFileDropField()
        layout.addWidget(self.path_field)

        form = QFormLayout()
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

        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(-1e9, 1e9)
        self.factor_spin.setDecimals(6)
        self.factor_spin.setValue(1.0)
        form.addRow("Facteur :", self.factor_spin)

        layout.addLayout(form)

    def definition(self) -> MapDefinition:
        return MapDefinition(
            name="Zone",
            offset=self.offset_spin.value(),
            rows=self.rows_spin.value(),
            columns=self.columns_spin.value(),
            cell_size=int(self.cell_size_combo.currentText()),
            endianness=self.endianness_combo.currentText(),
            factor=self.factor_spin.value(),
        )


class LissageTab(QWidget):
    def __init__(self, config: MapConfigPanel):
        super().__init__()
        self.config = config
        self.data: bytes | None = None
        self.suggestion = None

        layout = QVBoxLayout(self)
        disclaimer = QLabel(LISSAGE_DISCLAIMER)
        disclaimer.setObjectName("SafeInfoBanner")
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        form = QFormLayout()
        self.smoothing_spin = QDoubleSpinBox()
        self.smoothing_spin.setRange(0.0, 1.0)
        self.smoothing_spin.setSingleStep(0.05)
        self.smoothing_spin.setValue(0.3)
        form.addRow("Intensite du lissage (0-1) :", self.smoothing_spin)

        self.z_threshold_spin = QDoubleSpinBox()
        self.z_threshold_spin.setRange(0.5, 10.0)
        self.z_threshold_spin.setSingleStep(0.1)
        self.z_threshold_spin.setValue(2.5)
        form.addRow("Seuil de detection (z-score) :", self.z_threshold_spin)

        analyze_btn = QPushButton("Analyser et suggerer")
        analyze_btn.clicked.connect(self._run_analysis)
        form.addRow(analyze_btn)
        layout.addLayout(form)

        summary_row = QHBoxLayout()
        self.summary_label = QLabel("Aucune analyse effectuee.")
        summary_row.addWidget(self.summary_label, 1)
        export_btn = QPushButton("Exporter la suggestion (CSV)")
        export_btn.clicked.connect(self._export_csv)
        summary_row.addWidget(export_btn)
        layout.addLayout(summary_row)

        layout.addWidget(QLabel("Original -> Suggestion (cellules signalees en surbrillance)"))
        self.table = QTableWidget()
        layout.addWidget(self.table, 1)

    def _run_analysis(self) -> None:
        path = self.config.path_field.path()
        if not path:
            show_error(self, "Aucun fichier", "Ouvrez d'abord un fichier BIN.")
            return
        try:
            self.data = BinFile.load(path).data
            definition = self.config.definition()
            raw_grid = extract_map(self.data, definition)
        except (OSError, ValueError) as exc:
            show_error(self, "Erreur", str(exc))
            return

        scaled_grid = [[value * definition.factor for value in row] for row in raw_grid]
        self.suggestion = generate_suggestions(
            scaled_grid,
            smoothing_strength=self.smoothing_spin.value(),
            z_threshold=self.z_threshold_spin.value(),
        )
        self._refresh_table()
        self.summary_label.setText(
            f"{len(self.suggestion.outliers)} cellule(s) signalee(s) comme ecart isole - "
            f"{self.suggestion.changed_cell_count} cellule(s) modifiee(s) par le lissage suggere. "
            "Aucune ecriture effectuee."
        )

    def _refresh_table(self) -> None:
        suggestion = self.suggestion
        rows, columns = len(suggestion.original), len(suggestion.original[0])
        self.table.setRowCount(rows)
        self.table.setColumnCount(columns)
        outlier_positions = {(f.row, f.column) for f in suggestion.outliers}
        for r in range(rows):
            for c in range(columns):
                original, suggested = suggestion.original[r][c], suggestion.smoothed[r][c]
                text = f"{original:.3f} -> {suggested:.3f}" if abs(suggested - original) > 1e-9 else f"{original:.3f}"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if (r, c) in outlier_positions:
                    item.setBackground(QBrush(QColor(100, 60, 30)))
                    item.setToolTip("Ecart isole par rapport aux cellules voisines - verification manuelle recommandee.")
                self.table.setItem(r, c, item)

    def _export_csv(self) -> None:
        if self.suggestion is None:
            show_error(self, "Rien a exporter", "Lancez d'abord une analyse.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter la suggestion", "map_optimizer_suggestion.csv")
        if not path:
            return
        outlier_positions = {(f.row, f.column) for f in self.suggestion.outliers}
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("Ligne,Colonne,Original,Suggestion,Ecart_isole\n")
            for r, (orow, srow) in enumerate(zip(self.suggestion.original, self.suggestion.smoothed)):
                for c, (original, suggested) in enumerate(zip(orow, srow)):
                    flagged = "oui" if (r, c) in outlier_positions else "non"
                    handle.write(f"{r},{c},{original:.6f},{suggested:.6f},{flagged}\n")
        self.summary_label.setText(f"Suggestion exportee : {path}")


class TuningTab(QWidget):
    def __init__(self, config: MapConfigPanel):
        super().__init__()
        self.config = config
        self.data: bytes | None = None
        self.suggestion = None

        layout = QVBoxLayout(self)
        disclaimer = QLabel(TUNING_DISCLAIMER)
        disclaimer.setObjectName("WarningBanner")
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        layout.addWidget(QLabel(
            "Points de reference (vos valeurs, en unites reelles apres application du facteur) :"
        ))
        self.targets_table = QTableWidget(0, 3)
        self.targets_table.setHorizontalHeaderLabels(["Ligne", "Colonne", "Valeur cible"])
        layout.addWidget(self.targets_table)

        target_buttons = QHBoxLayout()
        add_btn = QPushButton("Ajouter un point")
        add_btn.clicked.connect(self._add_target_row)
        remove_btn = QPushButton("Supprimer la ligne selectionnee")
        remove_btn.clicked.connect(self._remove_selected_row)
        target_buttons.addWidget(add_btn)
        target_buttons.addWidget(remove_btn)
        target_buttons.addStretch(1)
        layout.addLayout(target_buttons)

        action_row = QHBoxLayout()
        interpolate_btn = QPushButton("Interpoler")
        interpolate_btn.clicked.connect(self._run_interpolation)
        action_row.addWidget(interpolate_btn)
        write_btn = QPushButton("Ecrire dans une copie...")
        write_btn.clicked.connect(self._write_copy)
        action_row.addWidget(write_btn)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.summary_label = QLabel("Aucune interpolation effectuee.")
        layout.addWidget(self.summary_label)

        layout.addWidget(QLabel("Original -> Suggestion Tuning"))
        self.table = QTableWidget()
        layout.addWidget(self.table, 1)

    def _add_target_row(self) -> None:
        row = self.targets_table.rowCount()
        self.targets_table.insertRow(row)
        for col, default in enumerate(("0", "0", "0")):
            self.targets_table.setItem(row, col, QTableWidgetItem(default))

    def _remove_selected_row(self) -> None:
        row = self.targets_table.currentRow()
        if row >= 0:
            self.targets_table.removeRow(row)

    def _read_targets(self) -> list[TuningTarget]:
        targets = []
        for row in range(self.targets_table.rowCount()):
            try:
                r = int(self.targets_table.item(row, 0).text())
                c = int(self.targets_table.item(row, 1).text())
                value = float(self.targets_table.item(row, 2).text())
            except (AttributeError, ValueError) as exc:
                raise ValueError(f"Ligne {row + 1} du tableau de points invalide : {exc}") from exc
            targets.append(TuningTarget(r, c, value))
        return targets

    def _run_interpolation(self) -> None:
        path = self.config.path_field.path()
        if not path:
            show_error(self, "Aucun fichier", "Ouvrez d'abord un fichier BIN.")
            return
        try:
            targets = self._read_targets()
            if not targets:
                raise ValueError("Ajoutez au moins un point de reference.")
            self.data = BinFile.load(path).data
            definition = self.config.definition()
            raw_grid = extract_map(self.data, definition)
        except (OSError, ValueError) as exc:
            show_error(self, "Erreur", str(exc))
            return

        scaled_grid = [[value * definition.factor for value in row] for row in raw_grid]
        try:
            self.suggestion = generate_tuning_suggestion(scaled_grid, targets)
        except ValueError as exc:
            show_error(self, "Points invalides", str(exc))
            return
        self._refresh_table()
        self.summary_label.setText(
            f"Interpolation calculee a partir de {len(targets)} point(s). Aucune ecriture effectuee."
        )

    def _refresh_table(self) -> None:
        suggestion = self.suggestion
        rows, columns = len(suggestion.original), len(suggestion.original[0])
        self.table.setRowCount(rows)
        self.table.setColumnCount(columns)
        target_positions = {(t.row, t.column) for t in suggestion.targets}
        for r in range(rows):
            for c in range(columns):
                original, tuned = suggestion.original[r][c], suggestion.tuned[r][c]
                text = f"{original:.3f} -> {tuned:.3f}"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if (r, c) in target_positions:
                    item.setBackground(QBrush(QColor(30, 70, 100)))
                    item.setToolTip("Point de reference saisi par l'utilisateur.")
                self.table.setItem(r, c, item)

    def _write_copy(self) -> None:
        source_path = self.config.path_field.path()
        if self.suggestion is None or not source_path:
            show_error(self, "Rien a ecrire", "Chargez un fichier et lancez une interpolation d'abord.")
            return

        default_name = str(Path(source_path).with_name(Path(source_path).stem + "_tuned" + Path(source_path).suffix))
        destination, _ = QFileDialog.getSaveFileName(
            self, "Ecrire la copie modifiee", default_name, "Fichiers BIN (*.bin);;Tous (*)"
        )
        if not destination:
            return

        confirm = QMessageBox.warning(
            self,
            "Confirmer l'ecriture",
            "Vous allez creer une copie modifiee du fichier avec les valeurs interpolees ci-dessus.\n\n"
            "Cette modification est experimentale. Verifiez la compatibilite du fichier, du "
            "calculateur et du materiel avant toute utilisation reelle.\n\n"
            f"Destination : {destination}\n\nContinuer ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            definition = self.config.definition()
            write_grid_to_copy(source_path, destination, definition, self.suggestion.tuned)
        except UnsafeDestinationError as exc:
            show_error(self, "Destination refusee", str(exc))
            return
        except (OSError, ValueError) as exc:
            show_error(self, "Erreur d'ecriture", str(exc))
            return

        self.summary_label.setText(f"Copie modifiee ecrite : {destination}")


class MapOptimizerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Optimizer Assistant - TunerPro Tools")
        self.resize(1150, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("Map Optimizer Assistant")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        self.config = MapConfigPanel()
        layout.addWidget(self.config)

        tabs = QTabWidget()
        tabs.addTab(LissageTab(self.config), "Lissage && detection")
        tabs.addTab(TuningTab(self.config), "Tuning (interpolation)")
        layout.addWidget(tabs, 1)

        quit_action = QAction("Quitter", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_dark_theme(app)
    window = MapOptimizerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
