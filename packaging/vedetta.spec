# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: pyinstaller packaging/vedetta.spec   (eseguito dalla radice del progetto)
import os
from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # radice del progetto, qualunque sia la cartella di lancio
datas, binaries, hiddenimports = [], [], []
for pkg in ("ultralytics", "lap", "torchvision"):  # torchvision: servono i binari _C per gli operatori (nms)
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h
hiddenimports += ["mss", "yaml", "cv2", "torchvision.ops", "vedetta", "vedetta.app", "vedetta.tools.zone_editor", "vedetta.tools.region_picker"]

a = Analysis(
    [os.path.join(ROOT, "run.py")], pathex=[ROOT], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
    hookspath=[], runtime_hooks=[], excludes=["matplotlib", "pandas", "scipy", "IPython", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Vedetta", console=True, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Vedetta")
