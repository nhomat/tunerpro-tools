#!/usr/bin/env python3
"""BIN Backup Manager - create timestamped, non-destructive backups.

The original file selected by the user is only ever opened for reading
and copied; it is never overwritten by this tool.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.backup_manager import backup_file, list_backups, restore_original
from tunerpro_tools.config import get_config
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.widgets.common import BinFileDropField, confirm_destructive_action, show_error


class BackupManagerWindow(ToolWindow):
    def __init__(self):
        super().__init__("backup_manager", "BIN Backup Manager", mode="MODIFICATION DE FICHIER")

        create_box = QGroupBox("Creer une sauvegarde")
        create_layout = QVBoxLayout(create_box)
        self.source_field = BinFileDropField("Fichier a sauvegarder...")
        create_layout.addWidget(self.source_field)
        kind_row = QHBoxLayout()
        kind_row.addWidget(QLabel("Type :"))
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["original", "modified"])
        kind_row.addWidget(self.kind_combo)
        backup_btn = QPushButton("Creer la sauvegarde")
        backup_btn.clicked.connect(self._create_backup)
        kind_row.addWidget(backup_btn)
        kind_row.addStretch(1)
        create_layout.addLayout(kind_row)
        self.content_layout.addWidget(create_box)

        list_box = QGroupBox("Sauvegardes existantes")
        list_layout = QVBoxLayout(list_box)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Categorie :"))
        self.list_kind_combo = QComboBox()
        self.list_kind_combo.addItems(["original", "modified"])
        self.list_kind_combo.currentTextChanged.connect(self._refresh_list)
        filter_row.addWidget(self.list_kind_combo)
        refresh_btn = QPushButton("Rafraichir")
        refresh_btn.clicked.connect(self._refresh_list)
        filter_row.addWidget(refresh_btn)
        filter_row.addStretch(1)
        list_layout.addLayout(filter_row)
        self.backup_list = QListWidget()
        list_layout.addWidget(self.backup_list, 1)
        restore_btn = QPushButton("Restore Original...")
        restore_btn.clicked.connect(self._restore_selected)
        list_layout.addWidget(restore_btn)
        self.content_layout.addWidget(list_box, 1)

        self._refresh_list()

    def _create_backup(self) -> None:
        source = self.source_field.path()
        if not source:
            show_error(self, "Aucun fichier", "Selectionnez un fichier a sauvegarder.")
            return
        try:
            record = backup_file(source, kind=self.kind_combo.currentText())
        except (FileNotFoundError, FileExistsError) as exc:
            show_error(self, "Erreur de sauvegarde", str(exc))
            log_operation(self.logger, "backup_file", source, error=str(exc))
            return
        log_operation(self.logger, "backup_file", source)
        self.set_status(f"Sauvegarde creee : {record.backup_path}")
        self._refresh_list()

    def _refresh_list(self) -> None:
        kind = self.list_kind_combo.currentText()
        self.backup_list.clear()
        for path in list_backups(kind=kind):
            self.backup_list.addItem(str(path))

    def _restore_selected(self) -> None:
        item = self.backup_list.currentItem()
        if item is None:
            show_error(self, "Aucune selection", "Selectionnez une sauvegarde dans la liste.")
            return
        backup_path = Path(item.text())
        destination, _ = QFileDialog.getSaveFileName(
            self, "Restaurer vers...", backup_path.name, "Fichiers BIN (*.bin);;Tous (*)"
        )
        if not destination:
            return
        if not confirm_destructive_action(
            self, "Confirmer la restauration",
            f"Copier {backup_path.name} vers :\n{destination} ?",
        ):
            return
        try:
            restore_original(backup_path, destination)
        except (FileNotFoundError, FileExistsError) as exc:
            show_error(self, "Erreur de restauration", str(exc))
            log_operation(self.logger, "restore_original", str(backup_path), error=str(exc))
            return
        log_operation(self.logger, "restore_original", str(backup_path))
        self.set_status(f"Fichier restaure vers : {destination}")


def main() -> int:
    return run_app(BackupManagerWindow)


if __name__ == "__main__":
    sys.exit(main())
