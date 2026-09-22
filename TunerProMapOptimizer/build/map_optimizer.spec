# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Map Optimizer Assistant.

Usage (on Windows, from the project root):
    pyinstaller build/map_optimizer.spec

Produces dist/MapOptimizer.exe.

IMPORTANT: PyInstaller does not cross-compile. Run this ON Windows to get
a Windows .exe - running it elsewhere produces a native binary for that
platform instead. See docs/DEVELOPER_NOTES.md.
"""
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).resolve().parent
SRC_PATH = str(PROJECT_ROOT / "src")
SCRIPT_PATH = str(PROJECT_ROOT / "tool" / "main.py")

a = Analysis(
    [SCRIPT_PATH],
    pathex=[SRC_PATH],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MapOptimizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)
