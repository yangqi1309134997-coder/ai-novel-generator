"""
AI小说创作工具 Pro - 打包脚本
用于将应用打包成Windows可执行文件(.exe)

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import os
import sys
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent


def install_dependencies():
    """安装打包所需的依赖"""
    print("=" * 60)
    print("安装打包依赖...")
    print("=" * 60)

    requirements = [
        "pyinstaller>=6.0.0",
    ]

    for req in requirements:
        print(f"安装 {req}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", req])

    print("✅ 依赖安装完成")


def build_exe():
    """使用PyInstaller打包成exe"""
    print("=" * 60)
    print("开始打包成exe（单文件版本）...")
    print("=" * 60)

    # PyInstaller参数
    pyinstaller_args = [
        "pyinstaller",
        "--name=AI小说创作工具Pro",
        "--icon=icon.ico" if (PROJECT_ROOT / "icon.ico").exists() else "--icon=NONE",
        "--onefile",  # 打包成单个exe文件
        "--windowed",  # 不显示控制台窗口
        "--clean",  # 清理缓存
        "--noconfirm",  # 覆盖输出目录而不询问
        "--runtime-hook=hook-safehttpx.py",  # 运行时钩子
        "--add-data=config;config",  # 包含配置目录
        "--add-data=templates;templates",  # 包含模板目录
        # Gradio相关
        "--hidden-import=gradio",
        "--hidden-import=gradio.themes",
        "--hidden-import=gradio.themes.soft",
        "--hidden-import=gradio.themes.base",
        "--hidden-import=gradio.components",
        "--hidden-import=gradio.components.base",
        "--hidden-import=gradio.templates",
        "--hidden-import=gradio_client",
        # httpx相关（解决safehttpx问题）
        "--hidden-import=httpx",
        "--hidden-import=httpx._transports.default",
        "--hidden-import=safehttpx",
        "--hidden-import=aiohttp",
        "--hidden-import=websockets",
        "--hidden-import=websockets.client",
        "--hidden-import=websockets.legacy",
        "--hidden-import=certifi",
        "--hidden-import=charset_normalizer",
        "--hidden-import=idna",
        "--hidden-import=sniffio",
        "--hidden-import=anyio",
        "--hidden-import=anyio.abc",
        "--hidden-import=anyio.streams",
        "--hidden-import=h11",
        "--hidden-import=h2",
        "--hidden-import=hpack",
        "--hidden-import=hyperframe",
        # 其他依赖
        "--hidden-import=openai",
        "--hidden-import=pandas",
        "--hidden-import=docx",
        "--hidden-import=docx.oxml",
        "--hidden-import=docx.oxml.ns",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        "--hidden-import=logging",
        "--hidden-import=pathlib",
        "--hidden-import=yaml",
        "--hidden-import=fitz",
        "--hidden-import=ebooklib",
        "--hidden-import=bs4",
        # numpy相关（gradio必需）
        "--hidden-import=numpy",
        "--hidden-import=numpy.core",
        "--hidden-import=numpy.core._multiarray_umath",
        # 收集所有数据文件
        "--collect-all=gradio",
        "--collect-data=gradio",
        "--collect-all=httpx",
        "--collect-data=httpx",
        # 排除不需要的模块
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=tkinter",
        "--exclude-module=test",
        "--exclude-module=pytest",
        # 注意：不要排除 setuptools，因为 pkg_resources 需要它
        # 注意：不要排除 numpy，因为 gradio 需要它
        "app.py",  # 主程序入口
    ]

    # 执行打包命令
    print(f"执行命令: {' '.join(pyinstaller_args)}")
    subprocess.check_call(pyinstaller_args)

    print("\n" + "=" * 60)
    print("✅ 单文件版打包完成！")
    print(f"可执行文件位置: {PROJECT_ROOT / 'dist' / 'AI小说创作工具Pro.exe'}")
    print("\n注意：首次运行可能较慢（需要解压临时文件）")
    print("=" * 60)


def build_portable_exe():
    """打包成便携版（文件夹形式，启动更快）"""
    print("=" * 60)
    print("开始打包成便携版（文件夹形式）...")
    print("=" * 60)

    # PyInstaller参数（便携版）
    pyinstaller_args = [
        "pyinstaller",
        "--name=AI小说创作工具Pro",
        "--icon=icon.ico" if (PROJECT_ROOT / "icon.ico").exists() else "--icon=NONE",
        "--onedir",  # 打包成文件夹形式（启动更快）
        "--windowed",
        "--clean",
        "--noconfirm",
        "--runtime-hook=hook-safehttpx.py",  # 运行时钩子
        "--add-data=config;config",
        "--add-data=templates;templates",
        # Gradio相关
        "--hidden-import=gradio",
        "--hidden-import=gradio.themes",
        "--hidden-import=gradio.themes.soft",
        "--hidden-import=gradio.themes.base",
        "--hidden-import=gradio.components",
        "--hidden-import=gradio.components.base",
        "--hidden-import=gradio.templates",
        "--hidden-import=gradio_client",
        # httpx相关
        "--hidden-import=httpx",
        "--hidden-import=httpx._transports.default",
        "--hidden-import=safehttpx",
        "--hidden-import=aiohttp",
        "--hidden-import=websockets",
        "--hidden-import=websockets.client",
        "--hidden-import=websockets.legacy",
        "--hidden-import=certifi",
        "--hidden-import=charset_normalizer",
        "--hidden-import=idna",
        "--hidden-import=sniffio",
        "--hidden-import=anyio",
        "--hidden-import=anyio.abc",
        "--hidden-import=anyio.streams",
        "--hidden-import=h11",
        "--hidden-import=h2",
        "--hidden-import=hpack",
        "--hidden-import=hyperframe",
        # 其他依赖
        "--hidden-import=openai",
        "--hidden-import=pandas",
        "--hidden-import=docx",
        "--hidden-import=docx.oxml",
        "--hidden-import=docx.oxml.ns",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        "--hidden-import=logging",
        "--hidden-import=pathlib",
        "--hidden-import=yaml",
        "--hidden-import=fitz",
        "--hidden-import=ebooklib",
        "--hidden-import=bs4",
        # numpy相关（gradio必需）
        "--hidden-import=numpy",
        "--hidden-import=numpy.core",
        "--hidden-import=numpy.core._multiarray_umath",
        # 收集所有数据文件
        "--collect-all=gradio",
        "--collect-data=gradio",
        "--collect-all=httpx",
        "--collect-data=httpx",
        # 排除不需要的模块
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=tkinter",
        "--exclude-module=test",
        "--exclude-module=pytest",
        # 注意：不要排除 setuptools，因为 pkg_resources 需要它
        # 注意：不要排除 numpy，因为 gradio 需要它
        "app.py",
    ]

    print(f"执行命令: {' '.join(pyinstaller_args)}")
    subprocess.check_call(pyinstaller_args)

    print("\n" + "=" * 60)
    print("✅ 便携版打包完成！")
    print(f"可执行文件位置: {PROJECT_ROOT / 'dist' / 'AI小说创作工具Pro' / 'AI小说创作工具Pro.exe'}")
    print("请将整个 dist/AI小说创作工具Pro 文件夹分发给用户")
    print("=" * 60)


def create_build_requirements():
    """创建打包所需的requirements文件"""
    requirements_content = """# AI小说创作工具 Pro - 打包依赖
# 使用方法: pip install -r build_requirements.txt

# 核心依赖
gradio>=4.0.0
pandas>=2.0.0
openai>=1.0.0
python-docx>=1.0.0

# 可选依赖
PyMuPDF>=1.23.0  # PDF支持
ebooklib>=0.18  # EPUB支持
beautifulsoup4>=4.12.0  # EPUB支持
PyYAML>=6.0  # YAML配置支持

# 打包依赖
pyinstaller>=6.0.0
"""

    with open(PROJECT_ROOT / "build_requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements_content)

    print("✅ 已创建 build_requirements.txt")


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "portable":
            install_dependencies()
            build_portable_exe()
        elif mode == "single":
            install_dependencies()
            build_exe()
        else:
            print("用法:")
            print("  python build_exe.py single   - 打包成单个exe文件")
            print("  python build_exe.py portable - 打包成便携版（文件夹）")
    else:
        # 默认打包成便携版（推荐）
        print("AI小说创作工具 Pro - 打包工具")
        print("\n请选择打包模式:")
        print("1. 便携版（文件夹形式，启动更快，推荐）")
        print("2. 单文件版（单个exe文件，体积较大）")

        choice = input("\n请输入选择 (1/2，默认1): ").strip()

        install_dependencies()

        if choice == "2":
            build_exe()
        else:
            build_portable_exe()

    # 创建requirements文件
    create_build_requirements()
