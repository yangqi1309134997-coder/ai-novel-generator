#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 小说创作工具启动脚本
支持多种运行模式和配置管理
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app import create_app
    from config import load_config
    from logger import setup_logger
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有依赖都已安装")
    sys.exit(1)


class NovelGeneratorRunner:
    """AI 小说创作工具运行器"""
    
    def __init__(self):
        self.app = None
        self.config = None
        self.logger = None
        
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if config_path:
                self.config = load_config(config_path)
            else:
                # 按优先级加载配置文件
                config_files = [
                    'config.yaml',
                    'config.yml',
                    'config.json',
                    '.env'
                ]
                
                for config_file in config_files:
                    if os.path.exists(config_file):
                        self.config = load_config(config_file)
                        break
                else:
                    # 如果没有找到配置文件，使用默认配置
                    self.config = self.get_default_config()
                    
            return self.config
            
        except Exception as e:
            print(f"配置加载失败: {e}")
            self.config = self.get_default_config()
            return self.config
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'api': {
                'openai': {
                    'enabled': False,
                    'api_key': '',
                    'model': 'gpt-4',
                    'max_tokens': 4000,
                    'temperature': 0.7
                },
                'glm': {
                    'enabled': False,
                    'api_key': '',
                    'model': 'glm-4',
                    'max_tokens': 4000,
                    'temperature': 0.7
                }
            },
            'system': {
                'logging': {
                    'level': 'INFO',
                    'file': 'logs/novel_generator.log',
                    'console_output': True
                },
                'concurrency': {
                    'max_workers': 4,
                    'request_timeout': 30
                }
            },
            'export': {
                'default_format': 'markdown',
                'output_directory': 'output'
            },
            'ui': {
                'theme': 'light',
                'language': 'zh-CN'
            }
        }
    
    def setup_logging(self) -> None:
        """设置日志"""
        if not self.config:
            return
            
        log_config = self.config.get('system', {}).get('logging', {})
        
        # 设置日志级别
        level = getattr(logging, log_config.get('level', 'INFO').upper(), logging.INFO)
        
        # 创建日志目录
        log_file = log_config.get('file', 'logs/novel_generator.log')
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 配置日志
        self.logger = setup_logger(
            level=level,
            log_file=log_file,
            console_output=log_config.get('console_output', True)
        )
    
    def create_directories(self) -> None:
        """创建必要的目录"""
        if not self.config:
            return
            
        directories = [
            self.config.get('export', {}).get('output_directory', 'output'),
            'logs',
            'cache',
            'data',
            'backups',
            'templates',
            'project_templates',
            'plugins'
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                if self.logger:
                    self.logger.info(f"创建目录: {directory}")
    
    def create_app(self) -> None:
        """创建 Flask 应用"""
        try:
            self.app = create_app(self.config)
            if self.logger:
                self.logger.info("Flask 应用创建成功")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Flask 应用创建失败: {e}")
            else:
                print(f"Flask 应用创建失败: {e}")
            sys.exit(1)
    
    def run_server(
        self,
        host: str = '127.0.0.1',
        port: int = 8000,
        debug: bool = False,
        use_reloader: bool = True
    ) -> None:
        """运行服务器"""
        if not self.app:
            print("应用未初始化")
            return
            
        if self.logger:
            self.logger.info(f"启动服务器: http://{host}:{port}")
            self.logger.info(f"调试模式: {debug}")
        
        try:
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                use_reloader=use_reloader,
                threaded=True
            )
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("服务器被用户中断")
        except Exception as e:
            if self.logger:
                self.logger.error(f"服务器运行错误: {e}")
            else:
                print(f"服务器运行错误: {e}")
    
    def run_gunicorn(
        self,
        host: str = '127.0.0.1',
        port: int = 8000,
        workers: int = 4,
        timeout: int = 120
    ) -> None:
        """运行 Gunicorn 服务器"""
        try:
            import gunicorn.app.base
            from gunicorn.six import StringIO
            
            class GunicornNovelGenerator(gunicorn.app.base.BaseApplication):
                def __init__(self, app, options=None):
                    self.application = app
                    self.options = options or {}
                    super().__init__()
                
                def load_config(self):
                    config = {key: value for key, value in self.options.items()}
                    for key, value in config.items():
                        self.cfg.set(key.lower(), value)
                
                def load(self):
                    return self.application
            
            options = {
                'bind': f'{host}:{port}',
                'workers': workers,
                'timeout': timeout,
                'worker_class': 'sync',
                'worker_connections': 1000,
                'max_requests': 1000,
                'max_requests_jitter': 50,
                'preload_app': True,
                'accesslog': '-',
                'errorlog': '-',
                'loglevel': 'info',
                'logger_class': 'gunicorn.glogging.Logger',
                'worker_tmp_dir': '/tmp'
            }
            
            if self.logger:
                self.logger.info(f"启动 Gunicorn 服务器: http://{host}:{port}")
                self.logger.info(f"工作进程数: {workers}")
            
            GunicornNovelGenerator(self.app, options).run()
            
        except ImportError:
            print("Gunicorn 未安装，请先安装: pip install gunicorn")
            self.run_server(host, port, debug=False, use_reloader=False)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Gunicorn 运行错误: {e}")
            else:
                print(f"Gunicorn 运行错误: {e}")
    
    def run_health_check(self) -> bool:
        """运行健康检查"""
        if not self.app:
            return False
            
        try:
            with self.app.test_client() as client:
                response = client.get('/health')
                return response.status_code == 200
        except Exception:
            return False


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='AI 小说创作工具启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                           # 开发模式启动
  %(prog)s --prod                    # 生产模式启动
  %(prog)s --host 0.0.0.0 --port 80  # 指定主机和端口
  %(prog)s --config custom.yaml     # 使用自定义配置文件
  %(prog)s --check                  # 检查配置
  %(prog)s --health                 # 健康检查
        """
    )
    
    # 基本选项
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='配置文件路径'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='服务器主机地址 (默认: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='服务器端口 (默认: 8000)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )
    
    parser.add_argument(
        '--prod', '--production',
        action='store_true',
        help='生产模式启动 (使用 Gunicorn)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Gunicorn 工作进程数 (默认: 4)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=120,
        help='Gunicorn 超时时间 (默认: 120)'
    )
    
    parser.add_argument(
        '--no-reloader',
        action='store_true',
        help='禁用代码重载'
    )
    
    # 实用工具选项
    parser.add_argument(
        '--check',
        action='store_true',
        help='检查配置和环境'
    )
    
    parser.add_argument(
        '--health',
        action='store_true',
        help='运行健康检查'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    # 创建运行器
    runner = NovelGeneratorRunner()
    
    # 加载配置
    config = runner.load_config(args.config)
    
    # 设置日志
    runner.setup_logging()
    
    # 创建应用
    runner.create_app()
    
    # 创建必要的目录
    runner.create_directories()
    
    # 检查模式
    if args.check:
        print("✓ 配置检查完成")
        print("✓ 应用创建成功")
        print("✓ 目录结构已创建")
        return 0
    
    # 健康检查模式
    if args.health:
        if runner.run_health_check():
            print("✓ 健康检查通过")
            return 0
        else:
            print("✗ 健康检查失败")
            return 1
    
    # 生产模式
    if args.prod:
        runner.run_gunicorn(
            host=args.host,
            port=args.port,
            workers=args.workers,
            timeout=args.timeout
        )
    else:
        # 开发模式
        runner.run_server(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=not args.no_reloader
        )
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序运行错误: {e}")
        sys.exit(1)