# -*- mode: python ; coding: utf-8 -*-
"""
AI小说创作工具 Pro - PyInstaller配置文件

使用方法:
    pyinstaller build_exe.spec

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""

import os
import sys

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('templates', 'templates'),
    ],
    hiddenimports=[
        'gradio',
        'gradio.themes',
        'gradio.themes.soft',
        'gradio.themes.base',
        'gradio.components',
        'gradio.components.base',
        'gradio.templates',
        'gradio_client',
        'openai',
        'pandas',
        'docx',
        'docx.oxml',
        'docx.oxml.ns',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'logging',
        'pathlib',
        'yaml',
        'fitz',  # PyMuPDF
        'ebooklib',
        'bs4',
        'httpx',
        'httpx._transports.default',
        'safehttpx',
        'aiohttp',
        'websockets',
        'websockets.client',
        'websockets.legacy',
        'certifi',
        'charset_normalizer',
        'idna',
        'sniffio',
        'anyio',
        'anyio.abc',
        'anyio.streams',
        'h11',
        'h2',
        'hpack',
        'hyperframe',
        'zstandard',
        'numpy',  # gradio需要
        'numpy.core',
        'numpy.core._multiarray_umath',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-safehttpx.py'],  # 运行时钩子
    excludes=[
        'matplotlib',
        'scipy',
        'tkinter',
        'test',
        'pytest',
        # 注意：不要排除 setuptools，因为 pkg_resources 需要它
        # 注意：不要排除 distutils，因为 setuptools 依赖它
        # 注意：不要排除 numpy，因为 gradio 需要它
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI小说创作工具Pro',
)
