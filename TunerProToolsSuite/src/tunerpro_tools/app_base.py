"""Common QMainWindow scaffold shared by every tool's main.py.

Keeping this here (rather than duplicating it in each ``tools/*/main.py``)
means every tool gets the same dark theme, title bar, mode banner and
Ctrl+Q/File>Quit shortcut for free, while remaining independently
launchable/compilable - a tool's main.py still only imports this
package plus PySide6, so PyInstaller can freeze each one on its own.
"""
from __future__ import annotations

import sys
from typing import Callable

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from .config import APP_NAME, APP_VERSION
from .logging_utils import get_tool_logger
from .theme import apply_dark_theme
from .widgets.common import mode_banner


class ToolWindow(QMainWindow):
    """Base window: title label, mode banner, content area, File menu, logger."""

    def __init__(self, tool_name: str, title: str, mode: str = "ANALYSE"):
        super().__init__()
        self.tool_name = tool_name
        self.logger = get_tool_logger(tool_name)
        self.setWindowTitle(f"{title} - {APP_NAME}")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 650)

        central = QWidget()
        self.setCentralWidget(central)
        self.root_layout = QVBoxLayout(central)

        title_label = QLabel(title)
        title_label.setObjectName("TitleLabel")
        self.root_layout.addWidget(title_label)
        self.root_layout.addWidget(mode_banner(mode))

        self.content_layout = QVBoxLayout()
        self.root_layout.addLayout(self.content_layout, 1)

        self.statusBar().showMessage("Pret.")

        self._build_menu()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&Fichier")
        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = self.menuBar().addMenu("&Aide")
        about_action = QAction("A propos", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "A propos",
            f"{self.windowTitle()}\n{APP_NAME} v{APP_VERSION}\n\n"
            "Outil hors-ligne destine a l'analyse et la simulation.",
        )

    def add_shortcut(self, sequence: str, callback: Callable[[], None], label: str = "") -> QAction:
        action = QAction(label or sequence, self)
        action.setShortcut(QKeySequence(sequence))
        action.triggered.connect(callback)
        self.addAction(action)
        return action

    def set_status(self, message: str) -> None:
        self.statusBar().showMessage(message)


def run_app(window_factory: Callable[[], QMainWindow]) -> int:
    """Create the QApplication, apply the theme, show the window, run the loop.

    Opens maximized: a fixed default size was too small on some screens
    to show every column/table without manual resizing (the exact
    complaint this addresses). The window remains freely resizable.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    apply_dark_theme(app)
    window = window_factory()
    window.showMaximized()
    return app.exec()
