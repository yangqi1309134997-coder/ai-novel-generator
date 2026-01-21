# -*- mode: python ; coding: utf-8 -*-
"""
AI小说创作工具 Pro - PyInstaller 打包配置
修复了safehttpx、gradio等第三方库的资源文件问题
"""
from PyInstaller.utils.hooks import collect_data_files, collect_all, get_package_paths
import os

block_cipher = None

# =============== 数据文件收集 ===============
datas = []
binaries = []

# 1. 项目配置文件和模板
if os.path.exists('config'):
    datas.append(('config', 'config'))
if os.path.exists('templates'):
    datas.append(('templates', 'templates'))

# 2. safehttpx - 关键修复!
# safehttpx需要version.txt文件,这是错误的根源
try:
    pkg_base, pkg_dir = get_package_paths('safehttpx')
    version_file = os.path.join(pkg_dir, 'version.txt')
    if os.path.exists(version_file):
        datas.append((version_file, 'safehttpx'))
        print(f"[Hook] Found safehttpx version.txt: {version_file}")
    else:
        print(f"[Hook] Warning: safehttpx version.txt not found at {version_file}")
    # 收集所有safehttpx数据文件
    datas += collect_data_files('safehttpx')
except Exception as e:
    print(f"[Hook] safehttpx collection error: {e}")

# 3. gradio - 收集所有组件和模板
try:
    datas += collect_data_files('gradio')
    print("[Hook] Collected gradio data files")
except Exception as e:
    print(f"[Hook] gradio data collection error: {e}")

# 4. httpx 相关
try:
    datas += collect_data_files('httpx')
    print("[Hook] Collected httpx data files")
except Exception as e:
    print(f"[Hook] httpx data collection error: {e}")

# 5. 使用collect_all收集整个包(更全面)
for package in ['gradio', 'httpx']:
    try:
        tmp_ret = collect_all(package)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
        print(f"[Hook] collect_all {package} completed")
    except Exception as e:
        print(f"[Hook] collect_all {package} error: {e}")

# =============== 隐藏导入 ===============
hiddenimports = [
    # Gradio完整导入链
    'gradio',
    'gradio.themes',
    'gradio.themes.soft',
    'gradio.themes.base',
    'gradio.themes.utils',
    'gradio.components',
    'gradio.components.base',
    'gradio.components.form',
    'gradio.templates',
    'gradio._simple_templates',
    'gradio_client',
    'gradio_client.client',

    # safehttpx和httpx - 关键!
    'safehttpx',
    'httpx',
    'httpx._transports.default',
    'httpx._transports.http2',
    'httpx._transports.httpcore',
    'httpx._client',
    'httpx._auth',

    # 网络相关
    'aiohttp',
    'websockets',
    'websockets.client',
    'websockets.legacy',
    'websockets.asyncio',

    # SSL/证书
    'certifi',
    'charset_normalizer',
    'idna',
    'sniffio',
    'anyio',
    'anyio.abc',
    'anyio.streams',
    'anyio._backends',
    'h11',
    'h2',
    'hpack',
    'hyperframe',
    'hstspreload',

    # OpenAI API
    'openai',
    'openai.resources',
    'openai.resources.chat',
    'openai.resources.completions',
    'openai._models',
    'openai._streaming',
    'tiktoken',
    'tiktoken_ext',

    # 数据处理
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs',
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
    'numpy.core._methods',
    'numpy.random',
    'numpy.linalg',

    # 文档处理
    'docx',
    'docx.oxml',
    'docx.oxml.ns',
    'docx.opc',
    'docx.opc.oxml',
    'docx.shared',
    'docx.styles',
    'lxml',
    'lxml._elementpath',

    # 图像处理
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL._imaging',
    'PIL._imagingcms',
    'PIL._imagingmath',

    # 文件解析
    'fitz',  # PyMuPDF
    'ebooklib',
    'ebooklib.plugins',
    'bs4',
    'bs4.builder',

    # 配置和日志
    'yaml',
    'logging',
    'pathlib',
    'json',
    'jsonschema',
    'packaging',
    'packaging.version',
    'pkg_resources',
    'setuptools',

    # 其他
    'typing',
    'typing_extensions',
    'warnings',
    'datetime',
    'threading',
    'queue',
]

# =============== 分析配置 ===============
a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['./'],  # 使用当前目录的hooks
    hooksconfig={},
    runtime_hooks=['rthook-safehttpx.py'],  # 运行时钩子修复safehttpx
    excludes=[
        'matplotlib',
        'scipy',
        'sklearn',
        'tkinter',
        'test',
        'pytest',
        'unittest',
        'pytz',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

# =============== 去重和优化 ===============
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# =============== 可执行文件配置 ===============
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
    icon='NONE',  # 如果有icon.ico文件,改为'icon.ico'
)

# =============== 收集所有文件 ===============
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI小说创作工具Pro',
)
