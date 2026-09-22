"""Shared widgets: drag & drop BIN picker, mode banners, progress helper."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QWidget,
)

CHUNK_SIZE = 4 * 1024 * 1024  # 4 MiB - large-file progress granularity


class BinFileDropField(QWidget):
    """A path field that accepts typing, Browse..., and drag & drop of a .bin file."""

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

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 (Qt override)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 (Qt override)
        urls = event.mimeData().urls()
        if urls:
            local_path = urls[0].toLocalFile()
            if local_path:
                self.set_path(local_path)


def mode_banner(mode: str) -> QLabel:
    """A colored banner making the current operating mode unmistakable.

    ``mode`` must be one of ANALYSE / SIMULATION / MODIFICATION DE FICHIER.
    """
    label = QLabel(f"MODE : {mode}")
    label.setAlignment(Qt.AlignCenter)
    if mode == "MODIFICATION DE FICHIER":
        label.setObjectName("WarningBanner")
    else:
        label.setObjectName("SafeInfoBanner")
    return label


def experimental_warning_label() -> QLabel:
    from ..config import EXPERIMENTAL_WARNING

    label = QLabel(EXPERIMENTAL_WARNING)
    label.setObjectName("WarningBanner")
    label.setWordWrap(True)
    return label


def confirm_destructive_action(parent, title: str, question: str) -> bool:
    answer = QMessageBox.question(
        parent, title, question, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    return answer == QMessageBox.Yes


def show_error(parent, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)


def run_chunked_with_progress(
    parent,
    title: str,
    total_size: int,
    reader: Callable[[Callable[[int], None]], object],
) -> object:
    """Run ``reader(report_progress)`` while showing a progress dialog.

    ``reader`` receives a callback it should invoke with bytes processed so
    far; used for potentially slow operations on large BIN files.
    """
    if total_size < CHUNK_SIZE:
        return reader(lambda _processed: None)

    dialog = QProgressDialog(title, None, 0, total_size, parent)
    dialog.setWindowModality(Qt.WindowModal)
    dialog.setMinimumDuration(0)
    dialog.show()

    def report_progress(processed: int) -> None:
        dialog.setValue(min(processed, total_size))
        dialog.repaint()

    try:
        result = reader(report_progress)
    finally:
        dialog.close()
    return result


def read_file_with_progress(parent, path: str, title: str = "Lecture du fichier...") -> bytes:
    size = Path(path).stat().st_size

    def reader(report_progress: Callable[[int], None]) -> bytes:
        chunks = []
        processed = 0
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(CHUNK_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)
                processed += len(chunk)
                report_progress(processed)
        return b"".join(chunks)

    return run_chunked_with_progress(parent, title, size, reader)
