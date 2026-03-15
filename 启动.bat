@echo off
chcp 65001 >nul
title AI Novel Generator 启动中...

echo ============================================================
echo 正在启动 AI 小说生成器...
echo 当前目录: %cd%
echo ============================================================

:: 检查 python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python 环境！
    echo 请确保已安装 Python 并添加到系统环境变量 PATH。
    pause
    exit /b
)

:: 运行程序
echo 正在加载模块...
python run.py

:: 程序结束后暂停，防止窗口闪退
echo ============================================================
echo 程序已停止运行。按任意键关闭此窗口...
pause