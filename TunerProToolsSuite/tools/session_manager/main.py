#!/usr/bin/env python3
"""Calibration Session - .tpsuite project manager."""
from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from tunerpro_tools.app_base import ToolWindow, run_app
from tunerpro_tools.logging_utils import log_operation
from tunerpro_tools.session import SESSION_EXTENSION, CalibrationSession
from tunerpro_tools.widgets.common import BinFileDropField, show_error


class SessionManagerWindow(ToolWindow):
    def __init__(self):
        super().__init__("session_manager", "Calibration Session", mode="ANALYSE")
        self.session = CalibrationSession(name="Nouvelle session")
        self.current_path: Path | None = None

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Nom du projet :"))
        self.name_edit = QLineEdit(self.session.name)
        self.name_edit.textChanged.connect(self._on_name_changed)
        name_row.addWidget(self.name_edit, 1)
        self.content_layout.addLayout(name_row)

        files_box = QGroupBox("Fichiers du projet")
        files_layout = QVBoxLayout(files_box)
        files_layout.addWidget(QLabel("BIN original :"))
        self.original_field = BinFileDropField()
        self.original_field.fileSelected.connect(self._on_original_changed)
        files_layout.addWidget(self.original_field)
        files_layout.addWidget(QLabel("BIN modifie :"))
        self.modified_field = BinFileDropField()
        self.modified_field.fileSelected.connect(self._on_modified_changed)
        files_layout.addWidget(self.modified_field)
        self.content_layout.addWidget(files_box)

        notes_box = QGroupBox("Notes")
        notes_layout = QVBoxLayout(notes_box)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.textChanged.connect(self._on_notes_changed)
        notes_layout.addWidget(self.notes_edit)
        self.content_layout.addWidget(notes_box)

        history_box = QGroupBox("Historique")
        history_layout = QVBoxLayout(history_box)
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        self.content_layout.addWidget(history_box, 1)

        button_row = QHBoxLayout()
        new_btn = QPushButton("Nouveau")
        new_btn.clicked.connect(self._new_session)
        open_btn = QPushButton("Ouvrir...")
        open_btn.clicked.connect(self._open_session)
        save_btn = QPushButton("Enregistrer...")
        save_btn.clicked.connect(self._save_session)
        button_row.addWidget(new_btn)
        button_row.addWidget(open_btn)
        button_row.addWidget(save_btn)
        button_row.addStretch(1)
        self.content_layout.addLayout(button_row)

        self.add_shortcut("Ctrl+S", self._save_session, "Enregistrer")
        self.add_shortcut("Ctrl+O", self._open_session, "Ouvrir")

    def _refresh_history(self) -> None:
        self.history_list.clear()
        for entry in self.session.history:
            self.history_list.addItem(f"{entry.timestamp} - {entry.action} - {entry.detail}")

    def _on_name_changed(self, text: str) -> None:
        self.session.name = text

    def _on_original_changed(self, path: str) -> None:
        self.session.original_bin_path = path
        self.session.record("original_bin_set", path)
        self._refresh_history()

    def _on_modified_changed(self, path: str) -> None:
        self.session.modified_bin_path = path
        self.session.record("modified_bin_set", path)
        self._refresh_history()

    def _on_notes_changed(self) -> None:
        self.session.notes = self.notes_edit.toPlainText()

    def _new_session(self) -> None:
        self.session = CalibrationSession(name="Nouvelle session")
        self.current_path = None
        self.name_edit.setText(self.session.name)
        self.original_field.set_path("")
        self.modified_field.set_path("")
        self.notes_edit.setPlainText("")
        self._refresh_history()

    def _open_session(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir une session", "", f"Sessions TunerPro Tools (*{SESSION_EXTENSION})"
        )
        if not path:
            return
        try:
            self.session = CalibrationSession.load(path)
        except (OSError, ValueError) as exc:
            show_error(self, "Erreur", f"Impossible d'ouvrir la session :\n{exc}")
            return
        self.current_path = Path(path)
        self.name_edit.setText(self.session.name)
        self.original_field.set_path(self.session.original_bin_path or "")
        self.modified_field.set_path(self.session.modified_bin_path or "")
        self.notes_edit.setPlainText(self.session.notes)
        self._refresh_history()
        log_operation(self.logger, "open_session", path)
        self.set_status(f"Session chargee : {path}")

    def _save_session(self) -> None:
        path = str(self.current_path) if self.current_path else ""
        selected, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer la session", path or f"{self.session.name}{SESSION_EXTENSION}",
            f"Sessions TunerPro Tools (*{SESSION_EXTENSION})",
        )
        if not selected:
            return
        if not selected.endswith(SESSION_EXTENSION):
            selected += SESSION_EXTENSION
        self.session.record("session_saved", selected)
        self.session.save(selected)
        self.current_path = Path(selected)
        self._refresh_history()
        log_operation(self.logger, "save_session", selected)
        self.set_status(f"Session enregistree : {selected}")


def main() -> int:
    return run_app(SessionManagerWindow)


if __name__ == "__main__":
    sys.exit(main())
