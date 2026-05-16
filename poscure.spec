# -*- mode: python ; coding: utf-8 -*-
# Poscure v1 — PyInstaller build spec
# Run: pyinstaller poscure.spec

import sys
from pathlib import Path

block_cipher = None
SRC = str(Path("src").resolve())

a = Analysis(
    [str(Path("src/main.py").resolve())],
    pathex=[SRC],
    binaries=[],
    datas=[
        # Include any assets if present
        # ("assets/icons", "assets/icons"),
    ],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PIL",
        "PIL.Image",
        "PIL.ImageOps",
        "sqlite3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim Qt modules we don't need
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtMultimedia",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtSensors",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.QtDataVisualization",
        "PySide6.QtCharts",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "tkinter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Poscure",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,             # compress; install UPX for smaller output
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,         # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",   # uncomment and provide icon file
    version_file=None,
)
