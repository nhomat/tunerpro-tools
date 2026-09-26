# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec building every tool as an independent windowed .exe.

Usage (on Windows, from the TunerProToolsSuite/ folder):
    pyinstaller build/tunerpro_tools.spec

This produces one onefile executable per tool directly under dist/, e.g.
dist/BinAnalyzer.exe, dist/BinCompare.exe, ... - matching the names
referenced in TunerPro_CustomTools_Setup.txt and install_tunerpro_tools.bat.

IMPORTANT: PyInstaller does not cross-compile. Running this spec on Linux
produces a Linux ELF binary, not a Windows .exe - see DEVELOPER_GUIDE.md.
Real .exe artifacts must be built by running this spec ON Windows (or in
a Windows CI runner).
"""
import sys
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).resolve().parent
SRC_PATH = str(PROJECT_ROOT / "src")
CONFIG_DATA = [(str(PROJECT_ROOT / "config" / "default_config.json"), "config")]

HIDDEN_IMPORTS = [
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
]

# (display .exe name, tool subfolder under tools/)
TOOLS = [
    ("Dashboard", "dashboard"),
    ("BinAnalyzer", "bin_analyzer"),
    ("BinCompare", "bin_compare"),
    ("MapViewer", "map_viewer"),
    ("LambdaAfrCalculator", "lambda_afr_calculator"),
    ("CalibrationDiff", "calibration_diff"),
    ("ValueConverter", "value_converter"),
    ("ChecksumAnalyzer", "checksum_analyzer"),
    ("BackupManager", "backup_manager"),
    ("MapDatabase", "map_database"),
    ("SessionManager", "session_manager"),
    ("CalibrationWorkbench", "calibration_workbench"),
    ("VehicleSimulator", "vehicle_simulator"),
]

all_binaries = []
all_analyses = []

for exe_name, tool_dir in TOOLS:
    script_path = str(PROJECT_ROOT / "tools" / tool_dir / "main.py")
    analysis = Analysis(
        [script_path],
        pathex=[SRC_PATH],
        binaries=[],
        datas=CONFIG_DATA,
        hiddenimports=HIDDEN_IMPORTS,
        hookspath=[],
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
        cipher=block_cipher,
    )
    pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)
    exe = EXE(
        pyz,
        analysis.scripts,
        analysis.binaries,
        analysis.zipfiles,
        analysis.datas,
        [],
        name=exe_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=None,
    )
    all_analyses.append(analysis)
    all_binaries.append(exe)
