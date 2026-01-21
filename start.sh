#!/bin/bash

# AI 小说创作工具启动脚本
# 支持 Linux 和 macOS 系统

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装，请先安装 Python 3.8+"
        exit 1
    fi
    
    # 检查 pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 未安装，请先安装 pip3"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 检查依赖
    log_info "检查 Python 依赖..."
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        log_error "依赖安装失败"
        exit 1
    fi
    
    log_info "依赖检查完成"
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."
    
    # 检查 .env 文件
    if [ ! -f ".env" ]; then
        log_warn ".env 文件不存在，正在创建..."
        cp .env.example .env
        log_info "请编辑 .env 文件并填入您的 API 密钥"
        read -p "是否现在编辑 .env 文件? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    fi
    
    # 检查配置文件
    if [ ! -f "config.yaml" ]; then
        log_warn "config.yaml 文件不存在，正在创建..."
        # 这里可以创建默认的 config.yaml
        log_info "配置文件创建完成"
    fi
    
    # 创建必要的目录
    log_info "创建必要的目录..."
    mkdir -p logs cache output data backups templates project_templates plugins
    
    log_info "配置检查完成"
}

# 启动应用
start_application() {
    log_info "启动 AI 小说创作工具..."
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 检查是否在 Docker 中运行
    if [ -f "/.dockerenv" ]; then
        log_info "检测到 Docker 环境，使用 Docker 配置启动..."
        python run.py
    else
        log_info "本地环境启动..."
        
        # 检查是否使用 gunicorn
        if [ "$1" = "prod" ] || [ "$1" = "production" ]; then
            log_info "生产模式启动 (使用 gunicorn)..."
            gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 app:app
        else
            log_info "开发模式启动..."
            python run.py
        fi
    fi
}

# 停止应用
stop_application() {
    log_info "停止 AI 小说创作工具..."
    
    # 查找并杀死进程
    local pid=$(ps aux | grep "python.*run.py" | grep -v grep | awk '{print $2}')
    
    if [ -n "$pid" ]; then
        log_info "找到进程 PID: $pid"
        kill -TERM $pid
        
        # 等待进程结束
        for i in {1..30}; do
            if ! ps -p $pid > /dev/null; then
                log_info "进程已停止"
                return 0
            fi
            sleep 1
        done
        
        # 如果进程还在运行，强制杀死
        if ps -p $pid > /dev/null; then
            log_warn "进程未正常停止，强制杀死..."
            kill -KILL $pid
        fi
    else
        log_warn "未找到运行中的进程"
    fi
}

# 重启应用
restart_application() {
    log_info "重启 AI 小说创作工具..."
    stop_application
    sleep 2
    start_application
}

# 显示状态
show_status() {
    local pid=$(ps aux | grep "python.*run.py" | grep -v grep | awk '{print $2}')
    
    if [ -n "$pid" ]; then
        log_info "应用正在运行，PID: $pid"
        log_info "进程信息:"
        ps -p $pid -o pid,ppid,cmd,etime,pcpu,pmem --no-headers
    else
        log_warn "应用未运行"
    fi
}

# 显示帮助
show_help() {
    echo "AI 小说创作工具启动脚本"
    echo ""
    echo "用法: $0 [选项] [命令]"
    echo ""
    echo "命令:"
    echo "  start [prod]     启动应用 (prod: 生产模式)"
    echo "  stop            停止应用"
    echo "  restart         重启应用"
    echo "  status          显示应用状态"
    echo "  check           检查系统依赖和配置"
    echo "  help            显示此帮助信息"
    echo ""
    echo "选项:"
    echo "  -v, --verbose   详细输出"
    echo "  -q, --quiet     静默模式"
    echo ""
    echo "示例:"
    echo "  $0 start        # 开发模式启动"
    echo "  $0 start prod   # 生产模式启动"
    echo "  $0 stop         # 停止应用"
    echo "  $0 restart       # 重启应用"
    echo "  $0 status       # 查看状态"
}

# 主函数
main() {
    # 检查参数
    case "${1:-}" in
        start)
            check_dependencies
            check_config
            start_application "$2"
            ;;
        stop)
            stop_application
            ;;
        restart)
            restart_application
            ;;
        status)
            show_status
            ;;
        check)
            check_dependencies
            check_config
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口
main "$@"