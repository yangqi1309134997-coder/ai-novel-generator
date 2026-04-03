"""
完整小说自动生成功能
支持缓存机制、上下文机制、连贯性系统

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""

import logging
import os
import re
from typing import Any, List, Tuple, Optional, Dict
from pathlib import Path
from datetime import datetime
import json

from src.core.coherence.hierarchical_summary import HierarchicalSummaryManager
from src.core.prompts.scene_planner import ScenePlanner
from src.core.style_optimizer import StyleOptimizer, detect_and_optimize, get_style_score
from src.core.quality_assessor import QualityAssessor, assess_chapter_quality
from src.core.unified_assessor import UnifiedAssessor, AITasteLevel, create_assessment_prompt

logger = logging.getLogger(__name__)


class AutoNovelGenerator:
    """
    自动小说生成器

    功能：
    1. 根据设定生成大纲
    2. 逐章生成内容
    3. 使用缓存机制支持暂停/恢复
    4. 使用上下文机制保持连贯性
    5. 使用连贯性系统跟踪角色、剧情、世界观
    """

    def __init__(
        self,
        api_client,
        prompt_manager,
        coherence_system,
        project_dir: Path,
        cache_dir: Optional[Path] = None,
        outline_max_tokens: int = 8000  # 大纲生成的max_tokens（实际来自全局max_tokens配置）
    ):
        """
        初始化生成器

        Args:
            api_client: API客户端
            prompt_manager: 提示词管理器
            coherence_system: 连贯性系统 (character_tracker, plot_manager, world_db)
            project_dir: 项目目录
            cache_dir: 缓存目录
            outline_max_tokens: 大纲生成的最大token数（来自全局Max Tokens配置，默认8000）
        """
        self.api_client = api_client
        self.prompt_manager = prompt_manager
        self.character_tracker = coherence_system.get("character_tracker")
        self.plot_manager = coherence_system.get("plot_manager")
        self.world_db = coherence_system.get("world_db")
        self.project_dir = project_dir
        self.cache_dir = cache_dir or Path("cache/generation")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.outline_max_tokens = outline_max_tokens # 保存配置

        # 分层摘要管理器（延迟初始化，需要project_id）
        self._summary_manager: Optional[HierarchicalSummaryManager] = None

        # 统一评估系统（整合AI去味和质量评估）
        self.unified_assessor = UnifiedAssessor(api_client)

        # 保留旧的系统以兼容
        self.style_optimizer = StyleOptimizer(api_client)
        self.quality_assessor = QualityAssessor(api_client)

        # 优化配置
        self.optimization_config = {
            "enable_style_optimization": True,  # 启用风格优化
            "enable_quality_assessment": True,  # 启用质量评估
            "style_optimization_mode": "auto",  # auto/ai_off/ai_on
            "min_quality_score": 75.0,  # 最低质量分数
            # 新增：统一评估配置
            "ai_taste_level": "strong",  # disabled/basic/strong
            "quality_min_score": 75.0,  # 最低质量分
            "quality_rewrite_threshold": 68.0,  # 质量重写阈值
            "enable_auto_rewrite": True,  # 是否自动重写
            "max_rewrite_attempts": 3,  # 最大重写次数
        }

        # 生成状态
        self.is_generating = False
        self.should_stop = False
        self.should_pause = False
        self.current_project_id = None
        self.current_chapter = 0
        self.total_chapters = 0
        self.token_adjustment_factor = 1.0
        self.context_chapter_limit = 50
        self.adjustment_history = []
        self._apply_runtime_flags()

    @staticmethod
    def _runtime_flag(name: str) -> bool:
        return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _runtime_int(name: str) -> Optional[int]:
        raw = os.getenv(name, "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            logger.warning("Invalid integer override for %s: %s", name, raw)
            return None

    def _apply_runtime_flags(self) -> None:
        """Allow stress-test overrides without changing the normal product path."""
        if self._runtime_flag("NOVEL_DISABLE_CHAPTER_ASSESSMENT"):
            self.optimization_config["enable_quality_assessment"] = False
            self.optimization_config["enable_auto_rewrite"] = False
            self.optimization_config["enable_style_optimization"] = False
            self.optimization_config["ai_taste_level"] = "disabled"
            logger.info("[stress] chapter assessment pipeline disabled by env")

        if self._runtime_flag("NOVEL_DISABLE_AUTO_REWRITE"):
            self.optimization_config["enable_auto_rewrite"] = False
            logger.info("[stress] auto rewrite disabled by env")

        target_words_override = self._runtime_int("NOVEL_TARGET_WORDS_OVERRIDE")
        if target_words_override and target_words_override > 0:
            logger.info("[stress] target words override enabled: %s", target_words_override)

    def pause_generation(self) -> None:
        """暂停生成（可继续）"""
        self.should_pause = True
        self.should_stop = True
        logger.info("[自动生成] 已发送暂停信号（可继续）")

    def resume_generation(self) -> None:
        """继续生成"""
        self.should_pause = False
        self.should_stop = False
        logger.info("[自动生成] 已发送继续信号")

    def stop_generation(self) -> None:
        """停止生成（不可继续）"""
        self.should_stop = True
        self.should_pause = False  # 停止时取消暂停状态
        logger.info("[自动生成] 已发送停止信号（不可继续）")

        # 动态token调整系统
        self.token_adjustment_factor = 1.0  # token调整系数，初始为1.0
        self.context_chapter_limit = 50     # 上下文章节限制，初始为50
        self.adjustment_history = []        # 调整历史，用于平滑调整

    def generate_outline(
        self,
        title: str,
        genre: str,
        character_setting: str,
        world_setting: str,
        plot_idea: str,
        chapter_count: int
    ) -> Tuple[bool, str, List[Dict]]:
        """
        生成小说大纲（支持分批生成，适用于大规模章节）

        Args:
            title: 小说标题
            genre: 类型
            character_setting: 角色设定
            world_setting: 世界观设定
            plot_idea: 剧情构思
            chapter_count: 章节数

        Returns:
            (success, message, outline_list)
        """
        try:
            logger.info(f"[自动生成] 开始生成大纲: {title} ({genre}, {chapter_count}章)")

            # 限制输入长度，避免超出模型限制
            max_char_setting = 500
            char_setting_short = character_setting[:max_char_setting] if len(character_setting) > max_char_setting else character_setting
            world_setting_short = world_setting[:max_char_setting] if len(world_setting) > max_char_setting else world_setting
            plot_idea_short = plot_idea[:max_char_setting] if len(plot_idea) > max_char_setting else plot_idea

            # 判断是否需要分批生成
            batch_size = 10  # 每批生成10章
            all_chapters = []

            if chapter_count <= batch_size:
                # 小规模：一次性生成
                logger.info(f"[自动生成] 章节数较少({chapter_count}章)，一次性生成")
                success, message, chapters = self._generate_single_batch(
                    title, genre, char_setting_short, world_setting_short,
                    plot_idea_short, chapter_count, 1, []
                )
                if not success:
                    return False, message, []
                all_chapters = chapters
            else:
                # 大规模：分批生成
                logger.info(f"[自动生成] 章节数较多({chapter_count}章)，采用分批生成策略（每批{batch_size}章）")
                total_batches = (chapter_count + batch_size - 1) // batch_size

                for batch_num in range(total_batches):
                    start_chapter = batch_num * batch_size + 1
                    end_chapter = min((batch_num + 1) * batch_size, chapter_count)
                    current_batch_size = end_chapter - start_chapter + 1

                    logger.info(f"[自动生成] 生成第{batch_num + 1}/{total_batches}批: 第{start_chapter}-{end_chapter}章（共{current_batch_size}章）")

                    # 容错机制：失败时逐步减少章节数重试，直到成功
                    fallback_sizes = [current_batch_size]
                    if current_batch_size >= 10:
                        fallback_sizes = [10, 5, 3, 2, 1]
                    elif current_batch_size >= 5:
                        fallback_sizes = [5, 3, 2, 1]
                    elif current_batch_size >= 3:
                        fallback_sizes = [3, 2, 1]
                    else:
                        fallback_sizes = [current_batch_size]

                    success = False
                    message = ""
                    chapters = []
                    for try_size in fallback_sizes:
                        logger.info(f"[自动生成] 尝试生成{try_size}章（第{start_chapter}-{start_chapter + try_size - 1}章）")
                        success, message, chapters = self._generate_single_batch(
                            title, genre, char_setting_short, world_setting_short,
                            plot_idea_short, try_size, start_chapter, all_chapters
                        )
                        if success:
                            logger.info(f"[自动生成] 第{batch_num + 1}批成功（{try_size}章），已累计生成{len(all_chapters) + len(chapters)}章")
                            break
                        else:
                            logger.warning(f"[自动生成] 生成{try_size}章失败: {message}，尝试减少章节数")

                    # 确保本批成功，否则终止
                    if not success:
                        return False, f"第{batch_num + 1}批最终失败: {message}", all_chapters

                    all_chapters.extend(chapters)
                    logger.info(f"[自动生成] 第{batch_num + 1}批生成成功，已累计生成{len(all_chapters)}章")

            logger.info(f"[自动生成] 大纲生成完成，共{len(all_chapters)}章")
            return True, f"大纲生成成功，共{len(all_chapters)}章", all_chapters

        except Exception as e:
            logger.error(f"[自动生成] 生成大纲失败: {e}", exc_info=True)
            return False, f"生成大纲失败: {str(e)}", []

    def _generate_single_batch(
        self,
        title: str,
        genre: str,
        character_setting: str,
        world_setting: str,
        plot_idea: str,
        chapter_count: int,
        start_chapter_num: int,
        previous_chapters: List[Dict],
        max_retries: int = 5  # 增加重试次数
    ) -> Tuple[bool, str, List[Dict]]:
        """
        生成单批章节大纲（支持自动重试）

        Args:
            title: 小说标题
            genre: 类型
            character_setting: 角色设定
            world_setting: 世界观设定
            plot_idea: 剧情构思
            chapter_count: 本批章节数
            start_chapter_num: 起始章节号
            previous_chapters: 之前生成的章节列表（作为上下文）
            max_retries: 最大重试次数（默认3次）

        Returns:
            (success, message, chapters)
        """
        last_error = ""
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"[自动重试] 第{attempt + 1}次尝试生成第{start_chapter_num}-{start_chapter_num + chapter_count - 1}章...")
                
                # 构建上下文信息（所有已生成的章节）
                context_info = ""
                if previous_chapters:
                    context_info = f"\n\n前面已生成的章节（共{len(previous_chapters)}章，请基于这些章节继续往下生成）：\n"
                    for ch in previous_chapters:
                        context_info += f"第{ch['num']}章：{ch['title']} - {ch['description']}\n"

                prompt = f"""请为一部{genre}小说生成大纲。

小说标题：{title}

角色设定：
{character_setting}

世界观设定：
{world_setting}

剧情构思：
{plot_idea}
{context_info}
要求：
- 基于上面已生成的章节，**继续往下生成**第{start_chapter_num}到第{start_chapter_num + chapter_count - 1}章
- 每章包含：章节标题、简要描述（50字内）、场景拆分（2-4个关键场景）
- 场景拆分格式：场景1-开场，场景2-发展，场景3-高潮，场景4-收尾
- 确保剧情连贯，与前面章节自然衔接

【重要】必须严格按照以下JSON格式返回，注意：
1. 只返回JSON，不要有任何其他文字、说明或markdown标记
2. 不要使用```json或```包裹
3. 确保所有引号都是英文双引号"
4. 确保JSON完整，不要中途截断
5. 每个章节的scenes数组必须完整闭合

JSON格式示例：
{{
  "title": "{title}",
  "chapters": [
    {{
      "num": {start_chapter_num},
      "title": "章节标题",
      "description": "章节描述",
      "scenes": [
        {{"order": 1, "name": "开场", "purpose": "承接上文"}},
        {{"order": 2, "name": "发展", "purpose": "推进剧情"}},
        {{"order": 3, "name": "高潮", "purpose": "本章重点"}},
        {{"order": 4, "name": "收尾", "purpose": "本章结束"}}
      ]
    }}
  ]
}}

现在请直接返回完整的JSON："""

                # AI自我重试提示（仅在重试时添加）
                if attempt > 0:
                    retry_hint = f"\n\n【重要提醒】上次生成失败（{last_error}），请务必：\n1. 确保生成完整的JSON，不要截断\n2. 每个章节的scenes数组必须完整闭合\n3. 检查所有括号和引号是否配对\n"
                    prompt = prompt + retry_hint

                # 调用API生成
                logger.debug(f"调用API生成第{start_chapter_num}-{start_chapter_num + chapter_count - 1}章")

                # 完全动态计算token，不依赖全局配置
                # 每章约3500-4000 tokens输出（包含4个场景的JSON）
                tokens_per_chapter = 4000
                required_tokens = chapter_count * tokens_per_chapter
                # 不再使用全局outline_max_tokens，完全根据章节数动态计算
                safe_max_tokens = required_tokens
                logger.info(f"使用 max_tokens={safe_max_tokens} 生成{chapter_count}章（每章约{tokens_per_chapter} tokens）")

                response = self.api_client.generate([
                    {"role": "system", "content": "你是一个专业的小说大纲创作助手。你必须只返回有效的JSON格式数据，不要添加任何其他文字。"},
                    {"role": "user", "content": prompt}
                ], temperature=0.7, max_tokens=safe_max_tokens)

                if not response:
                    last_error = "AI返回空响应"
                    logger.error(f"API返回空响应（第{attempt + 1}次尝试）")
                    continue

                logger.debug(f"API响应长度: {len(response)} 字符")

                # 解析JSON响应（复用之前的解析逻辑）
                result = self._parse_outline_response(response)
                if not result:
                    last_error = "无法解析AI返回的大纲（JSON格式错误）"
                    logger.warning(f"JSON解析失败（第{attempt + 1}次尝试），准备重试...")
                    continue

                # 验证章节号是否正确
                chapters = result.get("chapters", [])
                if not chapters:
                    last_error = "返回的大纲没有章节信息"
                    logger.warning(f"大纲没有章节信息（第{attempt + 1}次尝试），准备重试...")
                    continue

                # 确保章节号正确
                for i, ch in enumerate(chapters):
                    expected_num = start_chapter_num + i
                    if ch['num'] != expected_num:
                        logger.warning(f"章节号不匹配: 期望{expected_num}，实际{ch['num']}，自动修正")
                        ch['num'] = expected_num

                # 成功！
                if attempt > 0:
                    logger.info(f"[自动重试成功] 第{attempt + 1}次尝试成功，生成了{len(chapters)}章")
                return True, "生成成功", chapters

            except Exception as e:
                last_error = str(e)
                logger.error(f"生成批次大纲失败（第{attempt + 1}次尝试）: {e}")
                continue

        # 所有重试都失败
        logger.error(f"[自动重试失败] 已尝试{max_retries}次，全部失败。最后错误: {last_error}")
        return False, f"生成失败（已重试{max_retries}次）: {last_error}", []

    def _parse_outline_response(self, response: str) -> Optional[Dict]:
        """
        解析大纲API响应（增强版，多层级清理和修复）

        Args:
            response: API返回的原始响应

        Returns:
            解析后的字典，失败返回None
        """
        import re

        # ========== 第1步：预处理 ==========
        # 清理响应内容
        cleaned_response = response.strip()

        # 1.1 去除可能的markdown代码块标记
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        # 1.2 去除可能的前缀文字（如"好的，这是大纲："）
        # 查找第一个 { 的位置
        first_brace = cleaned_response.find('{')
        if first_brace > 0:
            prefix = cleaned_response[:first_brace].strip()
            if prefix:
                logger.debug(f"去除前缀文字: {prefix[:50]}...")
            cleaned_response = cleaned_response[first_brace:]

        # 1.3 去除可能的后缀文字
        # 找到最后一个 } 的位置
        last_brace = cleaned_response.rfind('}')
        if last_brace != -1 and last_brace < len(cleaned_response) - 1:
            suffix = cleaned_response[last_brace + 1:].strip()
            if suffix:
                logger.debug(f"去除后缀文字: {suffix[:50]}...")
            cleaned_response = cleaned_response[:last_brace + 1]

        # 1.4 修复中文引号（这是JSON解析失败的主要原因）
        cleaned_response = cleaned_response.replace('"', '"').replace('"', '"')
        cleaned_response = cleaned_response.replace(''', "'").replace(''', "'")

        # 1.5 修复常见的JSON格式问题
        # 修复缺少逗号的情况（如 "title": "xxx" "description": "yyy"）
        cleaned_response = re.sub(r'"\s*\n\s*"', '",\n"', cleaned_response)
        # 修复多余的逗号（如数组最后一个元素后的逗号）
        cleaned_response = re.sub(r',\s*\]', ']', cleaned_response)
        cleaned_response = re.sub(r',\s*\}', '}', cleaned_response)

        # ========== 第2步：尝试直接解析 ==========
        try:
            result = json.loads(cleaned_response)
            logger.info("直接解析JSON成功")
            return result
        except json.JSONDecodeError as je:
            logger.warning(f"直接解析JSON失败: {je}，尝试进一步修复")

        # ========== 第3步：尝试修复截断的JSON ==========
        # 检测是否是截断问题（JSON不完整）
        open_braces = cleaned_response.count('{')
        close_braces = cleaned_response.count('}')
        open_brackets = cleaned_response.count('[')
        close_brackets = cleaned_response.count(']')

        if open_braces != close_braces or open_brackets != close_brackets:
            logger.info(f"检测到JSON不完整: {{ = {open_braces}/{close_braces}, [ = {open_brackets}/{close_brackets}，尝试修复截断")
            
            # 尝试修复截断的JSON
            repaired_json = self._repair_truncated_json(cleaned_response)
            if repaired_json:
                try:
                    result = json.loads(repaired_json)
                    actual_chapters = len(result.get('chapters', []))
                    logger.info(f"成功修复截断的JSON，保留了{actual_chapters}章")
                    return result
                except json.JSONDecodeError as repair_error:
                    logger.error(f"修复后的JSON仍然无法解析: {repair_error}")

        # ========== 第4步：尝试正则提取 ==========
        json_match = re.search(r'\{[\s\S]*\}', cleaned_response)
        if json_match:
            json_str = json_match.group(0)
            try:
                result = json.loads(json_str)
                logger.info("通过正则提取成功解析JSON")
                return result
            except json.JSONDecodeError as je3:
                logger.error(f"正则提取后仍然解析失败: {je3}")

        # ========== 第5步：所有尝试都失败 ==========
        logger.error(f"所有JSON解析尝试都失败")
        logger.error(f"原始响应（前1000字符）: {response[:1000]}")
        logger.error(f"清理后响应（前1000字符）: {cleaned_response[:1000]}")
        return None

    def _repair_truncated_json(self, json_str: str) -> Optional[str]:
        """
        修复截断的JSON，找到最后一个完整的章节对象

        Args:
            json_str: 截断的JSON字符串

        Returns:
            修复后的JSON字符串，失败返回None
        """
        import re

        try:
            # 移除外层的 { 和 } 以便处理chapters数组
            inner_content = json_str.strip()
            if inner_content.startswith('{'):
                inner_content = inner_content[1:]
            if inner_content.endswith('}'):
                inner_content = inner_content[:-1]

            # 找到所有的章节对象
            # 改进的正则：匹配包含scenes数组的完整章节对象
            # 策略：找到每个章节的开始标记 "num": X，然后找到对应的完整对象
            chapters = []
            
            # 方法1：尝试匹配完整的章节对象（包含scenes）
            # 使用更灵活的模式，匹配到scenes数组结束
            chapter_pattern_with_scenes = r'\{\s*"num"\s*:\s*\d+,\s*"title"\s*:\s*"[^"]*",\s*"description"\s*:\s*"[^"]*",\s*"scenes"\s*:\s*\[[\s\S]*?\]\s*\}'
            matches = list(re.finditer(chapter_pattern_with_scenes, inner_content))
            
            if matches:
                logger.info(f"使用完整章节模式匹配到 {len(matches)} 个章节")
                for match in matches:
                    chapter_str = match.group(0).strip()
                    # 验证是否是有效的JSON
                    try:
                        json.loads(chapter_str)
                        chapters.append(chapter_str)
                    except json.JSONDecodeError:
                        continue
            
            # 方法2：如果方法1没有匹配到，尝试逐个解析章节
            if not chapters:
                logger.info("尝试逐个解析章节...")
                # 找到所有章节的开始位置
                chapter_starts = list(re.finditer(r'\{\s*"num"\s*:\s*(\d+)', inner_content))
                
                for i, start_match in enumerate(chapter_starts):
                    start_pos = start_match.start()
                    # 确定结束位置（下一个章节开始，或字符串结束）
                    if i + 1 < len(chapter_starts):
                        end_pos = chapter_starts[i + 1].start()
                    else:
                        end_pos = len(inner_content)
                    
                    chapter_segment = inner_content[start_pos:end_pos].strip()
                    
                    # 尝试找到完整的章节对象
                    # 查找最后一个完整的 }
                    brace_count = 0
                    last_valid_pos = -1
                    for pos, char in enumerate(chapter_segment):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                last_valid_pos = pos + 1
                                break
                    
                    if last_valid_pos > 0:
                        chapter_str = chapter_segment[:last_valid_pos].strip()
                        try:
                            # 验证是否是有效的JSON
                            parsed = json.loads(chapter_str)
                            if 'num' in parsed and 'title' in parsed:
                                chapters.append(chapter_str)
                                logger.debug(f"成功解析章节: 第{parsed['num']}章")
                        except json.JSONDecodeError:
                            continue

            if not chapters:
                logger.warning("无法从截断的JSON中提取任何有效章节")
                return None

            # 重建JSON
            chapters_json = ",\n    ".join(chapters)
            repaired_json = f'{{\n  "title": "Generated Outline",\n  "chapters": [\n    {chapters_json}\n  ]\n}}'

            logger.info(f"修复截断JSON：原JSON长度={len(json_str)}，修复后={len(repaired_json)}，成功提取{len(chapters)}章")
            return repaired_json

        except Exception as e:
            logger.warning(f"[自动生成] 修复截断JSON失败: {e}")
            return None

    def save_generation_cache(
        self,
        project_id: str,
        chapter_num: int,
        chapter_data: Dict,
        context_data: Optional[Dict] = None
    ) -> None:
        """
        保存生成缓存

        Args:
            project_id: 项目ID
            chapter_num: 章节号
            chapter_data: 章节数据
            context_data: 上下文数据（摘要等）
        """
        try:
            cache_file = self.cache_dir / f"{project_id}_cache.json"

            # 读取现有缓存
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            else:
                cache = {
                    "project_id": project_id,
                    "generated_chapters": {},
                    "context": {}
                }

            # 保存章节数据
            cache["generated_chapters"][str(chapter_num)] = {
                "data": chapter_data,
                "timestamp": datetime.now().isoformat()
            }

            # 保存上下文数据
            if context_data:
                cache["context"][str(chapter_num)] = context_data

            # 写入文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

            logger.debug(f"[自动生成] 保存缓存: 第{chapter_num}章")

        except Exception as e:
            logger.warning(f"[自动生成] 保存缓存失败: {e}")

    def load_generation_cache(self, project_id: str) -> Dict:
        """
        加载生成缓存

        Args:
            project_id: 项目ID

        Returns:
            缓存数据字典
        """
        try:
            cache_file = self.cache_dir / f"{project_id}_cache.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                logger.info(f"[自动生成] 加载缓存: {len(cache.get('generated_chapters', {}))} 章")
                return cache
        except Exception as e:
            logger.warning(f"[自动生成] 加载缓存失败: {e}")

        return {}

    def _ensure_summary_manager_initialized(self, project_id: str) -> None:
        """
        确保分层摘要管理器已初始化
        
        Args:
            project_id: 项目ID
        """
        if self._summary_manager is None or self._summary_manager.project_id != project_id:
            self._summary_manager = HierarchicalSummaryManager(
                project_id=project_id,
                chapters_per_arc=10,
                recent_chapters=5,
                cache_dir=self.cache_dir.parent / "coherence"
            )
            logger.info(f"已初始化分层摘要管理器: project_id={project_id}")

    def _build_smart_context(
        self,
        project_id: str,
        chapter_num: int,
        previous_chapters: List[Dict],
        max_tokens: int
    ) -> Tuple[str, bool]:
        """
        智能构建上下文（使用分层摘要系统）

        核心改进：
        - 使用分层摘要系统解决长小说上下文断裂问题
        - 第1-10章 → 第一卷摘要
        - 第11-20章 → 第二卷摘要
        - ...
        - 最新5章 → 完整内容

        Args:
            project_id: 项目ID
            chapter_num: 当前章节号
            previous_chapters: 前面章节列表
            max_tokens: 可用的最大token数

        Returns:
            (context_text, should_generate_summary)
        """
        # 确保动态调整系统已初始化
        self._ensure_dynamic_adjustment_initialized()
        
        # 确保分层摘要管理器已初始化
        self._ensure_summary_manager_initialized(project_id)

        # 加载上下文配置
        context_config = {
            "context_enable": True,
            "context_mode": "summary",
            "context_max_chapters": 50,
            "context_auto_allocate": True,
            "prev_chapter_tail_chars": 800,
        }

        config_file = Path("config/generation_config.json")
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            context_config["context_enable"] = config.get("context_enable", True)
            context_config["context_mode"] = config.get("context_mode", "summary")
            context_config["context_max_chapters"] = config.get("context_max_chapters", 50)
            context_config["context_auto_allocate"] = config.get("context_auto_allocate", True)
            context_config["prev_chapter_tail_chars"] = config.get("prev_chapter_tail_chars", 800)

        context_mode = context_config["context_mode"]
        prev_chapter_tail_chars = context_config["prev_chapter_tail_chars"]

        # 如果上下文被禁用或模式为disabled，仍保留最小衔接信息，避免后续章节被误写成“第一章”
        if not context_config["context_enable"] or context_mode == "disabled":
            logger.info("上下文机制已关闭，使用最小衔接模式")
            if not previous_chapters:
                return "【这是第一章，直接开始创作】", True

            last_chapter = previous_chapters[-1]
            last_title = last_chapter.get("title", "")
            last_content = (last_chapter.get("content", "") or "").strip()
            last_excerpt = last_content[-prev_chapter_tail_chars:] if last_content else "上一章内容不可用，请至少延续已知设定。"

            minimal_bridge = f"""【最小衔接信息】
当前要写的是第{chapter_num}章，不是第一章。
请延续既有角色关系、世界规则和剧情进度，不要重置设定。
上一章：第{last_chapter.get('num', chapter_num - 1)}章《{last_title}》
上一章结尾片段：
{last_excerpt}
"""
            return minimal_bridge, True

        logger.info(f"第{chapter_num}章上下文设置: mode={context_mode}")

        # 如果没有前面的章节，返回基础上下文
        if not previous_chapters:
            logger.info("没有前面的章节，返回基础上下文")
            return "【这是第一章，直接开始创作】", True

        # ========== 使用分层摘要系统构建上下文 ==========
        if context_mode == "summary":
            # 摘要模式：使用分层摘要管理器
            context_text = self._summary_manager.get_context_for_chapter(
                chapter_num=chapter_num,
                all_chapters=previous_chapters,
                prev_chapter_tail_chars=prev_chapter_tail_chars
            )
            
            # 获取统计信息
            stats = self._summary_manager.get_summary_stats()
            logger.info(f"分层摘要上下文构建完成: 已有{stats['total_arcs']}个卷摘要, 涵盖{stats['total_chapters_covered']}章")
            
            return context_text, True

        elif context_mode == "full":
            # 全文模式：保留原有逻辑，但有章节限制
            config_max_chapters = context_config["context_max_chapters"]
            max_chapters = min(self.context_chapter_limit, config_max_chapters)

            # 计算实际使用的章节数
            if chapter_num > max_chapters:
                start_idx = len(previous_chapters) - max_chapters
                relevant_chapters = previous_chapters[start_idx:] if start_idx >= 0 else previous_chapters
                logger.info(f"全文模式：使用最近{max_chapters}章作为上下文")
            else:
                relevant_chapters = previous_chapters
                logger.info(f"全文模式：使用前面所有章节（共{len(relevant_chapters)}章）")

            context_parts = []

            # 全文模式下不添加前一章尾部原文，因为已经包含完整章节
            # 只有摘要模式才需要添加前一章尾部
            logger.info(f"全文模式：不添加前一章尾部原文（已包含完整章节）")

            # 添加完整章节内容
            context_parts.append("【前文内容】")
            total_chars = 0
            chapters_with_content = 0

            for prev_ch in relevant_chapters:
                content = prev_ch.get("content", "")
                if content and content.strip():
                    context_parts.append(f"第{prev_ch['num']}章 {prev_ch['title']}:\n{content}")
                    total_chars += len(content)
                    chapters_with_content += 1

            if chapters_with_content == 0:
                logger.warning(f"全文模式：没有找到有内容的章节")
                return "【这是第一章，直接开始创作】", True

            # 添加最近5章摘要
            context_parts.append("\n【剧情连续性】")
            for prev_ch in relevant_chapters[-5:]:
                summary = prev_ch.get("summary", "")
                if summary:
                    context_parts.append(f"第{prev_ch['num']}章摘要: {summary}")

            context_text = "\n".join(context_parts)
            logger.info(f"全文模式：使用{chapters_with_content}章完整内容，总字符数: {total_chars}")

            return context_text, False

        else:
            # 未知模式，使用分层摘要系统
            logger.warning(f"未知的上下文模式: {context_mode}，使用分层摘要系统")
            context_text = self._summary_manager.get_context_for_chapter(
                chapter_num=chapter_num,
                all_chapters=previous_chapters,
                prev_chapter_tail_chars=prev_chapter_tail_chars
            )
            return context_text, True

    def generate_chapter(
        self,
        project_id: str,
        chapter_info: Dict,
        previous_chapters: List[Dict],
        use_context: bool = True
    ) -> Tuple[bool, str, Dict]:
        """
        生成单个章节（支持动态token调整和自动重试）

        Args:
            project_id: 项目ID
            chapter_info: 章节信息 {num, title, description}
            previous_chapters: 前面章节列表
            use_context: 是否使用上下文

        Returns:
            (success, message, chapter_data)
        """
        chapter_num = chapter_info["num"]
        chapter_title = chapter_info["title"]
        chapter_desc = chapter_info["description"]

        logger.info(f"生成第 {chapter_num} 章: {chapter_title}")

        # 确保动态调整参数已重置为配置值
        self._reset_dynamic_adjustment()

        # 读取目标字数配置
        target_words = 3000  # 默认值
        generation_preferences = {
            "temperature": 0.78,
            "writing_style": "详细生动",
            "writing_tone": "第三人称",
            "character_dev": "平衡发展",
            "plot_complexity": "中等复杂",
            "frequency_penalty": None,
            "presence_penalty": None,
        }
        try:
            gen_config_file = Path("config/generation_config.json")
            if gen_config_file.exists():
                with open(gen_config_file, 'r', encoding='utf-8') as f:
                    gen_config = json.load(f)
                    target_words = gen_config.get("target_words", 3000)
                    generation_preferences["temperature"] = gen_config.get("temperature", generation_preferences["temperature"])
                    generation_preferences["writing_style"] = gen_config.get("writing_style", generation_preferences["writing_style"])
                    generation_preferences["writing_tone"] = gen_config.get("writing_tone", generation_preferences["writing_tone"])
                    generation_preferences["character_dev"] = gen_config.get("character_dev", generation_preferences["character_dev"])
                    generation_preferences["plot_complexity"] = gen_config.get("plot_complexity", generation_preferences["plot_complexity"])
                    generation_preferences["frequency_penalty"] = gen_config.get("frequency_penalty", None)
                    generation_preferences["presence_penalty"] = gen_config.get("presence_penalty", None)
        except Exception as e:
            logger.warning(f"读取配置失败，使用默认值: {e}")

        # 重试机制（最多3次）
        target_words_override = self._runtime_int("NOVEL_TARGET_WORDS_OVERRIDE")
        if target_words_override and target_words_override > 0:
            target_words = target_words_override

        disable_context = self._runtime_flag("NOVEL_DISABLE_SMART_CONTEXT")
        disable_assessment = self._runtime_flag("NOVEL_DISABLE_CHAPTER_ASSESSMENT")
        disable_coherence_updates = self._runtime_flag("NOVEL_DISABLE_COHERENCE_UPDATES")

        for retry_count in range(3):
            try:
                # 使用动态token调整
                max_tokens_limit = self._calculate_max_tokens(target_words)
                logger.info(f"第{retry_count + 1}次尝试 - max_tokens={max_tokens_limit} (系数: {self.token_adjustment_factor:.3f}, 上下文: {self.context_chapter_limit}章)")

                # 构建上下文（使用动态调整的上下文章节数）
                if disable_context:
                    context_text = ""
                    should_generate_summary = False
                    coherence_info = ""
                    previous_summary = ""
                    project_reference = ""
                    canonical_names = []
                else:
                    context_text, should_generate_summary = self._build_smart_context(
                        project_id, chapter_num, previous_chapters, max_tokens_limit
                    )

                    # 获取连贯性信息
                    coherence_info = self._get_coherence_context(project_id, chapter_num)
                    previous_summary = self._get_previous_summary(previous_chapters)
                scene_plan = ScenePlanner.plan_scenes(
                    target_words=target_words,
                    chapter_desc=chapter_desc,
                    context_hint=chapter_title
                )
                if not disable_context:
                    project_reference = self._build_project_reference(project_id, chapter_num)
                    canonical_names = self._extract_canonical_names(
                        project_reference,
                        previous_summary,
                        chapter_title,
                        chapter_desc,
                    )
                scene_plan_text = "\n".join(
                    [
                        (
                            f"{idx + 1}. {scene['name']}（约{scene['target_words']}字）\n"
                            f"   目标：{scene['purpose']}\n"
                            f"   要素：{', '.join(scene.get('key_elements', []))}"
                        )
                        for idx, scene in enumerate(scene_plan)
                    ]
                )

                # 读取风格配置
                genre = self._get_genre_from_project(project_id)
                style_config = self._load_style_config(genre)

                # 构建生成提示词
                prompt = f"""{context_text}

【当前章节】
第{chapter_num}章：{chapter_title}

【章节要求】
{chapter_desc}

{coherence_info}

銆愬墠鎯呮憳瑕併€?
{previous_summary or "鏃犻渶棰濆鎽樿锛岀洿鎺ユ壙鎺ヤ笂鏂囧嵆鍙€?"}

銆愭湰绔犲満鏅鑲鍒掋€?
{scene_plan_text}
【项目参考卡】
{project_reference}
【必须保留的名称】
{canonical_names or "如上文所示，无额外名称白名单。"}
【命名一致性】
如果角色设定、前文或章节大纲里已经出现角色名、地名、组织名，请原样沿用，不要自行改名、翻译、简写或中英互换。

【写作基调】
- 语言风格：{generation_preferences['writing_style']}
- 叙述视角：{generation_preferences['writing_tone']}
- 角色推进：{generation_preferences['character_dev']}
- 剧情复杂度：{generation_preferences['plot_complexity']}

【创作要求】
1. 目标字数：约 {target_words} 字（可在±500字范围内浮动）
2. 保持与前文的连贯性，不能重置人物关系、世界规则和剧情状态
3. 以场景、动作、对话推动情节，不要写成提纲、总结或说明文
4. 角色性格、目标和情绪变化要有依据，不能突然跳变
5. 多写具体细节和感官反馈，少写空泛感叹、套路排比和模板化抒情
6. 避免明显 AI 腔，不要频繁使用"与此同时""这一刻""然而""不由得"等机械转场
7. 结尾要自然留下下一章推进空间，但不要直接预告"下一章将会发生什么"
8. 直接输出小说正文，不要添加小标题、序号、括号说明或创作分析

【绝对禁止使用的AI套话】
突然、竟然、霎时间、不由得、禁不住、心中涌起、却然、陡然、
在...的时候、随着...的发展、在...的背景下、
不禁...了起来、一股、一股...涌上心头、眼中闪过一丝...、
嘴角微微上扬、轻轻地点了点头、深深地吸了一口气、
心中暗想、暗自下定决心、感受到了前所未有的...、
仿佛...一般、宛如...似的、犹如...一样、恍如...、
不由自主地、情不自禁地、下意识地、
一种...的感觉、说不出的...、难以言喻的...、
浑身一震、瞳孔骤缩、倒吸一口凉气、
气氛突然变得...、空气中弥漫着...、
此刻、这一刻、这一瞬间、刹那间、
缓缓开口、沉声说道、语气坚定地说、
目光如炬、眼中带着...的神色、
迈着坚定的步伐、头也不回地、义无反顾地、
与此同时、然而、只见、赫然、顿时、
缓缓地、超乎想象、不可思议

【高级写作技法】
1. 展示而非告知：不要说"他很伤心"，而是描写"他手指微微颤抖，咖啡杯里的涟漪映着窗外的灰天"
2. 用动作代替形容：不要说"美丽的花园"，而是写"月季爬满石墙，蜜蜂在花瓣间穿梭"
3. 对话推动情节：每段对话至少包含一个信息增量或情感转折
4. 感官交错：视觉、听觉、触觉、嗅觉交替使用，营造沉浸感
5. 节奏变化：紧张段落用短句，舒缓段落用长句，避免句式单调
6. 信息差管理：读者知道但角色不知道，或角色知道但读者不知道——制造悬念

请开始创作本章内容："""

                # 构建消息列表（如有风格配置则注入风格system_prompt）
                messages = []

                # 注入风格系统提示词（优先使用风格配置）
                if style_config and style_config.get("system_prompt"):
                    messages.append({"role": "system", "content": style_config["system_prompt"]})
                    logger.info(f"第{chapter_num}章使用风格配置: {genre}")
                else:
                    messages.append({"role": "system", "content": "你是一位擅长中文长篇小说的职业作家。请直接输出自然、连贯、有场景感的正文，避免模板化总结、机械转场和明显AI痕迹。"})

                messages.append({"role": "user", "content": prompt})

                # 调用API生成
                response = self.api_client.generate(
                    messages,
                    temperature=generation_preferences["temperature"],
                    max_tokens=max_tokens_limit,
                    frequency_penalty=generation_preferences.get("frequency_penalty"),
                    presence_penalty=generation_preferences.get("presence_penalty")
                )

                response = self._sanitize_generated_text(response)

                if not response or len(response.strip()) < 100:
                    logger.warning(f"第{chapter_num}章生成内容过短，准备重试")
                    continue

                if disable_assessment:
                    optimized_content = response
                    actual_word_count = len(optimized_content)
                    word_diff = actual_word_count - target_words
                    diff_percent = abs(word_diff) / target_words * 100

                    logger.info(
                        f"[stress] 第{chapter_num}章 - 目标: {target_words}, 实际: {actual_word_count}, "
                        f"误差: {word_diff:+d} ({diff_percent:.1f}%)"
                    )
                    self._adjust_token_factor(actual_word_count, target_words)

                    chapter_data = {
                        "num": chapter_num,
                        "title": chapter_title,
                        "desc": chapter_desc,
                        "content": optimized_content,
                        "word_count": actual_word_count,
                        "generated_at": datetime.now().isoformat(),
                        "style_report": {"score": None, "grade": "skipped", "issues_count": 0},
                        "quality_report": {"skipped": True},
                        "summary": ""
                    }

                    if disable_coherence_updates:
                        logger.info("[stress] skip coherence updates for chapter %s", chapter_num)
                    else:
                        self._update_coherence_system(project_id, chapter_data)

                    self.save_generation_cache(
                        project_id,
                        chapter_num,
                        chapter_data,
                        {"summary": chapter_data.get("summary", "")}
                    )

                    logger.info(f"[stress] 第 {chapter_num} 章生成成功，字数: {chapter_data['word_count']}")
                    return True, f"第{chapter_num}章生成成功", chapter_data

                # ========== 统一评估系统（AI去味 + 质量评估） ==========
                # 配置统一评估器
                self.unified_assessor.configure(
                    ai_taste_level=self.optimization_config.get("ai_taste_level", "basic"),
                    enable_quality_assessment=self.optimization_config.get("enable_quality_assessment", True),
                    quality_min_score=self.optimization_config.get("quality_min_score", 70.0),
                    quality_rewrite_threshold=self.optimization_config.get("quality_rewrite_threshold", 60.0)
                )

                # 执行统一评估
                assessment_report = self.unified_assessor.assess(
                    content=response,
                    chapter_num=chapter_num,
                    chapter_outline=chapter_desc,
                    previous_summary=self._get_previous_summary(previous_chapters),
                    optimize=True  # 自动优化
                )

                # 使用优化后的内容
                optimized_content = assessment_report.optimized_content or response
                missing_required_names = self._find_missing_required_names(
                    optimized_content,
                    canonical_names
                )
                if missing_required_names:
                    missing_reason = f"关键名称漂移: {', '.join(missing_required_names)}"
                    assessment_report.need_rewrite = True
                    assessment_report.rewrite_reason = (
                        f"{assessment_report.rewrite_reason}; {missing_reason}"
                        if assessment_report.rewrite_reason else missing_reason
                    )
                    logger.warning(f"第{chapter_num}章命名一致性检查未通过: {missing_reason}")

                # 记录评估结果
                logger.info(f"第{chapter_num}章统一评估完成:")
                logger.info(f"  - 总分: {assessment_report.total_score:.1f} ({assessment_report.grade})")
                logger.info(f"  - AI去味: {assessment_report.ai_taste_score:.1f} ({assessment_report.ai_taste_grade})")
                logger.info(f"  - 质量评分: {assessment_report.quality_score:.1f} ({assessment_report.quality_grade})")

                # 检查是否需要重写
                if assessment_report.need_rewrite and self.optimization_config.get("enable_auto_rewrite", False):
                    logger.warning(f"第{chapter_num}章需要重写: {assessment_report.rewrite_reason}")
                    
                    # 执行自动重写
                    max_attempts = self.optimization_config.get("max_rewrite_attempts", 2)
                    rewrite_content = ""
                    
                    for attempt in range(1, max_attempts + 1):
                        logger.info(f"[自动重写] 第{chapter_num}章第{attempt}次重写尝试")
                        
                        # 生成重写提示
                        rewrite_prompt = create_assessment_prompt(assessment_report)
                        
                        # 使用目标字数的token设置重新生成
                        # 注意：重写时使用相同的target_words和token系数
                        rewrite_content = self._rewrite_chapter(
                            project_id=project_id,
                            chapter_num=chapter_num,
                            chapter_title=chapter_title,
                            chapter_desc=chapter_desc,
                            previous_chapters=previous_chapters,
                            target_words=target_words,
                            source_content=optimized_content,
                            rewrite_prompt=rewrite_prompt,
                            attempt=attempt
                        )
                        
                        if not rewrite_content:
                            logger.warning(f"[自动重写] 第{attempt}次重写失败")
                            continue
                        
                        # 重新评估重写后的内容
                        assessment_report = self.unified_assessor.assess(
                            content=rewrite_content,
                            chapter_num=chapter_num,
                            chapter_outline=chapter_desc,
                            previous_summary=self._get_previous_summary(previous_chapters),
                            optimize=True
                        )
                        
                        logger.info(f"[自动重写] 第{attempt}次重写结果: 总分={assessment_report.total_score:.1f}")
                        
                        # 如果重写后合格，使用新内容
                        candidate_content = assessment_report.optimized_content or rewrite_content
                        rewrite_word_count = len(candidate_content)
                        min_acceptable_words = int(target_words * 0.75)
                        missing_required_names = self._find_missing_required_names(
                            candidate_content,
                            canonical_names
                        )
                        if missing_required_names:
                            missing_reason = f"关键名称漂移: {', '.join(missing_required_names)}"
                            assessment_report.need_rewrite = True
                            assessment_report.rewrite_reason = (
                                f"{assessment_report.rewrite_reason}; {missing_reason}"
                                if assessment_report.rewrite_reason else missing_reason
                            )
                        if not assessment_report.need_rewrite and rewrite_word_count >= min_acceptable_words:
                            logger.info(f"[自动重写] 第{chapter_num}章重写成功！")
                            optimized_content = candidate_content
                            break
                        else:
                            rewrite_reason = assessment_report.rewrite_reason
                            if rewrite_word_count < min_acceptable_words:
                                rewrite_reason = f"{rewrite_reason}; 字数不足 ({rewrite_word_count} < {min_acceptable_words})" if rewrite_reason else f"字数不足 ({rewrite_word_count} < {min_acceptable_words})"
                            logger.warning(f"[自动重写] 第{attempt}次重写仍不合格: {rewrite_reason}")
                    
                    # 如果所有重写尝试都失败，使用最后一次的结果
                    if assessment_report.need_rewrite:
                        logger.warning(f"[自动重写] 第{chapter_num}章经过{max_attempts}次重写仍未达标，使用最后一次结果")
                        optimized_content = assessment_report.optimized_content or rewrite_content

                # 保存评估报告
                style_report = {
                    "score": assessment_report.ai_taste_score,
                    "grade": assessment_report.ai_taste_grade,
                    "issues_count": len(assessment_report.ai_taste_issues)
                }
                quality_report = assessment_report.to_dict()


                # 实际字数
                actual_word_count = len(optimized_content)
                word_diff = actual_word_count - target_words
                diff_percent = abs(word_diff) / target_words * 100

                logger.info(f"第{chapter_num}章 - 目标: {target_words}, 实际: {actual_word_count}, 误差: {word_diff:+d} ({diff_percent:.1f}%)")

                # 动态调整token系数（基于生成结果）
                self._adjust_token_factor(actual_word_count, target_words)

                # 构建章节数据
                chapter_data = {
                    "num": chapter_num,
                    "title": chapter_title,
                    "desc": chapter_desc,
                    "content": optimized_content,  # 使用优化后的内容
                    "word_count": actual_word_count,
                    "generated_at": datetime.now().isoformat(),
                    "style_report": style_report,  # 添加风格报告
                    "quality_report": quality_report  # 添加质量报告
                }

                # 生成摘要（如果需要）
                if should_generate_summary:
                    # 使用新的摘要生成方法，确保覆盖完整章节内容
                    chapter_data["summary"] = self._generate_chapter_summary(optimized_content, max_length=100)
                    logger.info(f"已生成第{chapter_num}章摘要（内容长度: {len(optimized_content)}字）")
                else:
                    chapter_data["summary"] = ""
                    logger.info(f"全文模式跳过摘要生成")

                # 更新连贯性系统
                logger.info(f"准备更新连贯性系统: 第{chapter_num}章（连贯性系统存在: {self.character_tracker is not None}）")
                if disable_coherence_updates:
                    logger.info("[stress] skip coherence updates for chapter %s", chapter_num)
                else:
                    self._update_coherence_system(project_id, chapter_data)

                # 保存缓存
                self.save_generation_cache(
                project_id,
                chapter_num,
                chapter_data,
                {"summary": chapter_data.get("summary", "")}
                )

                # ========== 分层摘要系统：检查是否需要生成卷摘要 ==========
                if self._summary_manager and self._summary_manager.should_generate_arc_summary(chapter_num):
                    arc_id = self._summary_manager.get_arc_id(chapter_num)
                    logger.info(f"第{chapter_num}章是第{arc_id}卷的最后一章，准备生成卷摘要")

                # 获取该卷的所有章节（包括刚生成的章节）
                # 注意：这里需要从previous_chapters中获取，因为chapter_data还未被加入
                    arc_chapters = self._summary_manager.get_arc_chapters(arc_id, previous_chapters + [chapter_data])

                    if arc_chapters:
                        # 生成卷摘要
                        self._generate_and_save_arc_summary(arc_id, arc_chapters)

                logger.info(f"第 {chapter_num} 章生成成功，字数: {chapter_data['word_count']}")
                return True, f"第{chapter_num}章生成成功", chapter_data

            except Exception as e:
                error_msg = str(e)
                logger.error(f"第{chapter_num}章生成失败 (第{retry_count + 1}次尝试): {e}")

                # 检测错误类型并尝试恢复
                error_type = self._detect_api_error_type(error_msg)

                if error_type in ['token_limit', 'context_too_long']:
                    should_retry, action_msg = self._handle_api_error(error_type, retry_count)
                    if should_retry:
                        logger.warning(f"第{chapter_num}章: {action_msg}")
                        continue # 重试
                    else:
                        return False, f"第{chapter_num}章生成失败: {action_msg}", {}

                # 其他错误，直接返回失败
                return False, f"第{chapter_num}章生成失败: {error_msg}", {}

        return False, f"第{chapter_num}章生成失败: 达到最大重试次数", {}

    def _generate_and_save_arc_summary(self, arc_id: int, arc_chapters: List[Dict]) -> None:
        """
        生成并保存卷摘要
        
        Args:
            arc_id: 卷号
            arc_chapters: 该卷的所有章节
        """
        logger.info(f"开始生成第{arc_id}卷摘要，包含{len(arc_chapters)}章")

        # 收集所有章节摘要
        chapter_summaries = []
        for ch in arc_chapters:
            summary = ch.get("summary", "")
            title = ch.get("title", "")
            num = ch.get("num", 0)
            if summary:
                chapter_summaries.append(f"第{num}章《{title}》: {summary}")
            elif title:
                chapter_summaries.append(f"第{num}章《{title}》")

        if not chapter_summaries:
            logger.warning(f"第{arc_id}卷没有章节摘要，跳过卷摘要生成")
            return

        # 构建卷摘要提示词
        summaries_text = "\n".join(chapter_summaries)
        arc_summary_prompt = f"""请根据以下章节摘要，生成一个完整的卷摘要（约500字）。

章节摘要：
{summaries_text}

请包含以下内容：
1. 主要情节发展（一句话概括核心剧情）
2. 主要事件列表（3-5个关键事件）
3. 角色变化（主要角色的成长或转变）
4. 未回收的伏笔（如果有）

请按以下JSON格式返回：
{{
    "summary": "卷摘要内容...",
    "main_events": ["事件1", "事件2", "事件3"],
    "character_changes": ["角色A的变化", "角色B的变化"],
    "foreshadowing": ["伏笔1", "伏笔2"]
}}

只返回JSON，不要其他文字。"""

        # 调用API生成卷摘要
        response = self.api_client.generate([
            {"role": "system", "content": "你是一个专业的小说编辑，擅长提炼和总结故事脉络。"},
            {"role": "user", "content": arc_summary_prompt}
        ], temperature=0.3, max_tokens=800)

        if not response:
            logger.error(f"生成第{arc_id}卷摘要失败: API返回空")
            return

        # 解析JSON响应
        response_text = response.strip()

        # 尝试提取JSON部分
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group()
        else:
            json_str = response_text

        arc_data = json.loads(json_str)

        # 更新分层摘要管理器
        self._summary_manager.update_arc_summary(
            arc_id=arc_id,
            chapters=arc_chapters,
            summary=arc_data.get("summary", ""),
            main_events=arc_data.get("main_events", []),
            character_changes=arc_data.get("character_changes", []),
            foreshadowing=arc_data.get("foreshadowing", [])
        )

        logger.info(f"✅ 第{arc_id}卷摘要生成完成")

    def _rewrite_chapter(
        self,
        project_id: str,
        chapter_num: int,
        chapter_title: str,
        chapter_desc: str,
        previous_chapters: List[Dict],
        target_words: int,
        source_content: str,
        rewrite_prompt: str,
        attempt: int
    ) -> Optional[str]:
        """
        重写章节
        
        Args:
            project_id: 项目ID
            chapter_num: 章节号
            chapter_title: 章节标题
            chapter_desc: 章节描述
            previous_chapters: 前面章节列表
            target_words: 目标字数
            rewrite_prompt: 重写提示
            attempt: 重写尝试次数
            
        Returns:
            重写后的内容，失败返回None
        """
        try:
            # 计算max_tokens（使用目标字数和当前的token系数）
            # 重写时使用相同的token设置，确保字数一致
            base_max_tokens = int(target_words * 1.2)  # 基础token
            adjusted_max_tokens = int(base_max_tokens * self.token_adjustment_factor)
            
            # 构建上下文
            context_text, use_summary = self._build_smart_context(
                project_id=project_id,
                chapter_num=chapter_num,
                previous_chapters=previous_chapters,
                max_tokens=adjusted_max_tokens
            )
            project_reference = self._build_project_reference(project_id, chapter_num)
            canonical_names = self._extract_canonical_names(project_reference, source_content, chapter_title, chapter_desc)
            
            # 获取提示词模板
            
            logger.info(f"[自动重写] 第{attempt}次尝试 - max_tokens={adjusted_max_tokens} (系数: {self.token_adjustment_factor:.3f})")
            
            # 构建重写提示词
            rewrite_system_prompt = f"""你是一个专业的小说作家，正在重写第{chapter_num}章。

{rewrite_prompt}
【重写硬约束】
1. 必须保留原文中的题材、角色身份、核心冲突和关键线索。
2. 只允许优化表达和结构，不允许把当前章节改写成另一个故事。
3. 原文里已经出现的角色名、地名和组织名必须保持一致。

銆愬緟淇鍘熸枃銆?
{source_content}
【项目参考卡】
{project_reference}

銆愪笉鍙繚鑳岀殑绾︽潫銆?
1. 蹇呴』淇濇寔褰撳墠绔犺妭鐨勯鏉愩€佹椂浠ｃ€佷富瑕佷汉鐗┿€佽韩浠藉拰鍦扮偣锛屼笉瑕佹崲涓€涓晠浜嬮噸鍐?
2. 涓嶈鑷繁鏂板涓庡綋鍓嶅ぇ绾叉棤鍏崇殑涓昏銆佷笘鐣岃鎴栦富绾垮啿绐?
3. 閲嶅啓鐨勭洰鐨勬槸鈥滄妸鍘熸湁鍐呭鍐欏緱鏇村ソ鈥濓紝涓嶆槸鎹㈡垚鍙︿竴绡囧皬璇?

请根据以上问题重新创作本章，注意：
1. 严格控制在{target_words}字左右（误差不超过±200字）
2. 避免使用AI化表达
3. 提高情节连贯性
4. 增强角色刻画
5. 丰富细节描写
6. 保持风格一致"""

            # 构建用户提示词
            user_prompt = f"""【章节信息】
章节：第{chapter_num}章
标题：{chapter_title}
大纲：{chapter_desc}

【前文上下文】
{context_text}
銆愬緟淇鍘熸枃銆?
{source_content}

【重写要求】
{rewrite_prompt}

请重新创作第{chapter_num}章《{chapter_title}》，目标字数约{target_words}字。"""

            # 调用API生成
            response = self.api_client.generate([
                {"role": "system", "content": rewrite_system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.8, max_tokens=adjusted_max_tokens)
            
            # 清理响应
            content = self._sanitize_generated_text(response)
            if not content:
                logger.warning(f"[自动重写] 第{attempt}次未获得有效正文，返回重试")
                return None
            
            # 检查字数
            actual_words = len(content)
            word_diff = actual_words - target_words
            diff_percent = abs(word_diff) / target_words * 100
            
            logger.info(f"[自动重写] 第{attempt}次结果 - 目标: {target_words}, 实际: {actual_words}, 误差: {word_diff:+d} ({diff_percent:.1f}%)")
            
            # 动态调整token系数（基于重写结果）
            self._adjust_token_factor(actual_words, target_words)
            
            return content
            
        except Exception as e:
            logger.error(f"[自动重写] 第{attempt}次重写失败: {e}", exc_info=True)
            return None

    def _extract_canonical_names(self, *texts: str) -> str:
        """Extract stable Latin-script names that should not be translated or renamed."""
        candidates: List[str] = []
        stopwords = {"API", "JSON", "Word", "Markdown", "HTML", "TXT", "Lin".upper()}

        for text in texts:
            if not text:
                continue
            for token in re.findall(r"\b[A-Z][A-Za-z0-9_-]{1,}\b", str(text)):
                if token.upper() in stopwords:
                    continue
                if token not in candidates:
                    candidates.append(token)

        if "Lin" in " ".join(texts) and "Lin" not in candidates:
            candidates.insert(0, "Lin")

        return ", ".join(candidates[:12])

    def _find_missing_required_names(self, content: str, canonical_names: str) -> List[str]:
        """Return required Latin-script names that disappeared from the generated text."""
        if not canonical_names:
            return []

        missing: List[str] = []
        required_names = [name.strip() for name in canonical_names.split(",") if name.strip()]
        normalized_content = content or ""

        for name in required_names:
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) and name not in normalized_content:
                missing.append(name)

        return missing

    def _build_project_reference(self, project_id: str, chapter_num: int) -> str:
        """Load stable project metadata to reduce naming and setting drift."""
        try:
            project_file = self.project_dir / f"{project_id}.json"
            if not project_file.exists():
                return "无额外项目参考。"

            project = json.loads(project_file.read_text(encoding="utf-8"))
            outline = project.get("outline", [])
            current_outline = next((item for item in outline if item.get("num") == chapter_num), {})

            parts = [
                f"项目标题：{project.get('title', '')}",
                f"题材类型：{project.get('genre', '')}",
                f"角色设定：{project.get('character_setting', '')}",
                f"世界设定：{project.get('world_setting', '')}",
                f"主线构思：{project.get('plot_idea', '')}",
            ]

            if current_outline:
                parts.append(f"当前章节标题：{current_outline.get('title', '')}")
                parts.append(f"当前章节大纲：{current_outline.get('description', '')}")

            return "\n".join(part for part in parts if part and not part.endswith("："))
        except Exception as exc:
            logger.warning(f"读取项目参考失败: {exc}")
            return "无额外项目参考。"

    def _load_style_config(self, genre: str) -> Optional[Dict]:
        """加载风格配置

        根据小说类型(genre)匹配对应的风格提示词JSON文件，
        返回风格配置字典，无匹配时返回None。
        """
        genre_map = {
            "玄幻": "xuanhuan", "仙侠": "xuanhuan",
            "都市": "dushi_romance", "言情": "dushi_romance",
            "悬疑": "xuanyi", "推理": "xuanyi",
            "历史": "lishi", "穿越": "lishi",
            "科幻": "kehuan",
            "武侠": "wuxia",
            "现实": "xianshi",
            "轻小说": "qingxiaoshuo",
        }
        style_id = genre_map.get(genre)
        if not style_id:
            return None
        style_path = Path("config/style_prompts") / f"{style_id}.json"
        if not style_path.exists():
            return None
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"加载风格配置失败 ({genre}/{style_id}): {exc}")
            return None

    def _get_genre_from_project(self, project_id: str) -> str:
        """从项目文件中读取题材类型"""
        try:
            project_file = self.project_dir / f"{project_id}.json"
            if project_file.exists():
                project = json.loads(project_file.read_text(encoding="utf-8"))
                return project.get("genre", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def _extract_message_content(response: Any) -> str:
        """Extract assistant text from SDK objects, dict payloads, or content blocks."""
        if response is None:
            return ""

        if isinstance(response, str):
            return response.strip()

        if isinstance(response, dict):
            choices = response.get("choices") or []
            if choices:
                message = choices[0].get("message") or {}
                content = message.get("content")
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict):
                            text = item.get("text") or item.get("content") or ""
                            if text:
                                parts.append(str(text))
                    return "".join(parts).strip()
                if content:
                    return str(content).strip()
            content = response.get("content")
            if content:
                return str(content).strip()
            return ""

        choices = getattr(response, "choices", None)
        if choices:
            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            if message is not None:
                content = getattr(message, "content", None)
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        text = getattr(item, "text", None)
                        if text:
                            parts.append(str(text))
                    return "".join(parts).strip()
                if content:
                    return str(content).strip()

        content = getattr(response, "content", None)
        if content:
            return str(content).strip()

        return str(response).strip()

    def _sanitize_generated_text(self, response) -> str:
        """Normalize SDK responses into plain chapter text."""
        text = self._extract_message_content(response)
        if not text:
            return ""

        if text.startswith("ChatCompletion(") or "ChatCompletionMessage(" in text:
            logger.warning("检测到非正文的 SDK 对象字符串，按空结果处理")
            return ""

        return text

    def _get_previous_summary(self, previous_chapters: List[Dict]) -> str:
        """
        获取前文摘要

        Args:
            previous_chapters: 前面章节列表

        Returns:
            前文摘要文本
        """
        if not previous_chapters:
            return ""

        # 获取最近3章的摘要
        recent_chapters = previous_chapters[-3:]
        summaries = []

        for ch in recent_chapters:
            summary = ch.get("summary", "")
            if summary:
                summaries.append(f"第{ch['num']}章: {summary}")

        return "\n".join(summaries)

    def _generate_chapter_summary(self, chapter_content: str, max_length: int = 100) -> str:
            """
            生成章节摘要，确保覆盖完整内容
            
            根据章节长度采用不同的采样策略：
            - 短章节（≤2000字）：使用完整内容
            - 中等章节（2000-5000字）：开头500字 + 中间500字 + 结尾500字
            - 长章节（>5000字）：开头500字 + 中间均匀采样500字 + 结尾500字
            
            Args:
                chapter_content: 章节内容
                max_length: 摘要最大字数（默认100字）
                
            Returns:
                生成的摘要文本
            """
            content_len = len(chapter_content)
            
            if content_len <= 2000:
                # 短章节：使用完整内容
                sample_content = chapter_content
                sample_desc = "完整内容"
            elif content_len <= 5000:
                # 中等章节：开头 + 中间 + 结尾
                mid_start = (content_len - 500) // 2
                sample_content = (
                    chapter_content[:500] +
                    "\n……\n" +
                    chapter_content[mid_start:mid_start + 500] +
                    "\n……\n" +
                    chapter_content[-500:]
                )
                sample_desc = f"开头500字+中间500字+结尾500字（总长{content_len}字）"
            else:
                # 长章节：开头 + 中间采样 + 结尾
                mid_start = content_len // 2
                sample_content = (
                    chapter_content[:500] +
                    "\n……\n" +
                    chapter_content[mid_start - 250:mid_start + 250] +
                    "\n……\n" +
                    chapter_content[-500:]
                )
                sample_desc = f"开头500字+中间采样500字+结尾500字（总长{content_len}字）"
            
            logger.info(f"生成摘要采样策略: {sample_desc}")
            
            summary_prompt = f"""请用简洁的语言总结以下章节的主要情节（{max_length}字以内）。
    
    要求：
    1. 包含主要情节发展
    2. 包含关键角色行为
    3. 包含重要事件转折
    4. 确保覆盖开头、中间、结尾的关键信息
    
    章节内容：
    {sample_content}
    
    只返回摘要内容，不要其他文字。"""
            
            summary = self.api_client.generate([
                {"role": "system", "content": "你是一个专业的小说摘要助手，擅长提炼章节核心内容。"},
                {"role": "user", "content": summary_prompt}
            ], temperature=0.3, max_tokens=300)
            
            return summary.strip() if summary else ""

    def _get_coherence_context(self, project_id: str, chapter_num: int) -> str:
        """获取连贯性上下文"""
        context_parts = []

        # 角色状态
        if self.character_tracker and self.character_tracker.all_characters:
            context_parts.append("【主要角色】")
            # 获取前5个角色的当前状态
            for char_name in list(self.character_tracker.all_characters)[:5]:
                char_state = self.character_tracker.get_character_current_state(char_name)
                if char_state:
                    status = char_state.location or "未知"
                    personality = char_state.personality or ""
                    context_parts.append(f"- {char_name}: {status} {(f'({personality})' if personality else '')}")
                else:
                    context_parts.append(f"- {char_name}")

        # 剧情线
        if self.plot_manager:
            active_threads = self.plot_manager.get_active_threads()
            if active_threads:
                context_parts.append("\n【当前剧情线】")
                for thread in active_threads[:3]:
                    context_parts.append(f"- {thread.name}: {thread.status}")

        # 世界观信息（如果有相关内容）
        if self.world_db:
            try:
                world_summary = self.world_db.get_world_summary(max_items=3)
                if world_summary and len(world_summary) > 20:
                    context_parts.append(f"\n{world_summary}")
            except Exception as e:
                logger.debug(f"获取世界观摘要失败: {e}")

        return "\n".join(context_parts) if context_parts else ""

    def _update_coherence_system(self, project_id: str, chapter_data: Dict) -> None:
        """更新连贯性系统"""
        try:
            chapter_content = chapter_data.get("content", "")
            chapter_num = chapter_data.get("num", 1)
            chapter_title = chapter_data.get("title", "")
            chapter_desc = chapter_data.get("desc", "")
            # 构造章节大纲字符串
            chapter_outline = f"第{chapter_num}章：{chapter_title}\n{chapter_desc}" if chapter_title else ""

            logger.info(f"连贯性系统状态: character_tracker={self.character_tracker is not None}, plot_manager={self.plot_manager is not None}, world_db={self.world_db is not None}")

            if not chapter_content or len(chapter_content) < 50:
                logger.warning(f"章节内容过短，跳过连贯性提取: 第{chapter_num}章（长度: {len(chapter_content)}）")
                return

            # 提取并更新角色信息
            if self.character_tracker:
                try:
                    from src.core.coherence.character_tracker import analyze_characters_from_chapter
                    logger.info(f"📊 开始提取角色信息: 第{chapter_num}章")
                    analyze_characters_from_chapter(
                        chapter_content,
                        chapter_num,
                        self.character_tracker,
                        self.api_client
                    )
                    logger.info(f"✅ 角色信息提取完成: 第{chapter_num}章")
                except Exception as e:
                    logger.error(f"❌ 提取角色信息失败: 第{chapter_num}章 - {e}")
            else:
                logger.warning("⚠️ character_tracker 未初始化，跳过角色提取")

            # 提取并更新剧情信息
            if self.plot_manager:
                try:
                    from src.core.coherence.plot_manager import analyze_plot_from_chapter
                    logger.info(f"📊 开始提取剧情信息: 第{chapter_num}章")
                    analyze_plot_from_chapter(
                        chapter_content,
                        chapter_outline,
                        chapter_num,
                        self.plot_manager,
                        self.api_client
                    )
                    logger.info(f"✅ 剧情信息提取完成: 第{chapter_num}章")
                except Exception as e:
                    logger.error(f"❌ 提取剧情信息失败: 第{chapter_num}章 - {e}")
            else:
                logger.warning("⚠️ plot_manager 未初始化，跳过剧情提取")

            # 注意：世界观数据库暂不支持自动提取，需要手动添加或使用其他方式

        except Exception as e:
            logger.error(f"❌ 更新连贯性系统失败: 第{chapter_num}章 - {e}", exc_info=True)

    def _ensure_dynamic_adjustment_initialized(self) -> None:
        """确保动态调整系统的属性已初始化（向后兼容）"""
        if not hasattr(self, 'token_adjustment_factor'):
            self.token_adjustment_factor = 1.0
            logger.info("初始化 token_adjustment_factor = 1.0")
        if not hasattr(self, 'context_chapter_limit'):
            self.context_chapter_limit = 50
            logger.info("初始化 context_chapter_limit = 50")
        if not hasattr(self, 'adjustment_history'):
            self.adjustment_history = []
            logger.info("初始化 adjustment_history = []")
        if not hasattr(self, 'should_pause'):
            self.should_pause = False
            logger.info("初始化 should_pause = False")

    def _reset_dynamic_adjustment(self) -> None:
        """
        重置动态调整参数为配置文件中的值
        每次新的生成任务开始时调用，确保使用用户配置的上下文章节数
        """
        # 从配置文件读取用户设置的上下文章节数
        config_max_chapters = 50  # 默认值
        try:
            config_file = Path("config/generation_config.json")
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    config_max_chapters = config.get("context_max_chapters", 50)
        except Exception as e:
            logger.warning(f"读取配置失败，使用默认上下文章节数: {e}")

        # 重置动态调整参数
        self.token_adjustment_factor = 1.0
        self.context_chapter_limit = config_max_chapters
        self.adjustment_history = []

        logger.info(f"[动态上下文] 重置为配置值: {config_max_chapters}章 (token系数: 1.0)")

    def _calculate_max_tokens(self, target_words: int) -> int:
        """
        根据目标字数和调整系数计算max_tokens

        Args:
            target_words: 目标字数

        Returns:
            调整后的max_tokens
        """
        # 确保动态调整系统已初始化
        self._ensure_dynamic_adjustment_initialized()

        base_tokens = int(target_words * 1.2)  # 基础token数
        adjusted_tokens = int(base_tokens * self.token_adjustment_factor)
        return max(adjusted_tokens, 1000)  # 最小1000 tokens

    def _adjust_token_factor(self, actual_words: int, target_words: int) -> None:
        """
        根据实际生成字数与目标字数的差距，调整token系数

        Args:
            actual_words: 实际生成的字数
            target_words: 目标字数
        """
        # 确保动态调整系统已初始化
        self._ensure_dynamic_adjustment_initialized()

        # 计算比率
        ratio = actual_words / target_words if target_words > 0 else 1.0

        # 记录到历史
        self.adjustment_history.append(ratio)

        # 只保留最近10次记录
        if len(self.adjustment_history) > 10:
            self.adjustment_history.pop(0)

        # 计算加权平均比率（最近的结果权重更高）
        if len(self.adjustment_history) >= 3:
            weighted_ratio = sum(self.adjustment_history[-3:]) / min(3, len(self.adjustment_history))
        else:
            weighted_ratio = ratio

        # 调整系数（平滑调整，每次最多调整10%）
        if weighted_ratio < 0.9:
            # 字数偏少，增加token
            new_factor = self.token_adjustment_factor * 1.1
            logger.info(f"字数偏少 ({actual_words}/{target_words}={ratio:.2f})，增加token系数: {self.token_adjustment_factor:.3f} → {new_factor:.3f}")
        elif weighted_ratio > 1.1:
            # 字数偏多，减少token
            new_factor = self.token_adjustment_factor * 0.9
            logger.info(f"字数偏多 ({actual_words}/{target_words}={ratio:.2f})，减少token系数: {self.token_adjustment_factor:.3f} → {new_factor:.3f}")
        else:
            # 字数合适，微调向1.0靠拢
            new_factor = self.token_adjustment_factor * 0.95 + 1.0 * 0.05
            logger.info(f"字数合适 ({actual_words}/{target_words}={ratio:.2f})，token系数保持: {self.token_adjustment_factor:.3f}")

        # 限制系数范围在0.5-2.0之间
        self.token_adjustment_factor = max(0.5, min(2.0, new_factor))

    def _detect_api_error_type(self, error_message: str) -> str:
        """
        检测API错误类型（支持GLM、OpenAI等格式）

        Args:
            error_message: 错误信息

        Returns:
            错误类型: 'token_limit', 'context_too_long', 'other', 'none'
        """
        error_lower = error_message.lower()

        # GLM模型常见错误格式
        # Error code: 400 - {'error': {'code': '1210', 'message': "Requested token count exceeds the model's maximum context length"}}
        if '1210' in error_message or 'requested token count exceeds' in error_lower:
            return 'token_limit'

        # 通用token超限错误
        if any(keyword in error_lower for keyword in [
            'maximum context length',
            'max_length',
            'too long',
            'exceed',
            'token limit',
            'tokens exceed'
        ]):
            # 区分是输入上下文太长还是输出太长
            if 'input' in error_lower or 'context' in error_lower or 'messages' in error_lower:
                return 'context_too_long'
            else:
                return 'token_limit'

        # OpenAI格式错误
        if 'max_tokens' in error_lower and 'exceed' in error_lower:
            return 'token_limit'

        return 'other'

    def _handle_api_error(self, error_type: str, retry_count: int) -> Tuple[bool, str]:
        """
        处理API错误，自动调整参数（优先减少上下文）

        Args:
            error_type: 错误类型
            retry_count: 当前重试次数

        Returns:
            (should_retry, action_message)
        """
        # 确保动态调整系统已初始化
        self._ensure_dynamic_adjustment_initialized()

        if retry_count >= 5:  # 增加到5次重试
            return False, "已达最大重试次数"

        if error_type == 'context_too_long':
            # 上下文过长：优先减少上下文章节数（这是主要原因）
            old_limit = self.context_chapter_limit

            # 激进减少策略：50→40→30→20→15→10→5
            if old_limit > 30:
                self.context_chapter_limit = max(20, old_limit - 10)  # 减少10章
            elif old_limit > 10:
                self.context_chapter_limit = max(5, old_limit - 5)   # 减少5章
            else:
                # 上下文已经很少了，尝试减少token系数
                old_factor = self.token_adjustment_factor
                self.token_adjustment_factor *= 0.8  # 减少20%
                logger.warning(f"上下文已最少，降低token系数: {old_factor:.3f} → {self.token_adjustment_factor:.3f}")
                return True, f"降低max_tokens并重试 (第{retry_count + 1}次，上下文: {self.context_chapter_limit}章)"

            logger.warning(f"检测到上下文过长错误，减少上下文章节: {old_limit} → {self.context_chapter_limit}")
            return True, f"减少上下文并重试 (第{retry_count + 1}次，上下文: {self.context_chapter_limit}章)"

        elif error_type == 'token_limit':
            # token超限（可能是输出太长）：同时调整上下文和token系数
            old_limit = self.context_chapter_limit
            old_factor = self.token_adjustment_factor

            # 同时减少上下文和token系数
            if self.context_chapter_limit > 5:
                self.context_chapter_limit = max(5, int(self.context_chapter_limit * 0.7))

            self.token_adjustment_factor *= 0.8  # 减少20%

            logger.warning(
                f"检测到token超限错误，"
                f"上下文: {old_limit} → {self.context_chapter_limit}章, "
                f"token系数: {old_factor:.3f} → {self.token_adjustment_factor:.3f}"
            )
            return True, f"减少上下文和max_tokens并重试 (第{retry_count + 1}次)"

        return False, "未知错误类型"

    def generate_full_novel(
        self,
        project_id: str,
        outline: List[Dict],
        start_chapter: int = 1,
        progress_callback=None,
        existing_chapters: List[Dict] = None
    ) -> Tuple[bool, str, List[Dict]]:
        """
        生成完整小说

        Args:
            project_id: 项目ID
            outline: 大纲列表
            start_chapter: 起始章节号
            progress_callback: 进度回调函数
            existing_chapters: 已存在的章节数据（用于继续生成）

        Returns:
            (success, message, all_chapters)
        """
        try:
            self.is_generating = True
            self.should_stop = False
            self.current_project_id = project_id
            self.total_chapters = len(outline)

            # 重置动态调整参数（每次新的生成任务都从配置重新读取）
            self._reset_dynamic_adjustment()

            # 初始化连贯性系统（如果还未初始化）
            logger.info(f"检查连贯性系统状态: character_tracker={self.character_tracker is not None}, plot_manager={self.plot_manager is not None}, world_db={self.world_db is not None}")

            if not self.character_tracker or not self.plot_manager or not self.world_db:
                logger.info(f"初始化连贯性系统: {project_id}")
                from src.core.coherence import CharacterTracker, PlotManager, WorldDatabase
                cache_dir = Path("cache/coherence")
                cache_dir.mkdir(parents=True, exist_ok=True)

                if not self.character_tracker:
                    self.character_tracker = CharacterTracker(project_id, cache_dir)
                    logger.info("✓ CharacterTracker 初始化完成")
                if not self.plot_manager:
                    self.plot_manager = PlotManager(project_id, cache_dir)
                    logger.info("✓ PlotManager 初始化完成")
                if not self.world_db:
                    self.world_db = WorldDatabase(project_id, cache_dir)
                    logger.info("✓ WorldDatabase 初始化完成")
            else:
                logger.info("连贯性系统已存在，直接使用")

            # 初始化all_chapters
            all_chapters = []
            failed_chapters = []  # 记录失败的章节

            # 如果是继续生成（start_chapter > 1），加载已有章节作为上下文
            if start_chapter > 1:
                if existing_chapters:
                    # 使用传入的已有章节
                    all_chapters = existing_chapters
                    logger.info(f"继续生成模式：加载了 {len(all_chapters)} 个已有章节作为上下文")
                else:
                    # 尝试从项目文件加载
                    try:
                        project_file = self.project_dir / f"{project_id}.json"
                        if project_file.exists():
                            with open(project_file, 'r', encoding='utf-8') as f:
                                project_data = json.load(f)
                            all_chapters = project_data.get("chapters", [])
                            logger.info(f"继续生成模式：从项目文件加载了 {len(all_chapters)} 个已有章节作为上下文")
                        else:
                            logger.warning(f"项目文件不存在：{project_file}，将从第{start_chapter}章开始生成，但没有上下文")
                    except Exception as e:
                        logger.warning(f"加载已有章节失败: {e}，将从第{start_chapter}章开始生成，但没有上下文")

            logger.info(f"开始生成完整小说: {len(outline)} 章，当前上下文: {len(all_chapters)} 章")

            # 确定要生成的章节范围
            for chapter_info in outline:
                if self.should_stop:
                    logger.info("用户请求停止生成")
                    break

                chapter_num = chapter_info.get("num", 1)
                if chapter_num < start_chapter:
                    continue

                # 更新进度
                if progress_callback:
                    progress_callback(
                        chapter_num,  # current
                        self.total_chapters,  # total
                        f"正在生成第 {chapter_num} 章: {chapter_info.get('title', '')}"  # message
                    )

                logger.info(f"生成进度: {chapter_num}/{self.total_chapters} - 正在生成第 {chapter_num} 章: {chapter_info.get('title', '')}")

                # 生成章节（上下文配置从generation_config.json读取）
                success, message, chapter_data = self.generate_chapter(
                    project_id,
                    chapter_info,
                    all_chapters,  # 前面的章节作为上下文
                    use_context=True  # 智能上下文构建器会读取配置文件决定实际行为
                )

                if not success:
                    logger.warning(f"第 {chapter_num} 章生成失败: {message}")
                    # 记录失败但继续生成
                    failed_chapters.append({
                        "num": chapter_num,
                        "title": chapter_info.get("title", ""),
                        "error": message
                    })
                    # 继续生成下一章，不中断
                    continue

                all_chapters.append(chapter_data)

                # 保存到项目文件（每生成一章就保存）
                self._save_project_chapters(project_id, all_chapters)

            # 生成完成后的总结
            success_count = len(all_chapters)
            failed_count = len(failed_chapters)

            if failed_count > 0:
                logger.warning(f"生成完成，但{failed_count}章失败: {[ch['num'] for ch in failed_chapters]}")
                message = f"部分成功: 成功生成{success_count}章，失败{failed_count}章"
                if failed_chapters:
                    message += f" (失败章节: {', '.join([str(ch['num']) for ch in failed_chapters])})"

            # 保存连贯性系统数据
            try:
                if self.character_tracker:
                    self.character_tracker.save_to_disk()
                if self.plot_manager:
                    self.plot_manager.save_to_disk()
                if self.world_db:
                    self.world_db.save_to_disk()
                logger.info("连贯性系统数据已保存")
            except Exception as e:
                logger.warning(f"保存连贯性系统数据失败: {e}")

            # 如果至少有一章成功，就认为整体成功
            return len(all_chapters) > 0, message, all_chapters

        except Exception as e:
            logger.error(f"生成小说失败: {e}", exc_info=True)
            return False, f"生成失败: {str(e)}", []

        finally:
            self.is_generating = False

    def stop_generation(self) -> None:
        """停止生成"""
        self.should_stop = True
        logger.info("已发送停止信号")

    def _save_project_chapters(self, project_id: str, chapters: List[Dict]) -> None:
        """保存章节到项目文件"""
        try:
            project_file = self.project_dir / f"{project_id}.json"

            # 读取现有项目数据
            if project_file.exists():
                with open(project_file, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
            else:
                project_data = {
                    "id": project_id,
                    "chapters": []
                }

            # 更新章节
            project_data["chapters"] = chapters
            project_data["updated_at"] = datetime.now().isoformat()

            # 保存
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"保存项目文件: {len(chapters)} 章")

        except Exception as e:
            logger.warning(f"保存项目文件失败: {e}")


def create_auto_generation_ui(
    app_state,
    generator: AutoNovelGenerator,
    project_choices: dict = None
):
    """
    创建自动生成UI

    Args:
        app_state: 应用状态
        generator: 自动生成器实例
        project_choices: 项目字典 {project_id: title}（用于加载项目，使用ID避免同名冲突）

    Returns:
        Gradio组件
    """
    import gradio as gr

    # 自动生成状态
    generation_progress = gr.State(value="")
    generation_status = gr.State(value="")
    loaded_project_id = gr.State(value="")  # 当前加载的项目ID

    # 准备Dropdown的choices（格式：[["项目标题 (ID)", "project_id"], ...]）
    if project_choices:
        dropdown_choices = [
            [f"{title} ({pid})", pid]  # 显示："标题 (ID)"，值：project_id
            for pid, title in project_choices.items()
        ]
    else:
        dropdown_choices = []

    with gr.Column():
        gr.Markdown("## 🚀 完整小说自动生成")
        gr.Markdown("填写基本信息 → 指定章节数 → 一键生成整本小说")

        with gr.Row():
            with gr.Column(scale=2):
                auto_title = gr.Textbox(
                    label="小说标题",
                    placeholder="例如：修仙之路",
                    lines=1
                )
                auto_genre = gr.Dropdown(
                    choices=[
                        "玄幻",
                        "仙侠",
                        "科幻",
                        "都市",
                        "历史",
                        "军事",
                        "游戏",
                        "体育",
                        "灵异",
                        "武侠",
                        "言情",
                        "其他"
                    ],
                    value="玄幻",
                    label="小说类型",
                    allow_custom_value=True,  # 允许用户输入自定义类型
                    info="选择或输入小说类型"
                )

            with gr.Column(scale=3):
                auto_chapter_count = gr.Slider(
                    minimum=10,
                    maximum=1000,
                    value=50,
                    step=10,
                    label="章节数量",
                    info="生成多少章"
                )

        auto_character_setting = gr.Textbox(
            label="角色设定",
            placeholder="描述主要角色：姓名、性格、背景、目标等",
            lines=5
        )

        auto_world_setting = gr.Textbox(
            label="世界观设定",
            placeholder="描述故事世界的规则、背景、设定等",
            lines=5
        )

        auto_plot_idea = gr.Textbox(
            label="剧情构思",
            placeholder="描述主要剧情走向、冲突、高潮等",
            lines=5
        )

        # 生成选项
        with gr.Row():
            auto_use_coherence = gr.Checkbox(
                value=True,
                label="使用连贯性系统",
                info="跟踪角色、剧情、世界观"
            )

        # ========== 新增：AI去味和质量评估设置 ==========
        gr.Markdown("### 🎯 质量控制设置")
        
        with gr.Row():
            with gr.Column(scale=1):
                auto_ai_taste_level = gr.Radio(
                    choices=[
                        ("禁用", "disabled"),
                        ("基础去味", "basic"),
                        ("强力去味", "strong")
                    ],
                    value="strong",
                    label="AI去味等级",
                    info="基础：本地自动修正 | 强力：AI辅助优化"
                )
            
            with gr.Column(scale=1):
                auto_enable_quality = gr.Checkbox(
                    value=True,
                    label="启用质量评估",
                    info="评估章节质量并给出改进建议"
                )
        
        with gr.Row():
            with gr.Column(scale=1):
                auto_quality_min_score = gr.Slider(
                    minimum=50,
                    maximum=90,
                    value=75,
                    step=5,
                    label="最低质量分",
                    info="低于此分数会标记为需要改进"
                )
            
            with gr.Column(scale=1):
                auto_quality_rewrite_threshold = gr.Slider(
                    minimum=40,
                    maximum=70,
                    value=68,
                    step=5,
                    label="重写阈值",
                    info="低于此分数建议重写章节"
                )
        
        with gr.Row():
            auto_enable_auto_rewrite = gr.Checkbox(
                value=True,
                label="自动重写不合格章节",
                info="当质量分低于重写阈值时自动重写"
            )
            
            auto_max_rewrite_attempts = gr.Slider(
                minimum=1,
                maximum=5,
                value=3,
                step=1,
                label="最大重写次数",
                info="最多尝试重写几次"
            )
        
        gr.Markdown("""
        💡 **提示**：
        - **AI去味等级**：基础模式使用本地规则修正，强力模式会调用AI进行深度优化
        - **质量评估**：会从连贯性、情节、角色、风格等多个维度评估章节质量
        - **重写功能**：当章节质量过低时，系统会根据评估报告自动重写
        - 上下文机制请在「系统设置 > 生成参数配置」中设置
        """)

        # ========== 原有的UI继续 ==========

        # 生成按钮 - 分为两组
        # 第一组：创建新项目
        with gr.Row():
            auto_generate_btn = gr.Button("🆕 创建新项目并开始生成", variant="primary", size="lg")

        # 第二组：控制按钮（暂停/继续 + 停止）
        with gr.Row():
            is_paused = gr.State(value=False)  # 是否已暂停

            auto_pause_continue_btn = gr.Button(
                "⏸️ 暂停",
                variant="secondary",
                size="lg"
            )
            auto_stop_btn = gr.Button("⏹️ 停止生成", variant="stop", size="lg")

        # 进度显示 - 使用更清晰的布局
        gr.Markdown("### 📊 生成进度")

        with gr.Row():
            # 进度百分比
            progress_percentage = gr.Textbox(
                label="完成度",
                value="0%",
                interactive=False,
                scale=1
            )
            # 当前章节
            progress_current = gr.Textbox(
                label="当前章节",
                value="- / -",
                interactive=False,
                scale=1
            )
            # 预计剩余时间
            progress_eta = gr.Textbox(
                label="预计剩余",
                value="--:--",
                interactive=False,
                scale=1
            )

        # 进度条
        progress_bar_slider = gr.Slider(
            minimum=0,
            maximum=100,
            value=0,
            label="进度条",
            interactive=False
        )

        # 详细日志
        with gr.Accordion("📝 详细日志", open=False):
            progress_box = gr.Textbox(
                label="生成日志",
                lines=15,
                interactive=False
            )

        # 统计信息
        with gr.Row():
            total_words_generated = gr.Textbox(
                label="已生成总字数",
                value="0 字",
                interactive=False
            )
            avg_words_per_chapter = gr.Textbox(
                label="平均章节字数",
                value="0 字",
                interactive=False
            )

        # ========== 项目加载区域 ==========
        gr.Markdown("### 📖 加载已有项目继续生成")
        gr.Markdown("""
        💡 **使用说明**：
        - 🆕 **创建新项目并开始生成**：创建全新的小说项目
        - 📖 **加载项目**：加载已有项目到表单
        - ✍️ **继续生成**：从上次停止处继续生成已加载的项目
        """)

        with gr.Row():
            auto_load_project_select = gr.Dropdown(
                choices=dropdown_choices,
                label="📖 选择要继续的项目",
                interactive=True,
                value=None
            )

        # 显示项目详细信息
        auto_load_project_info = gr.Textbox(
            label="项目信息",
            lines=5,
            interactive=False
        )

        # 操作按钮
        with gr.Row():
            auto_load_btn = gr.Button("📖 加载项目", variant="primary", size="lg")
            auto_export_btn = gr.Button("📤 导出小说")
            auto_continue_btn = gr.Button("✍️ 继续生成", variant="primary", size="lg")

        # 生成结果
        auto_result = gr.Textbox(
            label="生成结果",
            lines=5,
            interactive=False
        )

    # 事件处理
    def on_start_generation(
        title,
        genre,
        chapter_count,
        character_setting,
        world_setting,
        plot_idea,
        use_coherence,
        # 新增：质量控制参数
        ai_taste_level,
        enable_quality,
        quality_min_score,
        quality_rewrite_threshold,
        enable_auto_rewrite,
        max_rewrite_attempts
    ):
        """开始生成"""
        # 配置生成器的质量控制参数
        generator.optimization_config["ai_taste_level"] = ai_taste_level
        generator.optimization_config["enable_quality_assessment"] = enable_quality
        generator.optimization_config["quality_min_score"] = quality_min_score
        generator.optimization_config["quality_rewrite_threshold"] = quality_rewrite_threshold
        generator.optimization_config["enable_auto_rewrite"] = enable_auto_rewrite
        generator.optimization_config["max_rewrite_attempts"] = max_rewrite_attempts
        
        logger.info(f"[质量控制] AI去味等级: {ai_taste_level}")
        logger.info(f"[质量控制] 质量评估: {enable_quality}, 最低分: {quality_min_score}, 重写阈值: {quality_rewrite_threshold}")
        logger.info(f"[质量控制] 自动重写: {enable_auto_rewrite}, 最大次数: {max_rewrite_attempts}")
        
        if not title or not genre:
            yield (
                "❌ 请填写小说标题和类型",  # progress_box
                "0%",  # progress_percentage
                "- / -",  # progress_current
                "--:--",  # progress_eta
                0,  # progress_bar_slider
                "0 字",  # total_words_generated
                "0 字",  # avg_words_per_chapter
                "",  # auto_result
                ""  # project_id (placeholder)
            )
            return

        if not character_setting or not world_setting or not plot_idea:
            yield (
                "❌ 请填写角色设定、世界观设定和剧情构思",
                "0%",
                "- / -",
                "--:--",
                0,
                "0 字",
                "0 字",
                "信息不完整",
                ""
            )
            return

        try:
            # 生成项目ID
            project_id = datetime.now().strftime("%Y%m%d-%H%M%S")

            # 1. 生成大纲
            progress_text = f"📝 正在生成大纲...\n"

            yield (
                progress_text,
                "0%",
                "0 / 0",
                "--:--",
                0,
                "0 字",
                "0 字",
                "正在生成大纲...",
                ""
            )

            success, message, outline = generator.generate_outline(
                title,
                genre,
                character_setting,
                world_setting,
                plot_idea,
                int(chapter_count)
            )

            if not success:
                yield (
                    f"❌ {message}",
                    "0%",
                    "- / -",
                    "--:--",
                    0,
                    "0 字",
                    "0 字",
                    "大纲生成失败",
                    ""
                )
                return

            progress_text += f"✓ {message}\n大纲包含 {len(outline)} 章\n\n"

            yield (
                progress_text,
                "5%",
                "0 / " + str(len(outline)),
                "--:--",
                5,
                "0 字",
                "0 字",
                f"大纲已生成，共{len(outline)}章",
                ""
            )

            # 2. 创建项目
            project_data = {
                "id": project_id,
                "title": title,
                "genre": genre,
                "character_setting": character_setting,
                "world_setting": world_setting,
                "plot_idea": plot_idea,
                "chapter_count": len(outline),
                "chapters": [],
                "outline": outline,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            project_file = app_state.project_dir / f"{project_id}.json"
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)

            progress_text += f"✓ 项目创建成功 (ID: {project_id})\n\n"

            yield (
                progress_text,
                "10%",
                "0 / " + str(len(outline)),
                "--:--",
                10,
                "0 字",
                "0 字",
                f"项目已创建，开始生成章节...",
                ""
            )

            # 3. 开始生成章节
            progress_text += f"📖 开始生成章节...\n"

            # 用于统计
            start_time = datetime.now()
            total_words = 0
            chapter_word_counts = []

            # 使用自定义的进度回调
            def progress_callback(current, total, message):
                nonlocal progress_text, total_words, chapter_word_counts
                progress_text += f"  [{current}/{total}] {message}\n"
                logger.info(f"生成进度: {current}/{total} - {message}")

            success, message, all_chapters = generator.generate_full_novel(
                project_id,
                outline,
                start_chapter=1,
                progress_callback=progress_callback
            )

            progress_text += f"\n{'✓' if success else '⚠️'} {message}\n"

            if success:
                progress_text += f"\n🎉 小说生成完成！\n"
                progress_text += f"总章节数: {len(all_chapters)}\n"
                total_words = sum(ch.get('word_count', 0) for ch in all_chapters)
                avg_words = int(total_words / len(all_chapters)) if all_chapters else 0
                progress_text += f"总字数: {total_words:,}\n"
                progress_text += f"项目ID: {project_id}\n"
                result_message = f"成功生成 {len(all_chapters)} 章，共 {total_words:,} 字"

                yield (
                    progress_text,
                    "100%",
                    f"{len(all_chapters)} / {len(all_chapters)}",
                    "00:00",
                    100,
                    f"{total_words:,} 字",
                    f"{avg_words} 字",
                    result_message,
                    project_id
                )
            else:
                progress_text += f"\n⚠️ 生成未完成，已生成 {len(all_chapters)} 章\n"
                progress_text += f"您可以稍后继续生成\n"
                result_message = f"生成了 {len(all_chapters)} 章"
                total_words = sum(ch.get('word_count', 0) for ch in all_chapters)
                avg_words = int(total_words / len(all_chapters)) if all_chapters else 0
                percentage = (len(all_chapters) / len(outline) * 100) if outline else 0

                yield (
                    progress_text,
                    f"{percentage:.1f}%",
                    f"{len(all_chapters)} / {len(outline)}",
                    "--:--",
                    percentage,
                    f"{total_words:,} 字",
                    f"{avg_words} 字" if avg_words > 0 else "0 字",
                    result_message,
                    project_id
                )

        except Exception as e:
            logger.error(f"生成失败: {e}")
            yield (
                f"❌ 生成失败: {str(e)}",
                "0%",
                "- / -",
                "--:--",
                0,
                "0 字",
                "0 字",
                "生成失败",
                ""
            )

    def on_pause_continue_toggle(is_paused: bool):
        """
        暂停/继续切换

        Args:
            is_paused: 是否已暂停

        Returns:
            (新按钮文本, 新状态消息, 新is_paused)
        """
        if is_paused:
            # 当前是暂停状态，点击后继续
            generator.resume_generation()
            logger.info("用户点击继续生成")
            return "⏸️ 暂停", "▶️ 已继续生成", False
        else:
            # 当前是生成状态，点击后暂停
            generator.pause_generation()
            logger.info("用户点击暂停生成")
            return "▶️ 继续", "⏸️ 已暂停生成（可点击继续恢复）", True

    def on_stop_generation():
        """
        停止生成（终止，不可继续）

        Returns:
            状态消息
        """
        generator.stop_generation()
        logger.info("用户点击停止生成")
        return "⏹️ 已停止生成（如需继续，请使用「✍️ 继续生成」按钮）"

    def on_load_project(selected_value: str):
        """
        加载项目并填充表单

        Args:
            selected_value: Dropdown的值，格式为"project_id"
        """
        if not selected_value or not selected_value.strip():
            return (
                "❌ 请选择一个项目",
                gr.update(value=""),  # title
                gr.update(value=""),  # genre
                gr.update(value=""),  # character_setting
                gr.update(value=""),  # world_setting
                gr.update(value=""),  # plot_idea
                gr.update(value=50),  # chapter_count
                "",                   # project_id (for internal tracking)
                ""                    # auto_result
            )

        # selected_value就是project_id
        project_id = selected_value.strip()

        try:
            # 导入ProjectManager
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
            from project_manager import ProjectManager

            # 使用project_id获取项目（推荐方式）
            project = ProjectManager.get_project(project_id)
            if not project:
                return (
                    f"❌ 项目不存在 (ID: {project_id})",
                    gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(value=50),
                    "",  # project_id
                    ""   # auto_result
                )

            chapters = project.get("chapters", [])
            total_chapters = project.get("chapter_count", 50)
            project_title = project.get("title", "")
            project_id_from_file = project["id"]

            # 统计已完成的章节数
            completed_count = sum(1 for ch in chapters if ch.get("content", "").strip())

            info = f"""📖 项目: {project_title}
📚 类型: {project.get('genre', '')}
📊 总章节数: {total_chapters} 章
✅ 已完成: {completed_count} 章
⏳ 待生成: {total_chapters - completed_count} 章
📊 创建时间: {project.get('created_at', '')[:19]}
🔄 项目ID: {project_id_from_file}"""

            if completed_count >= total_chapters:
                info += "\n\n✅ 该项目已完成！"
            else:
                info += f"\n\n💡 表单已自动填充，请点击下方的「✍️ 继续生成」按钮从第 {completed_count + 1} 章开始继续生成"

            # 返回：信息 + 填充的表单字段 + project_id + 清空旧结果
            return (
                info,
                gr.update(value=project_title),                             # title
                gr.update(value=project.get("genre", "")),                     # genre
                gr.update(value=project.get("character_setting", "")),         # character_setting
                gr.update(value=project.get("world_setting", "")),             # world_setting
                gr.update(value=project.get("plot_idea", "")),                  # plot_idea
                gr.update(value=total_chapters),                                # chapter_count
                project_id_from_file,                                           # project_id
                ""                                                              # 清空生成结果
            )

        except Exception as e:
            logger.error(f"加载项目失败: {e}")
            return (
                f"❌ 加载项目失败: {str(e)}",
                gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(value=50),
                "",  # project_id
                ""   # auto_result
            )

    def on_continue_generation(
        title,
        genre,
        chapter_count,
        character_setting,
        world_setting,
        plot_idea,
        use_coherence,
        loaded_project_id  # 当前加载的项目ID（如果有）
    ):
        """继续生成已有项目"""
        # 优先使用loaded_project_id，否则通过标题查找
        project_id = None
        if loaded_project_id:
            project_id = loaded_project_id
            logger.info(f"使用加载的项目ID: {project_id}")

        if not project_id and not title:
            yield (
                "❌ 请先选择一个项目",
                "0%", "- / -", "--:--", 0,
                "0 字", "0 字", "请先选择项目", ""
            )
            return

        try:
            # 导入ProjectManager
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
            from project_manager import ProjectManager

            # 使用project_id获取项目（优先），或通过标题查找
            if project_id:
                project = ProjectManager.get_project(project_id)
                logger.info(f"通过ID获取项目: {project_id}")
            elif title:
                project = ProjectManager.get_project_by_title(title)
                if project:
                    project_id = project["id"]
                    logger.info(f"通过标题获取项目，ID: {project_id}")

            if not project:
                yield (
                    f"❌ 项目不存在 (ID: {project_id or title})",
                    "0%", "- / -", "--:--", 0,
                    "0 字", "0 字", "项目不存在", ""
                )
                return

            chapters = project.get("chapters", [])
            outline = project.get("outline", [])
            total_chapters = project.get("chapter_count", len(outline) if outline else 50)
            project_id = project["id"]  # 确保使用正确的project_id

            # 统计已完成的章节数
            completed_count = sum(1 for ch in chapters if ch.get("content", "").strip())

            logger.info(f"项目续写信息: ID={project_id}, 已完成={completed_count}, 总数={total_chapters}, 文件中章节数={len(chapters)}")

            # 正确判断：比较已完成章节数与项目总章节数
            if completed_count >= total_chapters:
                yield (
                    f"✅ 项目'{title}' 已经完成！所有 {total_chapters} 章都已生成。",
                    "100%", f"{completed_count} / {total_chapters}", "00:00", 100,
                    f"{sum(ch.get('word_count', 0) for ch in chapters):,} 字",
                    f"{int(sum(ch.get('word_count', 0) for ch in chapters) / completed_count)} 字" if completed_count > 0 else "0 字",
                    "项目已完成", project_id
                )
                return

            # 如果没有outline，需要先生成
            if not outline:
                yield (
                    f"⚠️ 项目缺少大纲，正在生成大纲...",
                    "0%", "0 / 0", "--:--", 0,
                    "0 字", "0 字", "正在生成大纲...", ""
                )

                success, message, outline = generator.generate_outline(
                    title,
                    genre,
                    character_setting,
                    world_setting,
                    plot_idea,
                    int(chapter_count)
                )

                if not success:
                    yield (
                        f"❌ 大纲生成失败: {message}",
                        "0%", "- / -", "--:--", 0,
                        "0 字", "0 字", "大纲生成失败", ""
                    )
                    return

                # 更新项目大纲
                project["outline"] = outline
                ProjectManager.save_project(project_id, project)

            # 计算起始章节
            start_chapter = completed_count + 1
            # 使用项目配置的总章节数，而不是outline的长度
            total_to_generate = total_chapters

            yield (
                f"📖 继续生成项目: {title}\n"
                f"✓ 已完成 {completed_count} 章\n"
                f"📝 从第 {start_chapter} 章开始继续生成\n"
                f"📊 总共 {total_to_generate} 章，还需生成 {total_to_generate - completed_count} 章\n\n",
                f"{int(completed_count / total_to_generate * 100)}%",
                f"{completed_count} / {total_to_generate}",
                "--:--",
                int(completed_count / total_to_generate * 100),
                f"{sum(ch.get('word_count', 0) for ch in chapters):,} 字",
                f"{int(sum(ch.get('word_count', 0) for ch in chapters) / completed_count)} 字" if completed_count > 0 else "0 字",
                f"继续从第 {start_chapter} 章开始生成...",
                ""
            )

            # 用于统计
            progress_text = f"📖 开始从第 {start_chapter} 章继续生成...\n"

            def progress_callback(current, total, message):
                nonlocal progress_text
                progress_text += f"  [{current}/{total}] {message}\n"
                logger.info(f"生成进度: {current}/{total} - {message}")

            # 继续生成 - 传递已有的章节作为上下文
            # generate_full_novel会自动保存完整章节到文件
            success, message, returned_chapters = generator.generate_full_novel(
                project_id,
                outline,
                start_chapter=start_chapter,
                progress_callback=progress_callback,
                existing_chapters=chapters  # 传递已有的所有章节作为上下文和基础
            )

            progress_text += f"\n{'✓' if success else '⚠️'} {message}\n"

            # 注意：returned_chapters已经是完整的章节列表（包含已有+新生成的）
            # generate_full_novel内部已经保存到文件了
            all_chapters = returned_chapters
            total_words = sum(ch.get('word_count', 0) for ch in all_chapters)
            avg_words = int(total_words / len(all_chapters)) if all_chapters else 0

            if success:
                progress_text += f"\n🎉 继续生成完成！\n"
                new_chapters_count = len(all_chapters) - completed_count
                progress_text += f"本次生成: {new_chapters_count} 章\n"
                progress_text += f"总计完成: {len(all_chapters)} / {total_to_generate} 章\n"
                progress_text += f"总字数: {total_words:,}\n"

                yield (
                    progress_text,
                    f"{int(len(all_chapters) / total_to_generate * 100)}%",
                    f"{len(all_chapters)} / {total_to_generate}",
                    "00:00",
                    int(len(all_chapters) / total_to_generate * 100),
                    f"{total_words:,} 字",
                    f"{avg_words} 字",
                    f"成功生成 {new_chapters_count} 章，共 {sum(ch.get('word_count', 0) for ch in all_chapters[completed_count:]) if completed_count < len(all_chapters) else 0:,} 字",
                    project_id
                )
            else:
                new_chapters_count = len(all_chapters) - completed_count
                progress_text += f"\n⚠️ 生成未完成，本次生成了 {new_chapters_count} 章\n"
                yield (
                    progress_text,
                    f"{int(len(all_chapters) / total_to_generate * 100)}%",
                    f"{len(all_chapters)} / {total_to_generate}",
                    "--:--",
                    int(len(all_chapters) / total_to_generate * 100),
                    f"{total_words:,} 字",
                    f"{avg_words} 字" if avg_words > 0 else "0 字",
                    f"生成了 {new_chapters_count} 章",
                    project_id
                )

        except Exception as e:
            logger.error(f"继续生成失败: {e}", exc_info=True)
            yield (
                f"❌ 继续生成失败: {str(e)}",
                "0%", "- / -", "--:--", 0,
                "0 字", "0 字", "继续生成失败", ""
            )

    # 绑定事件
    auto_generate_btn.click(
        fn=on_start_generation,
        inputs=[
            auto_title,
            auto_genre,
            auto_chapter_count,
            auto_character_setting,
            auto_world_setting,
            auto_plot_idea,
            auto_use_coherence,
            # 新增：质量控制参数
            auto_ai_taste_level,
            auto_enable_quality,
            auto_quality_min_score,
            auto_quality_rewrite_threshold,
            auto_enable_auto_rewrite,
            auto_max_rewrite_attempts
        ],
        outputs=[
            progress_box,          # 生成日志
            progress_percentage,   # 完成度百分比
            progress_current,      # 当前章节
            progress_eta,          # 预计剩余时间
            progress_bar_slider,   # 进度条
            total_words_generated, # 已生成总字数
            avg_words_per_chapter, # 平均章节字数
            auto_result,           # 生成结果
            gr.State()             # project_id (内部状态)
        ]
    )

    # ========== 控制按钮事件 ==========
    # 暂停/继续切换按钮
    auto_pause_continue_btn.click(
        fn=on_pause_continue_toggle,
        inputs=[is_paused],
        outputs=[
            auto_pause_continue_btn,  # 更新按钮文本
            progress_box,              # 显示状态消息
            is_paused                  # 更新暂停状态
        ]
    )

    # 停止按钮
    auto_stop_btn.click(
        fn=on_stop_generation,
        outputs=[progress_box]
    )

    # ========== 项目加载事件 ==========
    # 项目选择变化时显示信息并填充表单
    auto_load_project_select.change(
        fn=on_load_project,
        inputs=[auto_load_project_select],
        outputs=[
            auto_load_project_info,     # 显示信息
            auto_title,                  # 填充标题
            auto_genre,                  # 填充类型
            auto_character_setting,      # 填充角色设定
            auto_world_setting,          # 填充世界观
            auto_plot_idea,              # 填充剧情构思
            auto_chapter_count,          # 填充章节数
            loaded_project_id,           # 保存project_id到状态
            auto_result                  # 清空旧的生成结果
        ]
    )

    # 加载项目按钮 - 点击时也触发相同的加载逻辑
    auto_load_btn.click(
        fn=on_load_project,
        inputs=[auto_load_project_select],
        outputs=[
            auto_load_project_info,     # 显示信息
            auto_title,                  # 填充标题
            auto_genre,                  # 填充类型
            auto_character_setting,      # 填充角色设定
            auto_world_setting,          # 填充世界观
            auto_plot_idea,              # 填充剧情构思
            auto_chapter_count,          # 填充章节数
            loaded_project_id,           # 保存project_id到状态
            auto_result                  # 清空旧的生成结果
        ]
    )

    # 继续生成按钮 - 从已有项目继续生成
    auto_continue_btn.click(
        fn=on_continue_generation,
        inputs=[
            auto_title,
            auto_genre,
            auto_chapter_count,
            auto_character_setting,
            auto_world_setting,
            auto_plot_idea,
            auto_use_coherence,
            loaded_project_id
        ],
        outputs=[
            progress_box,          # 生成日志
            progress_percentage,   # 完成度百分比
            progress_current,      # 当前章节
            progress_eta,          # 预计剩余时间
            progress_bar_slider,   # 进度条
            total_words_generated, # 已生成总字数
            avg_words_per_chapter, # 平均章节字数
            auto_result,           # 生成结果
            loaded_project_id      # 返回project_id
        ]
    )

    # 暂停/继续切换按钮
    auto_pause_continue_btn.click(
        fn=on_pause_continue_toggle,
        inputs=[is_paused],
        outputs=[
            auto_pause_continue_btn,  # 更新按钮文本
            progress_box,              # 显示状态消息
            is_paused                  # 更新暂停状态
        ]
    )

    # 停止按钮
    auto_stop_btn.click(
        fn=on_stop_generation,
        outputs=[progress_box]
    )

    return {
        "auto_title": auto_title,
        "auto_genre": auto_genre,
        "auto_chapter_count": auto_chapter_count,
        "auto_character_setting": auto_character_setting,
        "auto_world_setting": auto_world_setting,
        "auto_plot_idea": auto_plot_idea,
        "auto_use_coherence": auto_use_coherence,
        "progress_box": progress_box,
        "auto_result": auto_result,
        "auto_load_project_select": auto_load_project_select,
        "auto_load_project_info": auto_load_project_info,
        "loaded_project_id": loaded_project_id,
        "auto_pause_continue_btn": auto_pause_continue_btn
    }
