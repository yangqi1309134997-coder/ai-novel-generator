"""
章节蓝图解析工具
解析章节蓝图为结构化数据

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 中文数字映射
CHINESE_NUM_MAP = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '百': 100, '千': 1000
}


def chinese_to_number(chinese_num: str) -> int:
    """将中文数字转换为阿拉伯数字"""
    chinese_num = chinese_num.strip()

    # 如果已经是数字，直接返回
    if chinese_num.isdigit():
        return int(chinese_num)

    # 简单的中文数字转换（支持一到九十九）
    if len(chinese_num) == 1:
        return CHINESE_NUM_MAP.get(chinese_num, 0)

    result = 0
    if '十' in chinese_num:
        parts = chinese_num.split('十')
        tens = CHINESE_NUM_MAP.get(parts[0], 1) if parts[0] else 1
        ones = CHINESE_NUM_MAP.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        result = tens * 10 + ones
    else:
        for char in chinese_num:
            if char in CHINESE_NUM_MAP:
                result = result * 10 + CHINESE_NUM_MAP[char]

    return result if result > 0 else 0


@dataclass
class ChapterInfo:
    """章节信息"""
    number: int
    title: str = ""
    position: str = ""  # 章节定位
    purpose: str = ""  # 核心作用
    suspense: str = "中等"  # 悬念密度
    foreshadowing: str = ""  # 伏笔操作
    twist_level: str = "★☆☆☆☆"  # 认知颠覆
    summary: str = ""  # 本章简述

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'number': self.number,
            'title': self.title,
            'position': self.position,
            'purpose': self.purpose,
            'suspense': self.suspense,
            'foreshadowing': self.foreshadowing,
            'twist_level': self.twist_level,
            'summary': self.summary,
        }


class ChapterBlueprintParser:
    """章节蓝图解析器"""

    # 正则表达式模式 - 支持阿拉伯数字和中文数字
    CHAPTER_PATTERN = re.compile(r'第\s*([零一二三四五六七八九十百千\d]+)\s*章\s*[-–—:：\s]\s*(.+?)(?=\n|$)')
    CHAPTER_SPLIT_PATTERN = re.compile(r'第\s*[零一二三四五六七八九十百千\d]+\s*章')
    FIELD_PATTERN = re.compile(r'(.+?)[：:]\s*(.+?)(?=\n|$)')

    def parse_blueprint(self, blueprint: str) -> List[ChapterInfo]:
        """
        解析章节蓝图

        Args:
            blueprint: 章节蓝图文本

        Returns:
            章节信息列表
        """
        if not blueprint:
            return []

        chapters = []

        # 分割章节
        chapter_blocks = self._split_chapters(blueprint)

        for block in chapter_blocks:
            chapter_info = self._parse_chapter_block(block)
            if chapter_info:
                chapters.append(chapter_info)

        logger.info(f"[蓝图解析] 解析到 {len(chapters)} 个章节")
        return chapters

    def get_chapter_info(
        self,
        blueprint: str,
        chapter_number: int
    ) -> Optional[ChapterInfo]:
        """
        获取指定章节的信息

        Args:
            blueprint: 章节蓝图文本
            chapter_number: 章节号

        Returns:
            章节信息，如果不存在则返回None
        """
        chapters = self.parse_blueprint(blueprint)
        for chapter in chapters:
            if chapter.number == chapter_number:
                return chapter
        return None

    def _split_chapters(self, blueprint: str) -> List[str]:
        """
        分割章节块

        Args:
            blueprint: 章节蓝图文本

        Returns:
            章节块列表
        """
        # 找到所有章节开始位置 - 支持中文数字
        chapter_starts = []
        for match in self.CHAPTER_SPLIT_PATTERN.finditer(blueprint):
            chapter_starts.append(match.start())

        if not chapter_starts:
            return [blueprint]

        # 分割章节
        chapters = []
        for i, start in enumerate(chapter_starts):
            end = chapter_starts[i + 1] if i + 1 < len(chapter_starts) else len(blueprint)
            chapter_block = blueprint[start:end].strip()
            chapters.append(chapter_block)

        return chapters

    def _parse_chapter_block(self, block: str) -> Optional[ChapterInfo]:
        """
        解析单个章节块

        Args:
            block: 章节块文本

        Returns:
            章节信息
        """
        # 提取章节号和标题
        title_match = self.CHAPTER_PATTERN.search(block)
        if not title_match:
            return None

        # 转换章节号（支持中文数字）
        chapter_num_str = title_match.group(1)
        chapter_number = chinese_to_number(chapter_num_str)
        chapter_title = title_match.group(2).strip()

        # 提取字段
        lines = block.split('\n')
        fields = {}

        for line in lines:
            line = line.strip()
            if not line or ('第' in line and '章' in line):
                continue

            field_match = self.FIELD_PATTERN.search(line)
            if field_match:
                field_name = field_match.group(1).strip()
                field_value = field_match.group(2).strip()
                fields[field_name] = field_value

        # 构建章节信息
        return ChapterInfo(
            number=chapter_number,
            title=chapter_title,
            position=fields.get('本章定位', ''),
            purpose=fields.get('核心作用', ''),
            suspense=fields.get('情感强度', '中等'),
            foreshadowing=fields.get('伏笔操作', ''),
            twist_level=fields.get('情节张力', '★☆☆☆☆'),
            summary=fields.get('本章简述', ''),
        )

    def extract_field(self, text: str, field_name: str) -> str:
        """
        从文本中提取字段值

        Args:
            text: 文本
            field_name: 字段名

        Returns:
            字段值
        """
        pattern = re.compile(rf'{field_name}[：:]\s*(.+?)(?=\n|$)')
        match = pattern.search(text)
        return match.group(1).strip() if match else ''

    def format_chapter_for_generation(
        self,
        chapter_info: ChapterInfo
    ) -> Dict:
        """
        格式化章节信息用于生成

        Args:
            chapter_info: 章节信息

        Returns:
            格式化的字典
        """
        return {
            'chapter_number': chapter_info.number,
            'chapter_title': chapter_info.title,
            'chapter_role': chapter_info.position,
            'chapter_purpose': chapter_info.purpose,
            'suspense_level': chapter_info.suspense,
            'foreshadowing': chapter_info.foreshadowing,
            'plot_twist_level': chapter_info.twist_level,
            'chapter_summary': chapter_info.summary,
        }


# 便捷函数
def parse_chapter_blueprint(blueprint: str) -> List[ChapterInfo]:
    """解析章节蓝图的便捷函数"""
    parser = ChapterBlueprintParser()
    return parser.parse_blueprint(blueprint)


def get_chapter_info(blueprint: str, chapter_number: int) -> Optional[ChapterInfo]:
    """获取章节信息的便捷函数"""
    parser = ChapterBlueprintParser()
    return parser.get_chapter_info(blueprint, chapter_number)
