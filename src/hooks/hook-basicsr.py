# hook-basicsr.py
# Place this file in your project root (same dir as main.py).
# PyInstaller picks it up via --additional-hooks-dir=.

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Pull in every submodule of basicsr so its arch registry is intact
datas, binaries, hiddenimports = collect_all("basicsr")

# Explicitly name the two archs we use (belt-and-suspenders)
hiddenimports += [
    "basicsr.archs",
    "basicsr.archs.rrdbnet_arch",
    "basicsr.archs.srvgg_arch",
    "basicsr.utils",
    "basicsr.utils.registry",
    "basicsr.data",
    "basicsr.losses",
    "basicsr.models",
    "basicsr.ops",
]