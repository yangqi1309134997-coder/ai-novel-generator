"""
AI小说创作工具Pro - 启动脚本
功能：创建虚拟环境、安装依赖、启动应用

使用方法：
    python start_venv.py

项目信息：
- 主启动文件：app.py
- Python要求：3.8+
- 主要依赖：gradio, pandas, openai, python-docx
"""

import sys
import os
import subprocess
import platform
from pathlib import Path
from datetime import datetime

# 项目配置
PROJECT_NAME = "AI小说创作工具Pro"
MAIN_SCRIPT = "app.py"
REQUIREMENTS_FILE = "requirements.txt"
VENV_DIR = "venv"
MIN_PYTHON_VERSION = (3, 8)
LOG_FILE = "logs/startup.log"


def log(message: str) -> None:
    """记录日志到文件和控制台"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    
    # 输出到控制台
    print(log_message)
    
    # 输出到日志文件
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / "startup.log", "a", encoding="utf-8") as f:
        f.write(log_message + "\n")


def check_python_version() -> bool:
    """检查Python版本是否满足要求"""
    log("=" * 60)
    log(f"{PROJECT_NAME} 启动脚本")
    log("=" * 60)
    log(f"检查Python版本...")
    
    version = sys.version_info
    if version < MIN_PYTHON_VERSION:
        error_msg = f"错误：Python版本过低！当前版本：{version.major}.{version.minor}.{version.micro}，要求版本：{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+"
        log(error_msg)
        print(f"\n{error_msg}")
        return False
    
    log(f"✓ Python版本检查通过：{version.major}.{version.minor}.{version.micro}")
    return True


def check_venv_exists() -> bool:
    """检查虚拟环境是否已存在"""
    venv_path = Path(VENV_DIR)
    exists = venv_path.exists() and venv_path.is_dir()
    
    if exists:
        # 检查虚拟环境是否完整
        if platform.system() == "Windows":
            python_exe = venv_path / "Scripts" / "python.exe"
            pip_exe = venv_path / "Scripts" / "pip.exe"
        else:
            python_exe = venv_path / "bin" / "python"
            pip_exe = venv_path / "bin" / "pip"
        
        if python_exe.exists() and pip_exe.exists():
            log(f"✓ 虚拟环境已存在：{VENV_DIR}")
            return True
        else:
            log(f"⚠ 虚拟环境不完整，将重新创建")
            return False
    
    log(f"✗ 虚拟环境不存在：{VENV_DIR}")
    return False


def create_venv() -> bool:
    """创建Python虚拟环境"""
    log(f"\n创建虚拟环境：{VENV_DIR}")
    
    try:
        # 使用内置venv模块创建虚拟环境
        subprocess.run(
            [sys.executable, "-m", "venv", VENV_DIR],
            check=True,
            capture_output=True,
            text=True
        )
        log(f"✓ 虚拟环境创建成功")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"错误：虚拟环境创建失败！\n{e.stderr}"
        log(error_msg)
        print(f"\n{error_msg}")
        return False


def get_venv_python() -> Path:
    """获取虚拟环境中的Python可执行文件路径"""
    if platform.system() == "Windows":
        return Path(VENV_DIR) / "Scripts" / "python.exe"
    else:
        return Path(VENV_DIR) / "bin" / "python"


def get_venv_pip() -> Path:
    """获取虚拟环境中的pip可执行文件路径"""
    if platform.system() == "Windows":
        return Path(VENV_DIR) / "Scripts" / "pip.exe"
    else:
        return Path(VENV_DIR) / "bin" / "pip"


def check_requirements_file() -> bool:
    """检查requirements.txt文件是否存在"""
    requirements_path = Path(REQUIREMENTS_FILE)
    if not requirements_path.exists():
        error_msg = f"错误：未找到依赖文件 {REQUIREMENTS_FILE}"
        log(error_msg)
        print(f"\n{error_msg}")
        return False
    
    log(f"✓ 找到依赖文件：{REQUIREMENTS_FILE}")
    return True


def install_dependencies() -> bool:
    """安装项目依赖"""
    log(f"\n安装项目依赖...")
    
    venv_pip = get_venv_pip()
    
    if not venv_pip.exists():
        error_msg = f"错误：虚拟环境中的pip不存在：{venv_pip}"
        log(error_msg)
        print(f"\n{error_msg}")
        return False
    
    try:
        # 升级pip
        log(f"升级pip...")
        subprocess.run(
            [str(venv_pip), "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
            text=True
        )
        log(f"✓ pip升级成功")
        
        # 安装依赖
        log(f"安装依赖包（这可能需要几分钟）...")
        result = subprocess.run(
            [str(venv_pip), "install", "-r", REQUIREMENTS_FILE],
            check=True,
            capture_output=True,
            text=True
        )
        
        log(f"✓ 依赖安装成功")
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = f"错误：依赖安装失败！\n{e.stderr}"
        log(error_msg)
        print(f"\n{error_msg}")
        print("\n提示：您可以尝试手动安装依赖：")
        print(f"  {venv_pip} install -r {REQUIREMENTS_FILE}")
        return False


def check_main_script() -> bool:
    """检查主启动文件是否存在"""
    main_script_path = Path(MAIN_SCRIPT)
    if not main_script_path.exists():
        error_msg = f"错误：未找到主启动文件 {MAIN_SCRIPT}"
        log(error_msg)
        print(f"\n{error_msg}")
        return False
    
    log(f"✓ 找到主启动文件：{MAIN_SCRIPT}")
    return True


def start_application() -> None:
    """启动应用"""
    log(f"\n启动应用...")
    venv_python = get_venv_python()
    
    if not venv_python.exists():
        error_msg = f"错误：虚拟环境中的Python不存在：{venv_python}"
        log(error_msg)
        print(f"\n{error_msg}")
        sys.exit(1)
    
    log(f"✓ 使用虚拟环境Python：{venv_python}")
    log(f"✓ 启动主程序：{MAIN_SCRIPT}")
    log("=" * 60)
    
    # 启动应用
    try:
        subprocess.run([str(venv_python), MAIN_SCRIPT])
    except KeyboardInterrupt:
        log(f"\n用户中断，程序退出")
    except Exception as e:
        error_msg = f"错误：启动应用失败！\n{str(e)}"
        log(error_msg)
        print(f"\n{error_msg}")
        sys.exit(1)


def main():
    """主函数"""
    # 1. 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 2. 检查虚拟环境
    venv_exists = check_venv_exists()
    
    # 3. 创建虚拟环境（如果不存在）
    if not venv_exists:
        if not create_venv():
            sys.exit(1)
    
    # 4. 检查依赖文件
    if not check_requirements_file():
        sys.exit(1)
    
    # 5. 安装依赖（总是检查并更新）
    if not install_dependencies():
        sys.exit(1)
    
    # 6. 检查主启动文件
    if not check_main_script():
        sys.exit(1)
    
    # 7. 启动应用
    start_application()


if __name__ == "__main__":
    main()
