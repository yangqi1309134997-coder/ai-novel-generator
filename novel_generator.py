"""
小说生成模块 - 支持大纲生成、章节生成、重写等

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from api_client import get_api_client
from config import get_config

logger = logging.getLogger(__name__)

# 预设模板
PRESET_TEMPLATES = {
    "重写风格 - 默认": "用更生动、细腻的笔触重写，语言优美，保留原意和情节，但加入更多细节描写和人物内心活动。",
    "重写风格 - 玄幻仙侠": "以古典仙侠风格重写，语言古风优雅，增加仙术法宝描写、灵气意境、人物心境修炼与道心感悟，保留原情节。",
    "重写风格 - 都市言情": "现代都市言情风格重写，语言轻松甜宠或虐心，增加浪漫互动、细腻心理描写、日常生活细节，人物情感更丰富。",
    "重写风格 - 悬疑惊悚": "悬疑惊悚风格重写，语言营造紧张氛围，增加心理惊悚描写、线索铺垫、环境渲染与反转元素。",
    "重写风格 - 科幻硬核": "硬科幻风格重写，语言严谨专业，增加科学原理解释、技术细节、世界观构建，逻辑自洽。",
    "重写风格 - 武侠江湖": "金庸古龙式武侠风格重写，语言潇洒豪气，增加武功招式描写、江湖恩怨、侠义精神。",
}


@dataclass
class Chapter:
    """章节数据结构"""
    num: int
    title: str
    desc: str
    content: str = ""
    word_count: int = 0
    generated_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "num": self.num,
            "title": self.title,
            "desc": self.desc,
            "content": self.content,
            "word_count": self.word_count,
            "generated_at": self.generated_at
        }


@dataclass
class NovelProject:
    """小说项目数据结构"""
    title: str
    genre: str
    character_setting: str
    world_setting: str
    plot_idea: str
    id: Optional[str] = None
    chapters: List[Chapter] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_completed_count(self) -> int:
        """获取已完成的章节数"""
        return sum(1 for ch in self.chapters if ch.content.strip())
    
    def get_total_words(self) -> int:
        """获取总字数"""
        return sum(ch.word_count for ch in self.chapters)


class OutlineParser:
    """大纲解析器"""
    
    @staticmethod
    def parse(outline_text: str) -> Tuple[List[Chapter], str]:
        """
        解析大纲文本
        
        Returns:
            (章节列表, 错误信息)
        """
        if not outline_text or not outline_text.strip():
            return [], "大纲为空"
        
        chapters = []
        lines = [line.strip() for line in outline_text.split('\n') if line.strip()]

        chapter_count = 0
        # 支持多种常见的大纲格式，尝试多种正则
        patterns = [
            r'第\s*(\d+)\s*章[：:\s]*([^\-—–]+)[-—–]\s*(.+)',
            r'^(\d+)[\).:\s]+([^\-—–]+)[-—–]\s*(.+)',
            r'第\s*(\d+)\s*章[:：]\s*(.+)',
        ]

        for line in lines:
            matched = False
            for pat in patterns:
                match = re.match(pat, line)
                if not match:
                    continue

                # 不同 pattern 捕获组含义可能不同
                if len(match.groups()) >= 3:
                    num = int(match.group(1))
                    title = match.group(2).strip()
                    desc = match.group(3).strip()
                else:
                    # 只有两组，尝试使用第二组拆分为标题与描述
                    num = int(match.group(1))
                    rest = match.group(2).strip()
                    if '-' in rest or '—' in rest or '–' in rest:
                        parts = re.split('[-—–]', rest, maxsplit=1)
                        title = parts[0].strip()
                        desc = parts[1].strip() if len(parts) > 1 else ''
                    else:
                        # 无法拆分，视为标题，描述为空
                        title = rest
                        desc = ''

                if not title:
                    logger.warning(f"跳过无效章节（无标题）: {line}")
                    matched = True
                    break

                # 清理标题：如果包含"第X章:"前缀，移除它
                if re.match(r'^第\d+章[:：]', title):
                    title = re.sub(r'^第\d+章[:：]\s*', '', title).strip()

                chapters.append(Chapter(num=num, title=title, desc=desc))
                chapter_count += 1
                matched = True
                break

            if not matched:
                # 额外容错：尝试按 '标题 - 描述' 解析，自动计数
                if '-' in line or '—' in line:
                    parts = re.split('[-—–]', line, maxsplit=1)
                    title = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ''
                    chapter_count += 1
                    chapters.append(Chapter(num=chapter_count, title=title, desc=desc))
        
        if not chapters:
            return [], "无法从大纲中解析任何章节，请检查格式"
        
        # 按章节号排序
        chapters.sort(key=lambda x: x.num)
        
        # 检查章节号的连续性
        for i, chapter in enumerate(chapters, 1):
            if chapter.num != i:
                logger.warning(f"章节号不连续: 期望{i}，实际{chapter.num}")
                chapter.num = i
        
        logger.info(f"成功解析 {len(chapters)} 个章节")
        return chapters, f"解析成功，共 {len(chapters)} 章"
    
    @staticmethod
    def format_for_display(chapters: List[Chapter]) -> str:
        """将章节列表格式化为可编辑的大纲文本"""
        lines = []
        for ch in chapters:
            lines.append(f"第{ch.num}章: {ch.title} - {ch.desc}")
        return "\n".join(lines)


class NovelGenerator:
    """小说生成器"""
    
    def __init__(self):
        self.config = get_config()
        self.api_client = get_api_client()
    
    def generate_outline(
        self,
        title: str,
        genre: str,
        total_chapters: int,
        character_setting: str,
        world_setting: str,
        plot_idea: str
    ) -> Tuple[str, str]:
        """
        生成小说大纲
        
        Returns:
            (大纲文本, 错误信息或成功提示)
        """
        if not title or not title.strip():
            return "", "小说标题不能为空"
        if not character_setting or not character_setting.strip():
            return "", "人物设定不能为空"
        if not world_setting or not world_setting.strip():
            return "", "世界观设定不能为空"
        if not plot_idea or not plot_idea.strip():
            return "", "主线剧情不能为空"
        
        if total_chapters <= 0:
            total_chapters = 20
        
        style_desc = self._build_style_description()
        
        prompt = f"""请生成一篇{genre}小说的完整大纲，标题：《{title}》。

人物设定：{character_setting}

世界观：{world_setting}

主线剧情：{plot_idea}

风格要求：{style_desc}

要求：
1. 总章节数约 {total_chapters} 章
2. 每章格式严格：第X章: 章节标题 - 简要剧情描述（50-100字）
3. 情节连贯，有起承转合，人物发展合理
4. 只输出大纲列表，不要其他内容
5. 大纲要精彩、引人入胜、有悬念"""
        
        messages = [
            {"role": "system", "content": "你是专业的小说大纲策划师，擅长创作吸引人的故事框架。"},
            {"role": "user", "content": prompt}
        ]
        
        logger.info(f"开始生成大纲: {title}")
        success, content = self.api_client.generate(messages, use_cache=True)
        
        if not success:
            logger.error(f"大纲生成失败: {content}")
            return "", content
        
        logger.info("大纲生成成功")
        return content, "大纲生成成功"
    
    def generate_chapter(
        self,
        chapter_num: int,
        chapter_title: str,
        chapter_desc: str,
        novel_title: str,
        character_setting: str,
        world_setting: str,
        plot_idea: str,
        previous_content: str = ""
    ) -> Tuple[str, str]:
        """
        生成单个章节
        
        Returns:
            (章节内容, 错误信息或成功提示)
        """
        style_desc = self._build_style_description()
        target_words = self.config.generation.chapter_target_words
        
        # 构建连贯性提示
        continuity_prompt = ""
        if previous_content:
            # 截取最后500字作为上文参考
            continuity_prompt = f"""

【前文回顾】
{previous_content[-500:]}

【连贯性检查清单】
✓ 确保情节走向与前文保持一致
✓ 人物状态和位置与前文对应
✓ 已有的悬念在本章得到呼应或推进
✓ 人物对话风格保持一致
✓ 避免重复已有的信息或情节
✓ 新的悬念为后续章节铺路

请严格按照以上检查清单确保内容与前文连贯流畅。"""
        
        prompt = f"""请撰写小说《{novel_title}》的第{chapter_num}章。

章节标题：{chapter_title}
本章大纲：{chapter_desc}

整体设定：
人物：{character_setting}
世界观：{world_setting}
主线剧情：{plot_idea}

风格要求：{style_desc}

具体要求：
1. 正文约 {target_words} 字（中文字符）
2. 情节严格符合本章大纲，与全书连贯
3. 对话自然，心理描写细腻，环境描写生动
4. 结尾留下适当悬念或铺垫下一章
5. 只输出正文，不要章节标题、说明或其他内容{continuity_prompt}"""
        
        messages = [
            {"role": "system", "content": "你是优秀的长篇小说作家，创作深入人心的故事。"},
            {"role": "user", "content": prompt}
        ]
        
        logger.info(f"开始生成章节: {chapter_num} - {chapter_title}")
        success, content = self.api_client.generate(messages, use_cache=False)
        
        if not success:
            logger.error(f"章节生成失败: {content}")
            return "", content
        
        logger.info(f"章节生成成功: {chapter_num}")
        logger.info(f"章节内容长度: {len(content)} 字")
        return content, "生成成功"
    
    def rewrite_paragraph(
        self,
        text: str,
        style_template: str = ""
    ) -> Tuple[str, str]:
        """
        重写段落
        
        Returns:
            (重写后的文本, 错误信息或成功提示)
        """
        if not text or not text.strip():
            return "", "文本为空"
        
        if len(text) > 5000:
            return "", "文本过长（>5000字），请分段处理"
        
        style = style_template or PRESET_TEMPLATES["重写风格 - 默认"]
        
        prompt = f"""请按照以下风格重写原文，保留原意和情节，但加入更多细节：

风格要求：{style}

原文：
{text}

请只输出重写后的文本，不要其他内容。"""
        
        messages = [
            {"role": "system", "content": "你是优秀的小说编辑，擅长用生动细腻的笔触改进文本。"},
            {"role": "user", "content": prompt}
        ]
        
        logger.info("开始重写段落")
        success, content = self.api_client.generate(messages, use_cache=False)
        
        if not success:
            logger.error(f"重写失败: {content}")
            return "", content
        
        logger.info("重写完成")
        return content, "重写成功"
    
    def generate_summary(self, text: str, max_length: int = 200) -> Tuple[str, str]:
        """
        生成文本摘要
        
        Returns:
            (摘要, 错误信息或成功提示)
        """
        if not text or not text.strip():
            return "", "文本为空"
        
        prompt = f"""请为以下文本生成一个简洁的摘要，不超过{max_length}字。

文本：
{text}

摘要："""
        
        messages = [
            {"role": "system", "content": "你是专业的内容编辑，擅长提炼文本的核心内容。"},
            {"role": "user", "content": prompt}
        ]
        
        logger.info("开始生成摘要")
        success, content = self.api_client.generate(messages, use_cache=True)
        
        if not success:
            return "", content
        
        logger.info("摘要生成成功")
        return content.strip(), "成功"
    
    def _build_style_description(self) -> str:
        """构建风格描述"""
        gen = self.config.generation
        return f"""写作风格：{gen.writing_style}
语调：{gen.writing_tone}
人物塑造：{gen.character_development}
情节复杂度：{gen.plot_complexity}"""


def get_generator() -> NovelGenerator:
    """获取小说生成器实例"""
    global _GENERATOR
    try:
        _GENERATOR
    except NameError:
        _GENERATOR = NovelGenerator()
    return _GENERATOR
