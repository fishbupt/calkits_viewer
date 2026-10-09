# Run from repo root: uv run --locked --group build pyinstaller packaging/calkits_viewer.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

project_root = Path(SPECPATH).parent
analysis = Analysis(
    [str(project_root / 'xkt_viewer.py')],
    pathex=[str(project_root / 'src')],
    binaries=[], datas=collect_data_files('matplotlib'),
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[], noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True,
          name='CalKitViewer', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=False, console=False)
collection = COLLECT(exe, analysis.binaries, analysis.datas,
                     strip=False, upx=False, name='CalKitViewer')
