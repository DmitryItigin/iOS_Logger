# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from qa_theme import app_icons

# release.yml writes ios_logger/_version.py before pyinstaller: a suffix there means a test build
try:
    from ios_logger._version import VERSION
except ImportError:
    VERSION = "dev"
_ICON = str(app_icons.icon_path("ios-logger", app_icons.is_test_version(VERSION)))

from PyInstaller.utils.hooks import collect_data_files


a = Analysis(
    ['ios_log_viewer.py'],
    pathex=[],
    binaries=[],
    datas=collect_data_files("qa_theme"),
    hiddenimports=[],
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
    name='iOS_Log_Viewer_console',
    icon=_ICON,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX-compressed exes are a common AV heuristic false-positive trigger
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
