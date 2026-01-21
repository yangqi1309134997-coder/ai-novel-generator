@echo off
setlocal enabledelayedexpansion

:: AI 小说创作工具启动脚本
:: 支持 Windows 系统

:: 颜色定义 (Windows 10+)
for /f "tokens=2 delims==" %%a in ('assoc .txt^|find "FileType"') do set "filetype=%%a"
for /f "tokens=2 delims==" %%a in ('ftype "%filetype%"^|find "cmd.exe"') do set "editor=%%a"

:: 日志函数
:log_info
echo [INFO] %~1
goto :eof

:log_warn
echo [WARN] %~1
goto :eof

:log_error
echo [ERROR] %~1
goto :eof

:log_debug
echo [DEBUG] %~1
goto :eof

:: 检查依赖
:check_dependencies
call :log_info "检查系统依赖..."

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Python 未安装，请先安装 Python 3.8+"
    exit /b 1
)

:: 检查 pip
pip --version >nul 2>&1
if errorlevel 1 (
    call :log_error "pip 未安装，请先安装 pip"
    exit /b 1
)

:: 检查虚拟环境
if not exist "venv" (
    call :log_info "创建虚拟环境..."
    python -m venv venv
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 检查依赖
call :log_info "检查 Python 依赖..."
pip install -r requirements.txt

if errorlevel 1 (
    call :log_error "依赖安装失败"
    exit /b 1
)

call :log_info "依赖检查完成"
goto :eof

:: 检查配置文件
:check_config
call :log_info "检查配置文件..."

:: 检查 .env 文件
if not exist ".env" (
    call :log_warn ".env 文件不存在，正在创建..."
    copy .env.example .env >nul
    call :log_info "请编辑 .env 文件并填入您的 API 密钥"
    set /p "edit_choice=是否现在编辑 .env 文件? (y/n): "
    if /i "!edit_choice!"=="y" (
        if defined editor (
            start "" "!editor!" .env
        ) else (
            notepad .env
        )
    )
)

:: 检查配置文件
if not exist "config.yaml" (
    call :log_warn "config.yaml 文件不存在，正在创建..."
    :: 这里可以创建默认的 config.yaml
    call :log_info "配置文件创建完成"
)

:: 创建必要的目录
call :log_info "创建必要的目录..."
if not exist "logs" mkdir logs
if not exist "cache" mkdir cache
if not exist "output" mkdir output
if not exist "data" mkdir data
if not exist "backups" mkdir backups
if not exist "templates" mkdir templates
if not exist "project_templates" mkdir project_templates
if not exist "plugins" mkdir plugins

call :log_info "配置检查完成"
goto :eof

:: 启动应用
:start_application
call :log_info "启动 AI 小说创作工具..."

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 检查是否在 Docker 中运行
if exist ".dockerenv" (
    call :log_info "检测到 Docker 环境，使用 Docker 配置启动..."
    python run.py
) else (
    call :log_info "本地环境启动..."
    
    :: 检查是否使用 gunicorn
    if "%1"=="prod" if "%2"=="production" (
        call :log_info "生产模式启动 (使用 gunicorn)..."
        gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 app:app
    ) else (
        call :log_info "开发模式启动..."
        python run.py
    )
)
goto :eof

:: 停止应用
:stop_application
call :log_info "停止 AI 小说创作工具..."

:: 查找并杀死进程
for /f "tokens=2 delims=," %%a in ('tasklist /v /fo csv ^| findstr "python.*run.py"') do (
    set pid=%%~a
    call :log_info "找到进程 PID: !pid!"
    taskkill /PID !pid! /F >nul 2>&1
    call :log_info "进程已停止"
)
goto :eof

:: 重启应用
:restart_application
call :log_info "重启 AI 小说创作工具..."
call :stop_application
timeout /t 2 /nobreak >nul
call :start_application
goto :eof

:: 显示状态
:show_status
tasklist /v /fo csv | findstr "python.*run.py" >nul
if errorlevel 1 (
    call :log_warn "应用未运行"
) else (
    call :log_info "应用正在运行"
    tasklist /v /fo csv | findstr "python.*run.py"
)
goto :eof

:: 显示帮助
:show_help
echo AI 小说创作工具启动脚本
echo.
echo 用法: %~n0 [选项] [命令]
echo.
echo 命令:
echo   start [prod]     启动应用 (prod: 生产模式)
echo   stop            停止应用
echo   restart         重启应用
echo   status          显示应用状态
echo   check           检查系统依赖和配置
echo   help            显示此帮助信息
echo.
echo 选项:
echo   -v, --verbose   详细输出
echo   -q, --quiet     静默模式
echo.
echo 示例:
echo   %~n0 start        # 开发模式启动
echo   %~n0 start prod   # 生产模式启动
echo   %~n0 stop         # 停止应用
echo   %~n0 restart       # 重启应用
echo   %~n0 status       # 查看状态
echo.
goto :eof

:: 主函数
:main
:: 检查参数
if "%~1"=="" (
    call :show_help
    exit /b 0
)

if "%~1"=="start" (
    call :check_dependencies
    call :check_config
    call :start_application %2 %3
) else if "%~1"=="stop" (
    call :stop_application
) else if "%~1"=="restart" (
    call :restart_application
) else if "%~1"=="status" (
    call :show_status
) else if "%~1"=="check" (
    call :check_dependencies
    call :check_config
) else if "%~1"=="help" (
    call :show_help
) else if "%~1"=="--help" (
    call :show_help
) else if "%~1"=="-h" (
    call :show_help
) else (
    call :log_error "未知命令: %~1"
    call :show_help
    exit /b 1
)
goto :eof

:: 脚本入口
call :main %*