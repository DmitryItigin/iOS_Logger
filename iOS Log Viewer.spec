# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files


a = Analysis(
    ['ios_log_viewer.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/icon.ico', 'assets')] + collect_data_files("qa_theme"),
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
    # No spaces -- GitHub sanitizes spaces in uploaded release asset names
    # inconsistently (dashes via manual web upload, dots via the Actions
    # release action observed here), making the resulting filename
    # unpredictable. A space-free name sidesteps that entirely.
    name='iOS-Log-Viewer',
    icon='assets/icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX-compressed exes are a common AV heuristic false-positive trigger
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
