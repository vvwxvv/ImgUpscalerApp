# hook-realesrgan.py
# Place this file in your project root (same dir as main.py).

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("realesrgan")