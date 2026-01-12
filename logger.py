"""
日志和监控模块 - 生产级别的日志系统

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 日志文件配置
LOG_FILE = os.path.join(LOG_DIR, f"novel_tool_{datetime.now().strftime('%Y%m%d')}.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, f"errors_{datetime.now().strftime('%Y%m%d')}.log")


def setup_logger(
    name: str,
    log_level: int = logging.INFO,
    log_to_file: bool = True,
    force_reconfigure: bool = False
) -> logging.Logger:
    """
    设置生产级别的logger
    
    Args:
        name: logger名称
        log_level: 日志级别
        log_to_file: 是否输出到文件
        force_reconfigure: 是否强制重新配置（清除旧的handler）
    
    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 如果强制重配，清除现有handler
    if force_reconfigure:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    # 避免重复添加handler
    elif logger.handlers:
        return logger
    
    # 控制台输出格式
    console_formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件输出（如果启用）
    if log_to_file:
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 通用日志
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # 错误日志 - 始终添加，确保ERROR级别的日志一定会被捕获
        error_handler = logging.handlers.RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
    
    return logger


class PerformanceMonitor:
    """性能监控工具"""
    
    def __init__(self):
        self.logger = setup_logger("PerformanceMonitor")
        self.metrics = {}
    
    def record_metric(self, name: str, value: float, unit: str = "ms") -> None:
        """记录性能指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(value)
        
        # 只保存最近1000条记录
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
    
    def get_average(self, name: str) -> Optional[float]:
        """获取平均值"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        return sum(self.metrics[name]) / len(self.metrics[name])
    
    def report(self) -> str:
        """生成性能报告"""
        if not self.metrics:
            return "暂无性能数据"
        
        report = "=== 性能监控报告 ===\n"
        for name, values in self.metrics.items():
            if values:
                avg = sum(values) / len(values)
                max_val = max(values)
                min_val = min(values)
                report += f"{name}: 平均={avg:.2f}ms, 最大={max_val:.2f}ms, 最小={min_val:.2f}ms, 次数={len(values)}\n"
        
        return report


# 全局实例
_logger = setup_logger("NovelTool")
_performance_monitor = PerformanceMonitor()


def get_logger(name: str = "NovelTool") -> logging.Logger:
    """获取logger实例"""
    return logging.getLogger(name)


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器"""
    return _performance_monitor
