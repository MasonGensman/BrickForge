# -*- mode: python ; coding: utf-8 -*-
#
# StudWorks PyInstaller spec (Package_020.5).
#
# Produces a single-file dist/StudWorks.exe. Bundles only the tier-4
# fallback LDraw library (src/brickforge/ldraw/ldraw, ~18 MB, primitives
# + LDConfig.ldr only -- no real part geometry) -- the full, real
# project-root ldraw/ library (~590 MB) is intentionally NOT bundled;
# see brickforge.services.ldraw_library_locator's four-tier discovery
# order for how a packaged build still finds a real library if one is
# installed on the machine it runs on (LDRAW_LIBRARY_PATH or a standard
# Windows install location).
#
# Set STUDWORKS_DEBUG_CONSOLE=1 before invoking PyInstaller for a debug
# build that keeps the console window open (shows the existing GPU/
# vendor startup banner and any tracebacks) -- see scripts/build.ps1.

import os

console_mode = os.environ.get("STUDWORKS_DEBUG_CONSOLE", "0") == "1"

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/brickforge/render/shaders', 'brickforge/render/shaders'),
        ('src/brickforge/ldraw/ldraw', 'brickforge/ldraw/ldraw'),
        ('src/brickforge/ui/resources/icon.ico', 'brickforge/ui/resources'),
        ('src/brickforge/ui/resources/icon.png', 'brickforge/ui/resources'),
    ],
    hiddenimports=[
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='StudWorks',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console_mode,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/brickforge/ui/resources/icon.ico',
    version='packaging/version_info.txt',
)
