# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = [('config', 'config'), ('templates', 'templates')]
binaries = []
hiddenimports = ['gradio', 'gradio.themes', 'gradio.themes.soft', 'gradio.themes.base', 'gradio.components', 'gradio.components.base', 'gradio.templates', 'gradio_client', 'httpx', 'httpx._transports.default', 'safehttpx', 'aiohttp', 'websockets', 'websockets.client', 'websockets.legacy', 'certifi', 'charset_normalizer', 'idna', 'sniffio', 'anyio', 'anyio.abc', 'anyio.streams', 'h11', 'h2', 'hpack', 'hyperframe', 'openai', 'pandas', 'docx', 'docx.oxml', 'docx.oxml.ns', 'PIL', 'PIL.Image', 'PIL.ImageTk', 'logging', 'pathlib', 'yaml', 'fitz', 'ebooklib', 'bs4', 'numpy', 'numpy.core', 'numpy.core._multiarray_umath']
datas += collect_data_files('gradio')
datas += collect_data_files('httpx')
tmp_ret = collect_all('gradio')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('httpx')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-safehttpx.py'],
    excludes=['matplotlib', 'scipy', 'tkinter', 'test', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI小说创作工具Pro',
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
    icon='NONE',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI小说创作工具Pro',
)
