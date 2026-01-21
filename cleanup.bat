@echo off
setlocal enabledelayedexpansion

echo ========================================
echo AI小说创作工具Pro - 清理脚本
echo ========================================
echo 版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
echo 作者：幻城
echo ========================================
echo.

REM 检查命令行参数，如果传入 -y 或 --yes 则跳过确认
set SKIP_CONFIRM=0
if "%~1"=="-y" set SKIP_CONFIRM=1
if "%~1"=="--yes" set SKIP_CONFIRM=1

REM 显示清理警告信息
echo [警告] 此操作将清理以下内容：
echo   - cache/ 目录下的所有文件和子目录
echo   - logs/ 目录下的所有日志文件
echo   - config/backups/ 目录下的所有备份文件
echo   - exports/ 目录下的所有导出文件
echo   - projects/ 目录下的所有项目数据
echo   - 临时区/ 目录下的所有文件
echo   - 所有 __pycache__ 目录
echo   - 所有 .pyc 文件
echo   - 所有 .spec 文件
echo   - 临时文件 0 和 1
echo.
echo [保留] 以下内容将被保留：
echo   - config/ 目录本身
echo   - config/novel_tool_config.json（主配置文件）
echo   - logs/ 目录本身
echo   - 其他必要的目录结构
echo.

REM 如果没有跳过确认，则询问用户
if %SKIP_CONFIRM%==0 (
    echo 请确认是否继续清理？(Y/N)
    set /p CONFIRM=
    if /i not "!CONFIRM!"=="Y" (
        echo 已取消清理操作。
        pause
        exit /b 0
    )
)

echo.
echo ========================================
echo 开始清理...
echo ========================================
echo.

REM 初始化文件计数器
set TOTAL_FILES=0

REM ========================================
REM 1. 清理 cache/ 目录
REM ========================================
echo [1/10] 清理 cache/ 目录...
if exist cache (
    for /f %%a in ('dir /s /b cache ^| find /c /v ""') do set CACHE_COUNT=%%a
    rmdir /s /q cache
    echo       已删除 !CACHE_COUNT! 个文件/目录
    set /a TOTAL_FILES+=CACHE_COUNT
) else (
    echo       cache/ 目录不存在，跳过
)
mkdir cache 2>nul
echo. > cache\response_cache.json
echo       已创建空 cache/ 目录

REM ========================================
REM 2. 清理 logs/ 目录中的日志文件（保留目录本身）
REM ========================================
echo [2/10] 清理 logs/ 目录中的日志文件...
if exist logs (
    for /f %%a in ('dir /s /b logs\*.log 2^>nul ^| find /c /v ""') do set LOG_COUNT=%%a
    if !LOG_COUNT! GTR 0 (
        del /f /q logs\*.log 2>nul
        echo       已删除 !LOG_COUNT! 个日志文件
        set /a TOTAL_FILES+=LOG_COUNT
    ) else (
        echo       logs/ 目录中没有日志文件，跳过
    )
) else (
    echo       logs/ 目录不存在，跳过
    mkdir logs 2>nul
)

REM ========================================
REM 3. 清理 config/backups/ 目录
REM ========================================
echo [3/10] 清理 config/backups/ 目录...
if exist config\backups (
    for /f %%a in ('dir /s /b config\backups ^| find /c /v ""') do set BACKUP_COUNT=%%a
    rmdir /s /q config\backups
    echo       已删除 !BACKUP_COUNT! 个备份文件
    set /a TOTAL_FILES+=BACKUP_COUNT
) else (
    echo       config/backups/ 目录不存在，跳过
)
mkdir config\backups 2>nul

REM ========================================
REM 4. 清理 exports/ 目录
REM ========================================
echo [4/10] 清理 exports/ 目录...
if exist exports (
    for /f %%a in ('dir /s /b exports ^| find /c /v ""') do set EXPORT_COUNT=%%a
    rmdir /s /q exports
    echo       已删除 !EXPORT_COUNT! 个导出文件
    set /a TOTAL_FILES+=EXPORT_COUNT
) else (
    echo       exports/ 目录不存在，跳过
)
mkdir exports 2>nul

REM ========================================
REM 5. 清理 projects/ 目录
REM ========================================
echo [5/10] 清理 projects/ 目录...
if exist projects (
    for /f %%a in ('dir /s /b projects ^| find /c /v ""') do set PROJECT_COUNT=%%a
    rmdir /s /q projects
    echo       已删除 !PROJECT_COUNT! 个项目文件
    set /a TOTAL_FILES+=PROJECT_COUNT
) else (
    echo       projects/ 目录不存在，跳过
)
mkdir projects 2>nul

REM ========================================
REM 6. 清理 临时区/ 目录
REM ========================================
echo [6/10] 清理 临时区/ 目录...
if exist 临时区 (
    for /f %%a in ('dir /s /b 临时区 ^| find /c /v ""') do set TEMP_COUNT=%%a
    rmdir /s /q 临时区
    echo       已删除 !TEMP_COUNT! 个临时文件
    set /a TOTAL_FILES+=TEMP_COUNT
) else (
    echo       临时区/ 目录不存在，跳过
)
mkdir 临时区 2>nul

REM ========================================
REM 7. 清理所有 __pycache__ 目录
REM ========================================
echo [7/10] 清理所有 __pycache__ 目录...
set PYCACHE_COUNT=0
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        set /a PYCACHE_COUNT+=1
    )
)
echo       已删除 !PYCACHE_COUNT! 个 __pycache__ 目录

REM ========================================
REM 8. 清理所有 .pyc 文件
REM ========================================
echo [8/10] 清理所有 .pyc 文件...
set PYC_COUNT=0
for /r . %%f in (*.pyc) do (
    if exist "%%f" (
        del /f /q "%%f" 2>nul
        set /a PYC_COUNT+=1
    )
)
echo       已删除 !PYC_COUNT! 个 .pyc 文件
set /a TOTAL_FILES+=PYC_COUNT

REM ========================================
REM 9. 清理所有 .spec 文件
REM ========================================
echo [9/10] 清理所有 .spec 文件...
set SPEC_COUNT=0
for %%f in (*.spec) do (
    if exist "%%f" (
        del /f /q "%%f" 2>nul
        set /a SPEC_COUNT+=1
    )
)
echo       已删除 !SPEC_COUNT! 个 .spec 文件
set /a TOTAL_FILES+=SPEC_COUNT

REM ========================================
REM 10. 清理临时文件 0 和 1
REM ========================================
echo [10/10] 清理临时文件 0 和 1...
set TEMP_FILE_COUNT=0
if exist 0 (
    del /f /q 0 2>nul
    set /a TEMP_FILE_COUNT+=1
)
if exist 1 (
    del /f /q 1 2>nul
    set /a TEMP_FILE_COUNT+=1
)
echo       已删除 !TEMP_FILE_COUNT! 个临时文件
set /a TOTAL_FILES+=TEMP_FILE_COUNT

REM ========================================
REM 显示清理完成信息
REM ========================================
echo.
echo ========================================
echo 清理完成！
echo ========================================
echo 总共清理了 !TOTAL_FILES! 个文件/目录
echo.
echo 项目已清理完成，保留了必要的配置和目录结构。
echo ========================================
echo.
echo 使用说明：
echo   - 直接运行此脚本会提示确认
echo   - 使用 -y 或 --yes 参数可跳过确认直接清理
echo   - 示例：cleanup.bat -y
echo ========================================

pause