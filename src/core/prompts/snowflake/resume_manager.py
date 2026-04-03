"""
断点续传管理器
管理生成过程中的阶段性数据持久化

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class PartialArchitectureData:
    """阶段性架构数据"""
    # 架构相关
    core_seed_result: str = ""
    character_dynamics_result: str = ""
    world_building_result: str = ""
    plot_arch_result: str = ""
    character_state_result: str = ""

    # 章节蓝图相关
    chapter_blueprint: str = ""
    current_chapter_number: int = 0

    # 元数据
    current_step: str = ""
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PartialArchitectureData':
        """从字典创建"""
        return cls(**data)


class PartialDataManager:
    """断点续传数据管理器"""

    def __init__(self, filepath: str):
        """
        初始化断点续传管理器

        Args:
            filepath: 项目文件路径
        """
        self.filepath = Path(filepath)
        self.partial_file = self.filepath / "partial_architecture.json"

    def load(self) -> PartialArchitectureData:
        """
        加载阶段性数据

        Returns:
            PartialArchitectureData对象
        """
        if not self.partial_file.exists():
            logger.info(f"[断点续传] 未找到阶段性数据文件: {self.partial_file}")
            return PartialArchitectureData()

        try:
            with open(self.partial_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"[断点续传] 成功加载阶段性数据，当前步骤: {data.get('current_step', '未知')}")
            return PartialArchitectureData.from_dict(data)

        except Exception as e:
            logger.warning(f"[断点续传] 加载阶段性数据失败: {e}")
            return PartialArchitectureData()

    def save(self, data: PartialArchitectureData) -> bool:
        """
        保存阶段性数据

        Args:
            data: 阶段性数据

        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            self.partial_file.parent.mkdir(parents=True, exist_ok=True)

            # 保存数据
            with open(self.partial_file, "w", encoding="utf-8") as f:
                json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info(f"[断点续传] 阶段性数据已保存: {self.partial_file}")
            return True

        except Exception as e:
            logger.error(f"[断点续传] 保存阶段性数据失败: {e}")
            return False

    def clear(self) -> bool:
        """
        清除阶段性数据

        Returns:
            是否清除成功
        """
        try:
            if self.partial_file.exists():
                self.partial_file.unlink()
                logger.info(f"[断点续传] 阶段性数据已清除: {self.partial_file}")
            return True

        except Exception as e:
            logger.error(f"[断点续传] 清除阶段性数据失败: {e}")
            return False

    def exists(self) -> bool:
        """
        检查是否存在阶段性数据

        Returns:
            是否存在
        """
        return self.partial_file.exists()


class ResumeManager:
    """断点续传管理器"""

    def __init__(self, filepath: str):
        """
        初始化断点续传管理器

        Args:
            filepath: 项目文件路径
        """
        self.filepath = filepath
        self.data_manager = PartialDataManager(filepath)

    def can_resume_architecture(self) -> bool:
        """
        检查是否可以恢复架构生成

        Returns:
            是否可以恢复
        """
        data = self.data_manager.load()
        return bool(data.core_seed_result or data.character_dynamics_result)

    def can_resume_blueprint(self) -> bool:
        """
        检查是否可以恢复章节蓝图生成

        Returns:
            是否可以恢复
        """
        data = self.data_manager.load()
        return bool(data.chapter_blueprint and data.current_chapter_number > 0)

    def get_resume_info(self) -> Dict[str, Any]:
        """
        获取恢复信息

        Returns:
            恢复信息字典
        """
        data = self.data_manager.load()

        return {
            "has_partial_data": self.data_manager.exists(),
            "current_step": data.current_step,
            "architecture_complete": bool(
                data.core_seed_result and
                data.character_dynamics_result and
                data.world_building_result and
                data.plot_arch_result
            ),
            "blueprint_progress": {
                "current": data.current_chapter_number,
                "blueprint": data.chapter_blueprint[:200] + "..." if len(data.chapter_blueprint) > 200 else data.chapter_blueprint
            }
        }

    def clear_all(self) -> bool:
        """
        清除所有阶段性数据

        Returns:
            是否清除成功
        """
        return self.data_manager.clear()


# 便捷函数
def create_resume_manager(filepath: str) -> ResumeManager:
    """创建断点续传管理器"""
    return ResumeManager(filepath)
