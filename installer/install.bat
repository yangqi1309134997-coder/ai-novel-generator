@echo off
chcp 65001 >nul 2>&1
title AI Novel Generator 4.5 安装程序
color 0A

echo ============================================================
echo       AI Novel Generator 4.5 Beta - 安装程序
echo       智能连贯性系统 | 22+提供商 | 灵活提示词
echo       版权所有 (c) 2026 新疆幻城网安科技有限责任公司
echo ============================================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] 管理员权限已确认
) else (
    echo [提示] 建议以管理员身份运行安装程序
    echo.
)

:: 设置安装目录
set "INSTALL_DIR=%LOCALAPPDATA%\AI_Novel_Generator"
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "STARTMENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"

echo 默认安装目录: %INSTALL_DIR%
echo.
set /p "custom_dir=请输入安装目录（直接回车使用默认）: "
if not "%custom_dir%"=="" set "INSTALL_DIR=%custom_dir%"

echo.
echo [1/5] 创建安装目录...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\config" mkdir "%INSTALL_DIR%\config"
if not exist "%INSTALL_DIR%\projects" mkdir "%INSTALL_DIR%\projects"
if not exist "%INSTALL_DIR%\cache" mkdir "%INSTALL_DIR%\cache"
if not exist "%INSTALL_DIR%\logs" mkdir "%INSTALL_DIR%\logs"
echo       完成

echo.
echo [2/5] 复制程序文件...
:: 复制 PyInstaller 生成的 dist 目录
if exist "%~dp0dist\AI_Novel_Generator" (
    xcopy "%~dp0dist\AI_Novel_Generator\*" "%INSTALL_DIR%\" /E /I /Y /Q >nul
    echo       程序文件复制完成
) else if exist "%~dp0..\dist\AI_Novel_Generator" (
    xcopy "%~dp0..\dist\AI_Novel_Generator\*" "%INSTALL_DIR%\" /E /I /Y /Q >nul
    echo       程序文件复制完成
) else (
    echo       [错误] 未找到编译后的程序文件！
    echo       请先运行 build.bat 进行编译
    pause
    exit /b 1
)

echo.
echo [3/5] 创建快捷方式...
:: 创建 VBS 脚本来生成快捷方式
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\create_shortcut.vbs"
echo sLinkFile = "%DESKTOP_DIR%\AI 小说工坊.lnk" >> "%TEMP%\create_shortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\create_shortcut.vbs"
echo oLink.TargetPath = "%INSTALL_DIR%\AI_Novel_Generator.exe" >> "%TEMP%\create_shortcut.vbs"
echo oLink.WorkingDirectory = "%INSTALL_DIR%" >> "%TEMP%\create_shortcut.vbs"
echo oLink.Description = "AI Novel Generator 4.5 - 智能小说创作工具" >> "%TEMP%\create_shortcut.vbs"
echo oLink.Save >> "%TEMP%\create_shortcut.vbs"
cscript //nologo "%TEMP%\create_shortcut.vbs" 2>nul
del "%TEMP%\create_shortcut.vbs" 2>nul
echo       桌面快捷方式已创建

:: 开始菜单快捷方式
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\create_shortcut2.vbs"
echo sLinkFile = "%STARTMENU_DIR%\AI 小说工坊.lnk" >> "%TEMP%\create_shortcut2.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\create_shortcut2.vbs"
echo oLink.TargetPath = "%INSTALL_DIR%\AI_Novel_Generator.exe" >> "%TEMP%\create_shortcut2.vbs"
echo oLink.WorkingDirectory = "%INSTALL_DIR%" >> "%TEMP%\create_shortcut2.vbs"
echo oLink.Description = "AI Novel Generator 4.5 - 智能小说创作工具" >> "%TEMP%\create_shortcut2.vbs"
echo oLink.Save >> "%TEMP%\create_shortcut2.vbs"
cscript //nologo "%TEMP%\create_shortcut2.vbs" 2>nul
del "%TEMP%\create_shortcut2.vbs" 2>nul
echo       开始菜单快捷方式已创建

echo.
echo [4/5] 创建卸载程序...
echo @echo off > "%INSTALL_DIR%\uninstall.bat"
echo chcp 65001 ^>nul 2^>^&1 >> "%INSTALL_DIR%\uninstall.bat"
echo title 卸载 AI Novel Generator 4.5 >> "%INSTALL_DIR%\uninstall.bat"
echo echo 正在卸载 AI Novel Generator 4.5... >> "%INSTALL_DIR%\uninstall.bat"
echo echo. >> "%INSTALL_DIR%\uninstall.bat"
echo set /p "confirm=确定要卸载吗？(y/n): " >> "%INSTALL_DIR%\uninstall.bat"
echo if /i "%%confirm%%"=="y" ( >> "%INSTALL_DIR%\uninstall.bat"
echo     del "%DESKTOP_DIR%\AI 小说工坊.lnk" 2^>nul >> "%INSTALL_DIR%\uninstall.bat"
echo     del "%STARTMENU_DIR%\AI 小说工坊.lnk" 2^>nul >> "%INSTALL_DIR%\uninstall.bat"
echo     echo 正在删除程序文件... >> "%INSTALL_DIR%\uninstall.bat"
echo     cd /d "%%TEMP%%" >> "%INSTALL_DIR%\uninstall.bat"
echo     rmdir /s /q "%INSTALL_DIR%" >> "%INSTALL_DIR%\uninstall.bat"
echo     echo 卸载完成！ >> "%INSTALL_DIR%\uninstall.bat"
echo ) else ( >> "%INSTALL_DIR%\uninstall.bat"
echo     echo 已取消卸载 >> "%INSTALL_DIR%\uninstall.bat"
echo ) >> "%INSTALL_DIR%\uninstall.bat"
echo pause >> "%INSTALL_DIR%\uninstall.bat"
echo       卸载程序已创建

echo.
echo [5/5] 注册表写入...
reg add "HKCU\Software\AI_Novel_Generator" /v "InstallPath" /t REG_SZ /d "%INSTALL_DIR%" /f >nul 2>&1
reg add "HKCU\Software\AI_Novel_Generator" /v "Version" /t REG_SZ /d "4.5.0" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\AI_Novel_Generator" /v "DisplayName" /t REG_SZ /d "AI 小说工坊 4.5" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\AI_Novel_Generator" /v "DisplayVersion" /t REG_SZ /d "4.5.0" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\AI_Novel_Generator" /v "Publisher" /t REG_SZ /d "新疆幻城网安科技有限责任公司" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\AI_Novel_Generator" /v "UninstallString" /t REG_SZ /d "%INSTALL_DIR%\uninstall.bat" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\AI_Novel_Generator" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f >nul 2>&1
echo       注册表写入完成

echo.
echo ============================================================
echo       安装完成！
echo ============================================================
echo.
echo 安装目录: %INSTALL_DIR%
echo.
echo 使用方法:
echo   1. 双击桌面上的 "AI 小说工坊" 快捷方式启动
echo   2. 或在开始菜单中找到 "AI 小说工坊"
echo   3. 启动后浏览器自动打开 http://127.0.0.1:7860
echo.
echo 首次使用:
echo   1. 打开 "系统设置" - "接口管理"
echo   2. 选择 AI 提供商（推荐 Ollama 本地免费）
echo   3. 点击 "测试连接" 然后 "保存配置"
echo   4. 开始创作！
echo.
echo 版权所有 (c) 2026 新疆幻城网安科技有限责任公司
echo.
pause
