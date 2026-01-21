"""
小说生成模块 - 支持大纲生成、章节生成、重写等

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import re
import logging
import json
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from api_client import get_api_client
from config import get_config

logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path("cache/generation")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 章节摘要缓存目录
SUMMARY_CACHE_DIR = Path("cache/summaries")
SUMMARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 预设模板 - 丰富的风格选择
PRESET_TEMPLATES = {
    "重写风格 - 默认": "用更生动、细腻的笔触重写，语言优美，保留原意和情节，但加入更多细节描写和人物内心活动。",
    "重写风格 - 玄幻仙侠": "以古典仙侠风格重写，语言古风优雅，增加仙术法宝描写、灵气意境、人物心境修炼与道心感悟，保留原情节。",
    "重写风格 - 都市言情": "现代都市言情风格重写，语言轻松甜宠或虐心，增加浪漫互动、细腻心理描写、日常生活细节，人物情感更丰富。",
    "重写风格 - 悬疑惊悚": "悬疑惊悚风格重写，语言营造紧张氛围，增加心理惊悚描写、线索铺垫、环境渲染与反转元素。",
    "重写风格 - 科幻硬核": "硬科幻风格重写，语言严谨专业，增加科学原理解释、技术细节、世界观构建，逻辑自洽。",
    "重写风格 - 武侠江湖": "金庸古龙式武侠风格重写，语言潇洒豪气，增加武功招式描写、江湖恩怨、侠义精神。",
    "重写风格 - 古代宫斗": "古代宫廷风格重写，语言典雅华丽，增加宫廷礼仪、权谋算计、勾心斗角，人物关系复杂微妙。",
    "重写风格 - 现代军事": "现代军事风格重写，语言硬朗刚毅，增加战术描写、武器装备、军营生活，突出军人的血性与担当。",
    "重写风格 - 历史演义": "历史演义风格重写，语言古朴庄重，增加历史背景、时代氛围、人物传记感，宏大的历史视角。",
    "重写风格 - 灵异玄幻": "灵异玄幻风格重写，语言神秘诡异，增加超自然元素、灵异现象、阴阳五行，营造玄幻氛围。",
    "重写风格 - 青春校园": "青春校园风格重写，语言清新活泼，增加校园生活细节、青春悸动、成长感悟，纯真美好。",
    "重写风格 - 职场商战": "职场商战风格重写，语言干练务实，增加商业策略、职场博弈、心理博弈，突出商业智慧。",
    "重写风格 - 赛博朋克": "赛博朋克风格重写，语言科技感十足，增加高科技元素、虚拟现实、人工智能，反乌托邦色彩。",
    "重写风格 - 西幻魔法": "西方奇幻风格重写，语言史诗感强，增加魔法体系、种族设定、神话元素，中世纪氛围。",
    "重写风格 - 恐怖悬疑": "恐怖悬疑风格重写，语言阴森压抑，增加恐怖氛围、心理暗示、超自然现象，让人毛骨悚然。",
    "重写风格 - 幽默搞笑": "幽默搞笑风格重写，语言诙谐机智，增加搞笑元素、夸张描写、喜剧效果，轻松有趣。",
    "重写风格 - 文艺清新": "文艺清新风格重写，语言优美清新，增加情感细腻、意境深远、文字诗意，如诗如画。",
    "重写风格 - 热血冒险": "热血冒险风格重写，语言激昂澎湃，增加冒险元素、战斗场景、友情羁绊，充满正能量。",
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
        previous_content: str = "",
        context_summary: str = ""
    ) -> Tuple[str, str]:
        """
        生成单个章节

        Args:
            chapter_num: 章节号
            chapter_title: 章节标题
            chapter_desc: 章节描述
            novel_title: 小说标题
            character_setting: 人物设定
            world_setting: 世界观设定
            plot_idea: 主线剧情
            previous_content: 前文内容（用于连贯性）
            context_summary: 上下文摘要（用于上下文增强）

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

        # 添加上下文摘要（如果提供）
        context_prompt = ""
        if context_summary:
            context_prompt = f"""

{context_summary}

请根据以上摘要了解前文的主要情节，确保本章与前文连贯。"""

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
5. 只输出正文，不要章节标题、说明或其他内容{continuity_prompt}{context_prompt}"""

        messages = [
            {"role": "system", "content": "你是优秀的长篇小说作家，创作深入人心的故事。"},
            {"role": "user", "content": prompt}
        ]

        logger.info(f"开始生成章节: {chapter_num} - {chapter_title}")
        if context_summary:
            logger.info(f"使用上下文增强，上下文长度: {len(context_summary)} 字")
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
        重写段落（带重试机制）

        Returns:
            (重写后的文本, 错误信息或成功提示)
        """
        if not text or not text.strip():
            return "", "文本为空"

        if len(text) > 20000:
            return "", "文本过长（>20000字），请分段处理"

        style = style_template or PRESET_TEMPLATES["重写风格 - 默认"]

        prompt = f"""请按照以下风格重写原文，保留原意和情节，但加入更多细节：

风格要求：{style}

原文：
{text}

【重要要求】
1. 必须输出完整的重写后的小说内容，字数应该与原文相当
2. 绝对不能只输出"重写成功"、"润色成功"、"生成成功"等状态消息
3. 必须输出实际的重写文本，包含丰富的细节描写和情节展开
4. 如果原文有1000字，重写后也应该有1000字左右
5. 不要输出任何说明性文字或状态确认消息

请严格按照以上要求输出完整的重写内容。"""

        messages = [
            {"role": "system", "content": "你是优秀的小说编辑，擅长用生动细腻的笔触改进文本。"},
            {"role": "user", "content": prompt}
        ]

        logger.info(f"开始重写段落，原文长度: {len(text)}字，风格: {style[:50]}")

        # 重试机制：当内容过短时重试
        max_retries = 3
        content = ""
        success_msg = ""

        for attempt in range(max_retries):
            logger.debug(f"重写尝试 {attempt + 1}/{max_retries}")
            success, content = self.api_client.generate(messages, use_cache=False)

            if not success:
                logger.error(f"重写失败（尝试 {attempt + 1}/{max_retries}）: {content}")
                if attempt < max_retries - 1:
                    continue
                return "", content

            # 严格的内容验证
            if not content or not content.strip():
                logger.error(f"重写返回空内容（尝试 {attempt + 1}/{max_retries}）")
                if attempt < max_retries - 1:
                    continue
                return "", "API返回空内容，请检查API配置"

            # 过滤状态消息（扩展列表）
            status_messages = [
                "续写成功", "重写成功", "润色成功", "生成成功", "完成", "done", "success",
                "OK", "ok", "Success", "SUCCESS", "成功", "完成",
                "已生成", "已重写", "已润色", "已续写",
                "生成成功", "重写完成", "润色完成", "续写完成"
            ]
            content_stripped = content.strip()
            if content_stripped in status_messages:
                logger.error(f"API返回了状态消息而非实际内容: {content}（尝试 {attempt + 1}/{max_retries}）")
                logger.error(f"内容长度: {len(content)}字，内容: {content}")
                if attempt < max_retries - 1:
                    continue
                return "", "API返回了状态消息，请检查API配置"

            # 检查内容长度（更严格）
            if len(content_stripped) < 50:
                logger.warning(f"重写内容过短: {len(content)}字（尝试 {attempt + 1}/{max_retries}）")
                logger.warning(f"内容: {content}")
                if attempt < max_retries - 1:
                    continue
                return "", f"重写内容过短（{len(content)}字），可能是API问题"

            # 内容验证通过
            logger.info(f"重写完成，内容长度: {len(content)}字，尝试次数: {attempt + 1}")
            logger.debug(f"内容前200字: {content[:200]}")
            return content, "重写成功"

        # 所有重试都失败
        logger.error(f"重写在{max_retries}次尝试后仍然失败")
        return "", f"重写失败：在{max_retries}次尝试后仍然失败"
    
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
    
    def polish_text(
        self,
        text: str,
        polish_type: str = "general",
        custom_requirements: str = ""
    ) -> Tuple[str, str]:
        """
        润色文本（带重试机制）

        Args:
            text: 待润色文本
            polish_type: 润色类型
            custom_requirements: 自定义要求

        Returns:
            (润色后的文本, 错误信息或成功提示)
        """
        if not text or not text.strip():
            return "", "文本为空"

        if len(text) > 10000:
            return "", "文本过长（>10000字），请分段处理"

        # 润色类型对应的提示词
        polish_prompts = {
            "general": "请对以下文本进行全面的润色优化，提升文笔质量，使语言更流畅、更生动、更有感染力。",
            "find_errors": "请仔细检查以下文本，找出其中的错误（包括错别字、语法错误、逻辑错误、用词不当等），并提出修改建议。",
            "suggest_improvements": "请阅读以下文本，提出具体的改进建议，包括情节、人物、对话、描写等方面的优化方向。",
            "direct_modify": "请直接修改并优化以下文本，提升文笔质量，使其更加专业和完善。",
            "remove_ai_flavor": "请去除以下文本中的AI生成痕迹，使其更加自然、更像人工创作，增加人味和情感深度。",
            "enhance_details": "请对以下文本进行细节增强，增加环境描写、心理描写、感官描写等，使内容更加丰富立体。",
            "optimize_dialogue": "请优化以下文本中的对话部分，使对话更自然、更符合人物性格、更有个性。",
            "improve_pacing": "请调整以下文本的节奏，优化情节推进速度，使故事更加引人入胜。",
        }

        prompt = polish_prompts.get(polish_type, polish_prompts["general"])

        if custom_requirements:
            prompt += f"\n\n额外要求：{custom_requirements}"

        prompt += f"""

原文：
{text}

请只输出润色后的文本或建议，不要其他内容。"""

        messages = [
            {"role": "system", "content": "你是专业的文学编辑和润色专家，擅长提升文本质量和文笔水平。"},
            {"role": "user", "content": prompt}
        ]

        logger.info(f"开始润色文本，类型: {polish_type}，原文长度: {len(text)}字")

        # 重试机制：当内容过短时重试
        max_retries = 3
        content = ""
        success_msg = ""

        for attempt in range(max_retries):
            logger.debug(f"润色尝试 {attempt + 1}/{max_retries}")
            success, content = self.api_client.generate(messages, use_cache=False)

            if not success:
                logger.error(f"润色失败（尝试 {attempt + 1}/{max_retries}）: {content}")
                if attempt < max_retries - 1:
                    continue
                return "", content

            # 严格的内容验证
            if not content or not content.strip():
                logger.error(f"润色返回空内容（尝试 {attempt + 1}/{max_retries}）")
                if attempt < max_retries - 1:
                    continue
                return "", "API返回空内容，请检查API配置"

            # 过滤状态消息（扩展列表）
            status_messages = [
                "续写成功", "重写成功", "润色成功", "生成成功", "完成", "done", "success",
                "OK", "ok", "Success", "SUCCESS", "成功", "完成",
                "已生成", "已重写", "已润色", "已续写",
                "生成成功", "重写完成", "润色完成", "续写完成"
            ]
            content_stripped = content.strip()
            if content_stripped in status_messages:
                logger.error(f"API返回了状态消息而非实际内容: {content}（尝试 {attempt + 1}/{max_retries}）")
                logger.error(f"内容长度: {len(content)}字，内容: {content}")
                if attempt < max_retries - 1:
                    continue
                return "", "API返回了状态消息，请检查API配置"

            # 检查内容长度（更严格）
            if len(content_stripped) < 50:
                logger.warning(f"润色内容过短: {len(content)}字（尝试 {attempt + 1}/{max_retries}）")
                logger.warning(f"内容: {content}")
                if attempt < max_retries - 1:
                    continue
                return "", f"润色内容过短（{len(content)}字），可能是API问题"

            # 内容验证通过
            logger.info(f"润色完成，内容长度: {len(content)}字，尝试次数: {attempt + 1}")
            logger.debug(f"内容前200字: {content[:200]}")
            return content, "润色成功"

        # 所有重试都失败
        logger.error(f"润色在{max_retries}次尝试后仍然失败")
        return "", f"润色失败：在{max_retries}次尝试后仍然失败"

    def polish_and_suggest(
        self,
        text: str,
        custom_requirements: str = ""
    ) -> Tuple[str, str, str]:
        """
        润色文本并提供建议

        Returns:
            (润色后的文本, 修改建议, 错误信息或成功提示)
        """
        if not text or not text.strip():
            return "", "", "文本为空"

        if len(text) > 10000:
            return "", "", "文本过长（>10000字），请分段处理"

        prompt = f"""请对以下文本进行全面分析和优化：

1. **找出错误**：检查错别字、语法错误、逻辑错误、用词不当等
2. **提出建议**：给出具体的改进建议，包括情节、人物、对话、描写等
3. **直接修改**：提供润色后的优化版本

原文：
{text}

{f"额外要求：{custom_requirements}" if custom_requirements else ""}

请按以下格式输出：
---
【发现的错误】
（列出发现的错误）

【改进建议】
（列出改进建议）

【润色后的文本】
（直接修改后的文本）
---"""

        messages = [
            {"role": "system", "content": "你是专业的文学编辑，擅长文本分析、错误查找和润色优化。"},
            {"role": "user", "content": prompt}
        ]

        logger.info("开始润色并提供建议")
        success, content = self.api_client.generate(messages, use_cache=False)

        if not success:
            logger.error(f"润色失败: {content}")
            return "", "", content

        # 添加内容验证
        if len(content) < 10:
            logger.warning(f"润色内容过短: {len(content)}字,内容: {content}")
            logger.warning(f"可能API返回了状态消息而非实际内容")

        # 解析返回的内容
        import re
        errors = ""
        suggestions = ""
        polished = ""

        # 尝试解析结构化输出
        if "【发现的错误】" in content:
            parts = content.split("【")
            for part in parts:
                if part.startswith("发现的错误】"):
                    errors = part.replace("发现的错误】", "").strip()
                elif part.startswith("改进建议】"):
                    suggestions = part.replace("改进建议】", "").strip()
                elif part.startswith("润色后的文本】"):
                    polished = part.replace("润色后的文本】", "").strip()
        else:
            # 如果没有按格式输出，将整个内容作为润色结果
            polished = content.strip()
            suggestions = "AI未按格式输出，请查看润色结果"

        logger.info(f"润色完成,润色内容长度: {len(polished)}字")
        return polished, suggestions, "润色成功"

    def continue_writing(
        self,
        existing_text: str,
        novel_title: str,
        character_setting: str,
        world_setting: str,
        plot_idea: str,
        target_words: int = 2500,
        continue_count: int = 1
    ) -> Tuple[str, str]:
        """
        续写小说内容（带重试机制）

        Args:
            existing_text: 已有的小说文本
            novel_title: 小说标题
            character_setting: 人物设定
            world_setting: 世界观设定
            plot_idea: 剧情设定
            target_words: 目标字数
            continue_count: 续写章节数

        Returns:
            (续写内容, 错误信息或成功提示)
        """
        if not existing_text or not existing_text.strip():
            return "", "已有文本为空"

        style_desc = self._build_style_description()

        # 获取已有文本的末尾部分作为上下文
        previous_content = existing_text[-1500:] if len(existing_text) > 1500 else existing_text

        prompt = f"""请续写小说《{novel_title}》的下一章内容。

【已有设定】
人物设定：{character_setting}
世界观：{world_setting}
主线剧情：{plot_idea}

【风格要求】
{style_desc}

【前文回顾】（最近1500字）
{previous_content}

【续写要求】
1. 根据前文内容自然续写下一章
2. 保持与前文的连贯性，包括人物性格、情节发展、对话风格等
3. 字数约 {target_words} 字
4. 不要重复前文已有的内容
5. 结尾留下适当的悬念或铺垫
6. 只输出续写的正文，不要章节标题、说明或其他内容"""

        messages = [
            {"role": "system", "content": "你是优秀的长篇小说作家，擅长创作引人入胜的故事和自然的情节衔接。"},
            {"role": "user", "content": prompt}
        ]

        logger.info(f"开始续写小说: {novel_title}，已有文本长度: {len(existing_text)}字，目标字数: {target_words}")

        # 重试机制：当内容过短时重试
        max_retries = 3
        content = ""
        success_msg = ""

        for attempt in range(max_retries):
            logger.debug(f"续写尝试 {attempt + 1}/{max_retries}")
            success, content = self.api_client.generate(messages, use_cache=False)

            if not success:
                logger.error(f"续写失败（尝试 {attempt + 1}/{max_retries}）: {content}")
                if attempt < max_retries - 1:
                    continue
                return "", content

            # 严格的内容验证
            if not content or not content.strip():
                logger.error(f"续写返回空内容（尝试 {attempt + 1}/{max_retries}）")
                if attempt < max_retries - 1:
                    continue
                return "", "API返回空内容，请检查API配置"

            # 过滤状态消息（扩展列表）
            status_messages = [
                "续写成功", "重写成功", "润色成功", "生成成功", "完成", "done", "success",
                "OK", "ok", "Success", "SUCCESS", "成功", "完成",
                "已生成", "已重写", "已润色", "已续写",
                "生成成功", "重写完成", "润色完成", "续写完成"
            ]
            content_stripped = content.strip()
            if content_stripped in status_messages:
                logger.error(f"API返回了状态消息而非实际内容: {content}（尝试 {attempt + 1}/{max_retries}）")
                logger.error(f"内容长度: {len(content)}字，内容: {content}")
                if attempt < max_retries - 1:
                    continue
                return "", "API返回了状态消息，请检查API配置"

            # 检查内容长度（更严格）
            if len(content_stripped) < 100:
                logger.warning(f"续写内容过短: {len(content)}字（尝试 {attempt + 1}/{max_retries}）")
                logger.warning(f"内容: {content}")
                if attempt < max_retries - 1:
                    continue
                return "", f"续写内容过短（{len(content)}字），可能是API问题"

            # 内容验证通过
            logger.info(f"续写成功，字数: {len(content)}，尝试次数: {attempt + 1}")
            logger.debug(f"内容前200字: {content[:200]}")
            return content, "续写成功"

        # 所有重试都失败
        logger.error(f"续写在{max_retries}次尝试后仍然失败")
        return "", f"续写失败：在{max_retries}次尝试后仍然失败"

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


# ==================== 缓存管理 ====================

def save_generation_cache(project_id: str, cache_data: Dict) -> Tuple[bool, str]:
    """
    保存生成缓存

    Args:
        project_id: 项目ID
        cache_data: 缓存数据字典

    Returns:
        (是否成功, 消息)
    """
    if not project_id or not project_id.strip():
        return False, "项目ID不能为空"

    if not cache_data:
        return False, "缓存数据不能为空"

    cache_file = CACHE_DIR / f"{project_id}.json"

    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        logger.info(f"缓存已保存: {cache_file}")
        return True, "缓存保存成功"
    except Exception as e:
        logger.error(f"保存缓存失败: {e}")
        return False, f"保存缓存失败: {str(e)}"


def load_generation_cache(project_id: str) -> Tuple[Optional[Dict], str]:
    """
    加载生成缓存

    Args:
        project_id: 项目ID

    Returns:
        (缓存数据, 消息)
    """
    if not project_id or not project_id.strip():
        return None, "项目ID不能为空"

    cache_file = CACHE_DIR / f"{project_id}.json"

    if not cache_file.exists():
        return None, "缓存不存在"

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        logger.info(f"缓存已加载: {cache_file}")
        return cache_data, "缓存加载成功"
    except Exception as e:
        logger.error(f"加载缓存失败: {e}")
        return None, f"加载缓存失败: {str(e)}"


def clear_generation_cache(project_id: str) -> Tuple[bool, str]:
    """
    清理生成缓存

    Args:
        project_id: 项目ID

    Returns:
        (是否成功, 消息)
    """
    if not project_id or not project_id.strip():
        return False, "项目ID不能为空"

    cache_file = CACHE_DIR / f"{project_id}.json"

    if not cache_file.exists():
        return False, "缓存不存在"

    try:
        cache_file.unlink()
        logger.info(f"缓存已清理: {cache_file}")
        return True, "缓存清理成功"
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        return False, f"清理缓存失败: {str(e)}"


def list_generation_caches() -> List[Dict]:
    """
    列出所有生成缓存

    Returns:
        缓存信息列表
    """
    caches = []
    if not CACHE_DIR.exists():
        return caches

    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            caches.append({
                "project_id": cache_file.stem,
                "title": cache_data.get("title", "未知"),
                "current_chapter": cache_data.get("current_chapter", 0),
                "total_chapters": cache_data.get("total_chapters", 0),
                "status": cache_data.get("generation_status", "unknown"),
                "timestamp": cache_data.get("timestamp", ""),
                "size": cache_file.stat().st_size
            })
        except Exception as e:
            logger.error(f"读取缓存失败 {cache_file}: {e}")

    return caches


def get_cache_size() -> int:
    """
    获取缓存总大小（字节）

    Returns:
        缓存总大小
    """
    total_size = 0
    if CACHE_DIR.exists():
        for cache_file in CACHE_DIR.glob("*.json"):
            total_size += cache_file.stat().st_size
    return total_size


# ==================== 章节摘要管理 ====================

def generate_chapter_summary(chapter_content: str, chapter_title: str) -> Tuple[str, str]:
    """
    生成章节摘要

    Args:
        chapter_content: 章节内容
        chapter_title: 章节标题

    Returns:
        (摘要内容, 错误信息或成功提示)
    """
    if not chapter_content or not chapter_content.strip():
        return "", "章节内容为空"

    generator = get_generator()

    prompt = f"""请为以下章节生成一个简洁的摘要（100-200字）。

章节标题：{chapter_title}

章节内容：
{chapter_content[:3000]}

要求：
1. 保留关键情节和人物信息
2. 突出章节的核心冲突和转折
3. 语言简洁明了
4. 只输出摘要内容，不要其他说明"""

    messages = [
        {"role": "system", "content": "你是专业的内容编辑，擅长提炼章节的核心情节和关键信息。"},
        {"role": "user", "content": prompt}
    ]

    logger.info(f"开始生成章节摘要: {chapter_title}")
    success, content = generator.api_client.generate(messages, use_cache=False)

    if not success:
        logger.error(f"章节摘要生成失败: {content}")
        return "", content

    logger.info(f"章节摘要生成成功: {len(content)} 字")
    return content.strip(), "摘要生成成功"


def save_chapter_summary(project_id: str, chapter_num: int, summary: str) -> Tuple[bool, str]:
    """
    保存章节摘要到缓存

    Args:
        project_id: 项目ID
        chapter_num: 章节号
        summary: 摘要内容

    Returns:
        (是否成功, 消息)
    """
    if not project_id or not project_id.strip():
        return False, "项目ID不能为空"

    if not summary or not summary.strip():
        return False, "摘要内容不能为空"

    # 创建项目目录
    project_dir = SUMMARY_CACHE_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # 保存摘要
    summary_file = project_dir / f"{chapter_num}.json"
    summary_data = {
        "chapter_num": chapter_num,
        "summary": summary,
        "generated_at": datetime.now().isoformat()
    }

    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        logger.info(f"章节摘要已保存: {summary_file}")
        return True, "摘要保存成功"
    except Exception as e:
        logger.error(f"保存章节摘要失败: {e}")
        return False, f"保存摘要失败: {str(e)}"


def load_chapter_summaries(project_id: str) -> Tuple[List[Dict], str]:
    """
    加载所有章节摘要

    Args:
        project_id: 项目ID

    Returns:
        (摘要列表, 消息)
    """
    if not project_id or not project_id.strip():
        return [], "项目ID不能为空"

    project_dir = SUMMARY_CACHE_DIR / project_id

    if not project_dir.exists():
        return [], "摘要目录不存在"

    summaries = []
    try:
        # 按章节号排序加载
        summary_files = sorted(project_dir.glob("*.json"), key=lambda x: int(x.stem))

        for summary_file in summary_files:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
                summaries.append(summary_data)

        logger.info(f"加载了 {len(summaries)} 个章节摘要")
        return summaries, f"加载了 {len(summaries)} 个章节摘要"
    except Exception as e:
        logger.error(f"加载章节摘要失败: {e}")
        return [], f"加载摘要失败: {str(e)}"


def build_context_from_summaries(summaries: List[Dict], max_context_length: int = 1000) -> str:
    """
    从摘要构建上下文

    Args:
        summaries: 摘要列表
        max_context_length: 最大上下文长度（字符数）

    Returns:
        上下文字符串
    """
    if not summaries:
        return ""

    # 按时间倒序排列（最新的在前）
    sorted_summaries = sorted(summaries, key=lambda x: x.get('chapter_num', 0), reverse=True)

    # 构建上下文
    context_parts = []
    current_length = 0

    for summary_data in sorted_summaries:
        chapter_num = summary_data.get('chapter_num', 0)
        summary = summary_data.get('summary', '')

        if not summary:
            continue

        # 检查是否超出长度限制
        part = f"第{chapter_num}章：{summary}\n"
        if current_length + len(part) > max_context_length:
            break

        context_parts.append(part)
        current_length += len(part)

    # 按章节正序排列（最早的在前）
    context_parts.reverse()

    if context_parts:
        context = "【前文摘要】\n" + "\n".join(context_parts)
        logger.info(f"构建上下文成功，包含 {len(context_parts)} 个章节摘要，总长度 {len(context)} 字")
        return context
    else:
        logger.warning("没有可用的摘要构建上下文")
        return ""


def clear_chapter_summaries(project_id: str) -> Tuple[bool, str]:
    """
    清理项目的章节摘要

    Args:
        project_id: 项目ID

    Returns:
        (是否成功, 消息)
    """
    if not project_id or not project_id.strip():
        return False, "项目ID不能为空"

    project_dir = SUMMARY_CACHE_DIR / project_id

    if not project_dir.exists():
        return False, "摘要目录不存在"

    try:
        import shutil
        shutil.rmtree(project_dir)
        logger.info(f"章节摘要已清理: {project_dir}")
        return True, "摘要清理成功"
    except Exception as e:
        logger.error(f"清理章节摘要失败: {e}")
        return False, f"清理摘要失败: {str(e)}"


def list_summary_caches() -> List[Dict]:
    """
    列出所有摘要缓存

    Returns:
        缓存信息列表
    """
    caches = []
    if not SUMMARY_CACHE_DIR.exists():
        return caches

    for project_dir in SUMMARY_CACHE_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        try:
            summary_files = list(project_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in summary_files)

            caches.append({
                "project_id": project_dir.name,
                "chapter_count": len(summary_files),
                "total_size": total_size,
                "size_kb": round(total_size / 1024, 2)
            })
        except Exception as e:
            logger.error(f"读取摘要缓存失败 {project_dir}: {e}")

    return caches


def get_summary_cache_size() -> int:
    """
    获取摘要缓存总大小（字节）

    Returns:
        缓存总大小
    """
    total_size = 0
    if SUMMARY_CACHE_DIR.exists():
        for summary_file in SUMMARY_CACHE_DIR.rglob("*.json"):
            total_size += summary_file.stat().st_size
    return total_size
