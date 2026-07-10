from pathlib import Path


PROJECT_DIR = Path(SPECPATH)

a = Analysis(
    [str(PROJECT_DIR / "mini_notes_summary.py")],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=["executa_manifest", "executa_sdk", "executa_sdk.sampling"],
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
    name="mini-notes-summary",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
