# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — dracula-gui (windowed / tkinter build) → dracula-gui[.exe].

Onefile windowed app from run_gui.py (no console window). Bundles the same
self-contained game data + icons as the CLI build. tkinter (stdlib) is collected
automatically. On macOS a windowed build produces a .app bundle.

Build:  pyinstaller packaging/dracula-gui.spec
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.abspath(SPECPATH))  # repo root (SPECPATH = packaging/)

datas = (
    [(f, "engine/data") for f in glob.glob(os.path.join(ROOT, "engine", "data", "*.json"))]
    + [(f, "engine/data/i18n") for f in glob.glob(os.path.join(ROOT, "engine", "data", "i18n", "*.csv"))]
    + [(os.path.join(ROOT, "icon", "vampire.ico"), "icon"),
       (os.path.join(ROOT, "icon", "vampire.png"), "icon")]
)

a = Analysis(
    [os.path.join(ROOT, "run_gui.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dracula-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "icon", "vampire.ico"),
)

# macOS only: wrap the windowed exe in a .app bundle (ignored elsewhere). The icon
# (.icns) is injected post-build by installer/macos/build-dmg.sh, generated from the PNG.
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Dracula Adventure.app",
        bundle_identifier="com.gerwout.dracula-adventure",
    )

