# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('static', 'static'), ('src', 'src'), ('models', 'models')]
binaries = []
hiddenimports = ['torch', 'torch.nn', 'torch.nn.functional', 'torch._C', 'torch.cuda', 'torchvision', 'torchvision.transforms', 'torchvision.transforms.functional', 'basicsr', 'basicsr.archs', 'basicsr.archs.rrdbnet_arch', 'basicsr.archs.srvgg_arch', 'basicsr.utils', 'basicsr.utils.registry', 'realesrgan', 'numpy', 'numpy.core', 'numpy.core._multiarray_umath', 'PIL', 'PIL.Image', 'PIL.ImageFilter', 'PIL.JpegImagePlugin', 'PIL.PngImagePlugin', 'PIL.WebPImagePlugin', 'PIL.BmpImagePlugin', 'PIL.TiffImagePlugin']
tmp_ret = collect_all('torch')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('torchvision')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('basicsr')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('realesrgan')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('timm')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['src/hooks'],
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
    [],
    exclude_binaries=True,
    name='ImgUpscalerApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['static\\favicon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ImgUpscalerApp',
)
