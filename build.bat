@echo off
chcp 65001 >nul 2>&1
title AI Novel Generator 4.5 - 编译打包
color 0B

echo ============================================================
echo       AI Novel Generator 4.5 - 编译打包
echo ============================================================
echo.

:: 检查 PyInstaller
pip show pyinstaller >nul 2>&1
if %errorLevel% neq 0 (
    echo [安装] 正在安装 PyInstaller...
    pip install pyinstaller
)

:: 检查 Python 版本
echo [检查] Python 版本:
python --version
echo.

:: 清理旧的编译文件
echo [1/3] 清理旧文件...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
echo       完成

:: 执行编译
echo.
echo [2/3] 开始编译（这可能需要几分钟）...
echo.
pyinstaller --clean --noconfirm ai_novel_generator.spec
if %errorLevel% neq 0 (
    echo.
    echo [错误] 编译失败！请检查错误信息。
    pause
    exit /b 1
)

echo.
echo [3/3] 编译完成，整理发布文件...

:: 创建发布目录
set "RELEASE_DIR=release\AI_Novel_Generator_4.5"
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"

:: 复制编译结果
xcopy "dist\AI_Novel_Generator\*" "%RELEASE_DIR%\" /E /I /Y /Q

:: 复制安装脚本
copy "installer\install.bat" "%RELEASE_DIR%\install.bat" >nul

:: 创建启动脚本
echo @echo off > "%RELEASE_DIR%\启动.bat"
echo chcp 65001 ^>nul 2^>^&1 >> "%RELEASE_DIR%\启动.bat"
echo title AI 小说工坊 4.5 >> "%RELEASE_DIR%\启动.bat"
echo color 0A >> "%RELEASE_DIR%\启动.bat"
echo echo ============================================================ >> "%RELEASE_DIR%\启动.bat"
echo echo       AI Novel Generator 4.5 Beta - 智能小说创作工具 >> "%RELEASE_DIR%\启动.bat"
echo echo       版权所有 (c) 2026 新疆幻城网安科技有限责任公司 >> "%RELEASE_DIR%\启动.bat"
echo echo ============================================================ >> "%RELEASE_DIR%\启动.bat"
echo echo. >> "%RELEASE_DIR%\启动.bat"
echo echo [1] 正在启动程序，请稍候... >> "%RELEASE_DIR%\启动.bat"
echo echo [2] 启动完成后请在浏览器中访问: >> "%RELEASE_DIR%\启动.bat"
echo echo. >> "%RELEASE_DIR%\启动.bat"
echo echo       http://127.0.0.1:7860 >> "%RELEASE_DIR%\启动.bat"
echo echo. >> "%RELEASE_DIR%\启动.bat"
echo echo [3] 如需停止服务器，请关闭此窗口或按 Ctrl+C >> "%RELEASE_DIR%\启动.bat"
echo echo. >> "%RELEASE_DIR%\启动.bat"
echo echo ============================================================ >> "%RELEASE_DIR%\启动.bat"
echo echo. >> "%RELEASE_DIR%\启动.bat"
echo AI_Novel_Generator.exe >> "%RELEASE_DIR%\启动.bat"
echo echo. >> "%RELEASE_DIR%\启动.bat"
echo echo 程序已退出 >> "%RELEASE_DIR%\启动.bat"
echo pause >> "%RELEASE_DIR%\启动.bat"

:: 创建 README
echo AI Novel Generator 4.5 Beta > "%RELEASE_DIR%\README.txt"
echo 智能连贯性系统 | 22+提供商 | 灵活提示词 >> "%RELEASE_DIR%\README.txt"
echo. >> "%RELEASE_DIR%\README.txt"
echo 使用方法: >> "%RELEASE_DIR%\README.txt"
echo   1. 双击 启动.bat 运行程序 >> "%RELEASE_DIR%\README.txt"
echo   2. 或双击 install.bat 安装到系统 >> "%RELEASE_DIR%\README.txt"
echo   3. 启动后浏览器自动打开 http://127.0.0.1:7860 >> "%RELEASE_DIR%\README.txt"
echo. >> "%RELEASE_DIR%\README.txt"
echo 首次使用请先在"系统设置"-"接口管理"中配置AI提供商 >> "%RELEASE_DIR%\README.txt"
echo 推荐使用 Ollama（本地免费）或 OpenAI >> "%RELEASE_DIR%\README.txt"
echo. >> "%RELEASE_DIR%\README.txt"
echo 版权所有 (c) 2026 新疆幻城网安科技有限责任公司 >> "%RELEASE_DIR%\README.txt"

:: 压缩
echo.
echo 正在压缩为 ZIP...
powershell -Command "Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath 'release\AI_Novel_Generator_4.5_Portable.zip' -Force"
echo.
echo ============================================================
echo       编译打包完成！
echo ============================================================
echo.
echo 发布文件位于:
echo   文件夹: %RELEASE_DIR%\
echo   ZIP包: release\AI_Novel_Generator_4.5_Portable.zip
echo.
echo 使用方法:
echo   直接解压 ZIP 运行 启动.bat
echo   或运行 install.bat 安装到系统
echo.
pause
