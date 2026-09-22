"""Dark stylesheet, matching TunerPro Tools Suite's look."""
from __future__ import annotations

DARK_STYLESHEET = """
QWidget { background-color: #1e1e1e; color: #e0e0e0; font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; }
QLabel#TitleLabel { font-size: 20px; font-weight: 600; color: #ffffff; }
QPushButton { background-color: #2d6cdf; color: white; border: none; border-radius: 4px; padding: 6px 14px; }
QPushButton:hover { background-color: #3a7cf0; }
QPushButton:pressed { background-color: #1f56c0; }
QPushButton:disabled { background-color: #3a3a3a; color: #888888; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #2b2b2b; border: 1px solid #444444; border-radius: 3px; padding: 4px; color: #f0f0f0; }
QTableWidget { background-color: #232323; alternate-background-color: #292929; gridline-color: #3a3a3a; border: 1px solid #3a3a3a; }
QHeaderView::section { background-color: #2d2d2d; color: #dddddd; padding: 4px; border: 1px solid #3a3a3a; }
QLabel#WarningBanner { background-color: #4a3200; color: #ffd479; border: 1px solid #7a5300; border-radius: 4px; padding: 6px 10px; }
QLabel#SafeInfoBanner { background-color: #123a24; color: #7fe0a8; border: 1px solid #1f6b40; border-radius: 4px; padding: 6px 10px; }
QStatusBar { background-color: #171717; }
"""


def apply_dark_theme(app) -> None:
    app.setStyleSheet(DARK_STYLESHEET)
