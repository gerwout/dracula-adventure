# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — dracula (CLI / console build) → dracula[.exe].

Onefile console app from run_cli.py. Bundles the self-contained game data
(engine/data/*.json incl. world.json, engine/data/i18n/*.csv) and the icons at
their source-relative paths, so the engine's Path(__file__).parent lookups resolve
inside the PyInstaller bundle. The original game files are NOT bundled — the runtime
reads only engine/data/world.json.

Build:  pyinstaller packaging/dracula-cli.spec
"""
import glob
import os

ROOT = os.path.dirname(os.path.abspath(SPECPATH))  # repo root (SPECPATH = packaging/)

datas = (
    [(f, "engine/data") for f in glob.glob(os.path.join(ROOT, "engine", "data", "*.json"))]
    + [(f, "engine/data/i18n") for f in glob.glob(os.path.join(ROOT, "engine", "data", "i18n", "*.csv"))]
    + [(os.path.join(ROOT, "icon", "vampire.ico"), "icon"),
       (os.path.join(ROOT, "icon", "vampire.png"), "icon")]
)

a = Analysis(
    [os.path.join(ROOT, "run_cli.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],  # CLI build needs no GUI toolkit
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dracula",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "icon", "vampire.ico"),
)
