"""Drag & drop BIN file field, shared with the rest of the tool."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QWidget


class BinFileDropField(QWidget):
    fileSelected = Signal(str)

    def __init__(self, placeholder: str = "Glissez un fichier .bin ici ou cliquez Parcourir...", parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.editingFinished.connect(self._on_edit_finished)
        browse_button = QPushButton("Parcourir...")
        browse_button.clicked.connect(self._on_browse)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._edit, 1)
        layout.addWidget(browse_button)

    def path(self) -> str:
        return self._edit.text().strip()

    def set_path(self, path: str) -> None:
        self._edit.setText(path)
        self.fileSelected.emit(path)

    def _on_edit_finished(self) -> None:
        if self._edit.text().strip():
            self.fileSelected.emit(self._edit.text().strip())

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Selectionner un fichier BIN", "", "Fichiers BIN (*.bin);;Tous les fichiers (*)")
        if path:
            self.set_path(path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls:
            local_path = urls[0].toLocalFile()
            if local_path:
                self.set_path(local_path)


def show_error(parent, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)
