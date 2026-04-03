# -*- mode: python ; coding: utf-8 -*-
"""
AI Novel Generator 4.5 - PyInstaller 打包配置
生成 Windows 可执行文件
"""
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_all, copy_metadata

block_cipher = None

# 项目根目录
ROOT = os.path.abspath('.')

# ===== 收集数据文件 =====

# 项目自身数据
datas = [
    ('config', 'config'),
    ('src', 'src'),
]

# Gradio 及其依赖的数据文件（使用 PyInstaller hook 工具正确收集）
_extra_hidden = []
for pkg in ['gradio', 'gradio_client', 'safehttpx', 'groovy', 'huggingface_hub']:
    try:
        pkg_datas, pkg_bins, pkg_hidden = collect_all(pkg)
        datas.extend(pkg_datas)
        _extra_hidden.extend(pkg_hidden)
    except Exception:
        try:
            datas.extend(collect_data_files(pkg))
        except Exception:
            pass

# ===== 隐式导入 =====
hiddenimports = [
    'gradio',
    'gradio.themes',
    'gradio.components',
    'gradio.layouts',
    'gradio.blocks',
    'gradio.events',
    'gradio.routes',
    'gradio.utils',
    'gradio.cli',
    'gradio.data_classes',
    'gradio.exceptions',
    'gradio.external',
    'gradio.flagging',
    'gradio.helpers',
    'gradio.templating',
    'openai',
    'docx',
    'docx.shared',
    'docx.enum',
    'docx.oxml',
    'huggingface_hub',
    'httpx',
    'httpcore',
    'pydantic',
    'pydantic_core',
    'pydantic.deprecated',
    'pydantic.deprecated.decorator',
    'annotated_types',
    'anyio',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.responses',
    'fastapi',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'multipart',
    'python_multipart',
    'jinja2',
    'markupsafe',
    'websockets',
    'sniffio',
    'idna',
    'h11',
    'click',
    'tqdm',
    'packaging',
    'filelock',
    'typing_extensions',
    'yaml',
    'json5',
    'toml',
    'semantic_version',
    'numpy',
    'pandas',
    'aiofiles',
    'ffmpy',
    'pydub',
    'altair',
    'safehttpx',
]

# 排除不需要的大型模块
excludes = [
    'matplotlib',
    'tkinter',
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'scipy',
    'sklearn',
    'tensorflow',
    'torch',
    'IPython',
    'notebook',
    'sphinx',
    'pytest',
    'playwright',
]

a = Analysis(
    ['run.py'],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports + _extra_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='AI_Novel_Generator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI_Novel_Generator',
)
