#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI小说生成工具 Pro v2.0 - 快速开始脚本
自动化初始化、测试和启动
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def print_header(text):
    """打印标题"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_success(text):
    """打印成功信息"""
    print(f"✅ {text}")

def print_error(text):
    """打印错误信息"""
    print(f"❌ {text}")

def print_warning(text):
    """打印警告信息"""
    print(f"⚠️  {text}")

def print_info(text):
    """打印信息"""
    print(f"ℹ️  {text}")

def check_python():
    """检查Python版本"""
    print_header("检查Python环境")
    
    version_info = sys.version_info
    python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    
    print_info(f"Python版本: {python_version}")
    
    if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 8):
        print_error("Python版本过低，需要3.8或更高")
        sys.exit(1)
    
    print_success("Python版本检查通过")

def check_files():
    """检查必要文件"""
    print_header("检查项目文件")
    
    required_files = [
        "app.py",
        "config.py",
        "logger.py",
        "api_client.py",
        "file_parser.py",
        "novel_generator.py",
        "exporter.py",
        "project_manager.py",
        "requirements.txt",
        "README.md"
    ]
    
    missing = []
    for filename in required_files:
        if os.path.exists(filename):
            print_success(f"找到 {filename}")
        else:
            missing.append(filename)
            print_error(f"缺少 {filename}")
    
    if missing:
        print_error(f"缺少 {len(missing)} 个文件: {', '.join(missing)}")
        print_warning("请确保所有文件都在同一目录中")
        sys.exit(1)
    
    print_success("所有必要文件都存在")

def setup_directories():
    """创建必要目录"""
    print_header("初始化项目目录")
    
    directories = [
        "projects",
        "exports",
        "logs",
        "cache",
        "config"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print_success(f"目录就绪: {directory}/")

def create_default_config():
    """创建默认配置文件"""
    print_header("创建配置文件")
    
    config_file = "config/novel_tool_config.json"
    
    if os.path.exists(config_file):
        print_warning("配置文件已存在，跳过创建")
        return
    
    default_config = {
        "version": "2.0.0",
        "backends": [
            {
                "name": "本地Ollama",
                "type": "ollama",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama",
                "model": "llama3.1:latest",
                "enabled": True,
                "timeout": 30,
                "retry_times": 3
            }
        ],
        "generation": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_tokens": 4096,
            "chapter_target_words": 2500,
            "writing_style": "流畅自然，情节紧凑，人物刻画细腻",
            "writing_tone": "中性",
            "character_development": "详细",
            "plot_complexity": "中等"
        }
    }
    
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(default_config, f, ensure_ascii=False, indent=4)
    
    print_success(f"配置文件已创建: {config_file}")
    print_info("请根据需要编辑配置文件或在Web UI中修改")

def install_dependencies():
    """安装依赖"""
    print_header("安装Python依赖")
    
    try:
        import gradio
        print_success("gradio 已安装")
    except ImportError:
        print_warning("gradio 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gradio>=4.0.0"])
    
    try:
        import pandas
        print_success("pandas 已安装")
    except ImportError:
        print_warning("pandas 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas>=2.0.0"])
    
    try:
        import openai
        print_success("openai 已安装")
    except ImportError:
        print_warning("openai 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai>=1.0.0"])
    
    try:
        import docx
        print_success("python-docx 已安装")
    except ImportError:
        print_warning("python-docx 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx>=0.8.10"])
    
    # 可选依赖
    print_info("检查可选依赖...")
    
    optional = [
        ("fitz (PyMuPDF)", "PyMuPDF"),
        ("ebooklib", "ebooklib"),
        ("bs4 (beautifulsoup4)", "beautifulsoup4"),
        ("markdown", "markdown")
    ]
    
    for name, package in optional:
        try:
            __import__(package.replace("-", "_"))
            print_success(f"{name} 已安装")
        except ImportError:
            print_warning(f"{name} 未安装（可选，但建议安装）")
            print_info(f"安装方式: pip install {package}")

def test_import():
    """测试导入"""
    print_header("测试模块导入")
    
    modules = [
        "config",
        "logger",
        "api_client",
        "file_parser",
        "novel_generator",
        "exporter",
        "project_manager"
    ]
    
    for module in modules:
        try:
            __import__(module)
            print_success(f"导入 {module} 成功")
        except ImportError as e:
            print_error(f"导入 {module} 失败: {e}")
            return False
    
    return True

def show_next_steps():
    """显示后续步骤"""
    print_header("🎉 初始化完成！")
    
    print("""
下一步操作：

1. ⚙️  配置API后端
   编辑文件: config/novel_tool_config.json
   或在Web UI的"⚙️ 设置"标签中修改

2. 🚀 启动应用
   运行命令: python app.py
   
   或在Windows中双击: run.bat
   或在Linux/Mac中运行: ./run.sh

3. 🌐 打开浏览器
   访问地址: http://127.0.0.1:7860

4. ✍️  开始创作！
   - 选择功能标签页
   - 填写创意设定
   - 开始生成您的小说

常用帮助：
📖 完整文档: 阅读 README.md
📈 升级说明: 阅读 UPGRADE_GUIDE.md
📋 优化总结: 阅读 COMPLETION_REPORT.md
🐛 问题排除: 查看 logs/ 目录下的日志

配置文件位置：
- 主配置: config/novel_tool_config.json
- 日志: logs/novel_tool_*.log
- 项目: projects/*/
- 导出: exports/*/
- 缓存: cache/

建议：
✓ 保存创意设定
✓ 定期备份项目 (projects/ 目录)
✓ 调整参数找到最适合的设置
✓ 使用不同导出格式分享作品

问题帮助：
如果遇到问题，请查看日志文件：
  logs/novel_tool_*.log      # 通用日志
  logs/errors_*.log          # 错误日志

祝您创作愉快！ 📖✨
""")

def main():
    """主函数"""
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║          AI小说创作工具 Pro v2.0 - 快速开始向导              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    try:
        # 步骤1: 检查Python
        check_python()
        
        # 步骤2: 检查文件
        check_files()
        
        # 步骤3: 创建目录
        setup_directories()
        
        # 步骤4: 创建配置
        create_default_config()
        
        # 步骤5: 安装依赖
        install_dependencies()
        
        # 步骤6: 测试导入
        if not test_import():
            print_error("模块导入失败，请检查安装")
            sys.exit(1)
        
        # 步骤7: 显示后续步骤
        show_next_steps()
        
        print("\n" + "="*60)
        print("✨ 所有初始化步骤都已完成！")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  初始化被中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
