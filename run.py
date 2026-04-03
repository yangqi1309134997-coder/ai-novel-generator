#!/usr/bin/env python3
"""
AI Novel Generator 4.5 Beta - 入口文件

重构版本，集成连贯性系统、提示词系统、统一API客户端

使用方法：
    python run.py

环境变量：
    NOVEL_TOOL_HOST - 服务器地址（默认: 127.0.0.1）
    NOVEL_TOOL_PORT - 端口（默认: 7860）
    NOVEL_TOOL_SHARE - 是否开启公网访问（默认: false）

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""

import sys
import os
import logging
from pathlib import Path

# 关闭输出缓冲，确保 print 立即显示
os.environ['PYTHONUNBUFFERED'] = '1'

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置日志 - 只输出到文件，不干扰控制台
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "app_startup.log", encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    import atexit

    try:
        print("=" * 60, flush=True)
        print("  AI Novel Generator 4.5 Beta", flush=True)
        print("  智能小说创作工具 | 22+ AI 提供商", flush=True)
        print("  版权所有 (c) 2026 新疆幻城网安科技有限责任公司", flush=True)
        print("=" * 60, flush=True)
        print(flush=True)
        print("[*] 正在初始化，请稍候...", flush=True)
        print(flush=True)

        logger.info("=" * 60)
        logger.info("AI Novel Generator 4.5 Beta")
        logger.info("智能连贯性系统 | 22+提供商 | 灵活提示词")
        logger.info("=" * 60)

        # 注册退出时的API日志摘要
        def on_exit():
            try:
                from src.utils.api_logger import get_api_logger
                get_api_logger().summary()
            except:
                pass

        atexit.register(on_exit)

        # 导入并启动应用
        from src.ui.app import main as run_app
        run_app()

    except KeyboardInterrupt:
        print("\n用户中断，程序退出", flush=True)
    except Exception as e:
        print(f"\n[错误] 启动失败: {e}", flush=True)
        logger.error(f"启动失败: {e}", exc_info=True)
        input("按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
