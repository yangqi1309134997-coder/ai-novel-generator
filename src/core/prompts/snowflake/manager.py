"""
雪花写作法管理器
管理整个雪花写作法的生成流程

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from . import (
    generate_core_seed_prompt,
    generate_character_dynamics_prompt,
    generate_world_building_prompt,
    generate_plot_architecture_prompt,
    generate_character_state_prompt,
    generate_chapter_blueprint_prompt,
    generate_chunked_chapter_blueprint_prompt,
)

logger = logging.getLogger(__name__)


@dataclass
class SnowflakeArchitecture:
    """雪花架构数据"""
    core_seed: str = ""
    character_dynamics: str = ""
    world_building: str = ""
    plot_architecture: str = ""
    character_state: str = ""
    chapter_blueprint: str = ""

    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {
            'core_seed': self.core_seed,
            'character_dynamics': self.character_dynamics,
            'world_building': self.world_building,
            'plot_architecture': self.plot_architecture,
            'character_state': self.character_state,
            'chapter_blueprint': self.chapter_blueprint,
        }

    def is_complete(self) -> bool:
        """检查架构是否完整"""
        return bool(
            self.core_seed and
            self.character_dynamics and
            self.world_building and
            self.plot_architecture
        )


@dataclass
class SnowflakeConfig:
    """雪花写作法配置"""
    topic: str = ""
    genre: str = "通用"
    number_of_chapters: int = 50
    word_number: int = 3000
    user_guidance: str = ""

    # 生成参数
    temperature: float = 0.7
    max_tokens: int = 4096

    # 分块生成配置
    enable_chunked: bool = True
    chunk_size: Optional[int] = None  # None表示自动计算


class SnowflakeManager:
    """雪花写作法管理器"""

    def __init__(self, api_client):
        """
        初始化雪花写作法管理器

        Args:
            api_client: API客户端
        """
        self.api_client = api_client

    def generate_architecture(
        self,
        config: SnowflakeConfig,
        on_progress: Optional[callable] = None
    ) -> Tuple[bool, str, SnowflakeArchitecture]:
        """
        生成完整的小说架构

        Args:
            config: 雪花写作法配置
            on_progress: 进度回调函数

        Returns:
            (成功标志, 消息, 架构数据)
        """
        try:
            logger.info("[雪花写作法] 开始生成架构...")
            architecture = SnowflakeArchitecture()

            # 步骤1: 核心种子
            if not architecture.core_seed:
                if on_progress:
                    on_progress('正在生成核心种子...', 1, 5)
                architecture.core_seed = self._generate_core_seed(config)
                logger.info("[雪花写作法] 核心种子生成完成")

            # 步骤2: 角色动力学
            if not architecture.character_dynamics:
                if on_progress:
                    on_progress('正在生成角色体系...', 2, 5)
                architecture.character_dynamics = self._generate_character_dynamics(
                    config, architecture.core_seed
                )
                logger.info("[雪花写作法] 角色体系生成完成")

            # 步骤2.5: 角色状态
            if not architecture.character_state and architecture.character_dynamics:
                if on_progress:
                    on_progress('正在生成角色状态...', 2.5, 5)
                architecture.character_state = self._generate_character_state(
                    architecture.character_dynamics
                )
                logger.info("[雪花写作法] 角色状态生成完成")

            # 步骤3: 世界观
            if not architecture.world_building:
                if on_progress:
                    on_progress('正在构建世界观...', 3, 5)
                architecture.world_building = self._generate_world_building(
                    config, architecture.core_seed
                )
                logger.info("[雪花写作法] 世界观生成完成")

            # 步骤4: 情节架构
            if not architecture.plot_architecture:
                if on_progress:
                    on_progress('正在设计情节架构...', 4, 5)
                architecture.plot_architecture = self._generate_plot_architecture(
                    config,
                    architecture.core_seed,
                    architecture.character_dynamics,
                    architecture.world_building
                )
                logger.info("[雪花写作法] 情节架构生成完成")

            if on_progress:
                on_progress('架构生成完成!', 5, 5)

            return True, "架构生成成功", architecture

        except Exception as e:
            logger.error(f"[雪花写作法] 架构生成失败: {e}", exc_info=True)
            return False, f"架构生成失败: {str(e)}", SnowflakeArchitecture()

    def generate_chapter_blueprint(
        self,
        config: SnowflakeConfig,
        architecture: SnowflakeArchitecture,
        existing_blueprint: str = "",
        on_progress: Optional[callable] = None
    ) -> Tuple[bool, str, str]:
        """
        生成章节蓝图

        Args:
            config: 雪花写作法配置
            architecture: 架构数据
            existing_blueprint: 已有的章节蓝图
            on_progress: 进度回调函数

        Returns:
            (成功标志, 消息, 章节蓝图)
        """
        try:
            logger.info(f"[雪花写作法] 开始生成章节蓝图...")

            # 构建小说架构文本
            novel_architecture_text = self._build_novel_architecture_text(
                config, architecture
            )

            # 计算分块大小
            chunk_size = self._calculate_chunk_size(
                config.number_of_chapters,
                config.max_tokens,
                config.chunk_size
            )

            # 解析已有章节
            existing_chapters = self._parse_existing_chapters(existing_blueprint)
            max_existing_chapter = max(existing_chapters) if existing_chapters else 0

            logger.info(f"[雪花写作法] 已有{max_existing_chapter}章，分块大小={chunk_size}")

            # 如果已有蓝图，继续生成
            if existing_blueprint and max_existing_chapter > 0:
                blueprint = existing_blueprint
                current_start = max_existing_chapter + 1

                while current_start <= config.number_of_chapters:
                    current_end = min(current_start + chunk_size - 1, config.number_of_chapters)

                    if on_progress:
                        on_progress(
                            f'正在生成章节大纲 ({current_start}-{current_end})...',
                            current_start - 1,
                            config.number_of_chapters
                        )

                    # 限制已有蓝图到最近100章
                    limited_blueprint = self._limit_blueprint(blueprint, 100)

                    chunk_result = self._generate_chunked_blueprint(
                        config,
                        novel_architecture_text,
                        limited_blueprint,
                        current_start,
                        current_end
                    )

                    if chunk_result:
                        blueprint = f"{blueprint}\n\n{chunk_result}"
                    else:
                        logger.warning(f"[雪花写作法] 分块生成失败: {current_start}-{current_end}")

                    current_start = current_end + 1

                return True, "章节蓝图生成完成", blueprint

            # 没有已有蓝图，从头生成
            else:
                # 如果章节不多，一次性生成
                if chunk_size >= config.number_of_chapters:
                    if on_progress:
                        on_progress(
                            f'正在生成章节大纲 (1-{config.number_of_chapters})...',
                            0,
                            1
                        )

                    blueprint = self._generate_full_blueprint(
                        config,
                        novel_architecture_text
                    )

                    if on_progress:
                        on_progress('章节蓝图生成完成!', 1, 1)

                    return True, "章节蓝图生成完成", blueprint

                # 章节较多，分块生成
                else:
                    blueprint = ""
                    current_start = 1

                    while current_start <= config.number_of_chapters:
                        current_end = min(current_start + chunk_size - 1, config.number_of_chapters)

                        if on_progress:
                            on_progress(
                                f'正在生成章节大纲 ({current_start}-{current_end})...',
                                current_start - 1,
                                config.number_of_chapters
                            )

                        limited_blueprint = self._limit_blueprint(blueprint, 100)

                        chunk_result = self._generate_chunked_blueprint(
                            config,
                            novel_architecture_text,
                            limited_blueprint,
                            current_start,
                            current_end
                        )

                        if chunk_result:
                            blueprint = f"{blueprint}\n\n{chunk_result}" if blueprint else chunk_result

                        current_start = current_end + 1

                    if on_progress:
                        on_progress('章节蓝图生成完成!', config.number_of_chapters, config.number_of_chapters)

                    return True, "章节蓝图生成完成", blueprint

        except Exception as e:
            logger.error(f"[雪花写作法] 章节蓝图生成失败: {e}", exc_info=True)
            return False, f"章节蓝图生成失败: {str(e)}", ""

    # ========== 私有方法 ==========

    def _generate_core_seed(self, config: SnowflakeConfig) -> str:
        """生成核心种子"""
        prompt = generate_core_seed_prompt({
            'topic': config.topic,
            'genre': config.genre,
            'number_of_chapters': config.number_of_chapters,
            'word_number': config.word_number,
            'user_guidance': config.user_guidance,
        })

        return self._call_api(prompt, config.temperature, config.max_tokens)

    def _generate_character_dynamics(
        self,
        config: SnowflakeConfig,
        core_seed: str
    ) -> str:
        """生成角色动力学"""
        prompt = generate_character_dynamics_prompt({
            'genre': config.genre,
            'core_seed': core_seed,
            'user_guidance': config.user_guidance,
        })

        return self._call_api(prompt, config.temperature, config.max_tokens)

    def _generate_character_state(self, character_dynamics: str) -> str:
        """生成角色状态"""
        prompt = generate_character_state_prompt({
            'character_dynamics': character_dynamics,
        })

        return self._call_api(prompt, 0.5, 3000)

    def _generate_world_building(
        self,
        config: SnowflakeConfig,
        core_seed: str
    ) -> str:
        """生成世界观"""
        prompt = generate_world_building_prompt({
            'genre': config.genre,
            'core_seed': core_seed,
            'user_guidance': config.user_guidance,
        })

        return self._call_api(prompt, config.temperature, config.max_tokens)

    def _generate_plot_architecture(
        self,
        config: SnowflakeConfig,
        core_seed: str,
        character_dynamics: str,
        world_building: str
    ) -> str:
        """生成情节架构"""
        prompt = generate_plot_architecture_prompt({
            'genre': config.genre,
            'core_seed': core_seed,
            'character_dynamics': character_dynamics,
            'world_building': world_building,
            'user_guidance': config.user_guidance,
        })

        return self._call_api(prompt, config.temperature, config.max_tokens)

    def _generate_full_blueprint(
        self,
        config: SnowflakeConfig,
        novel_architecture: str
    ) -> str:
        """生成完整的章节蓝图"""
        prompt = generate_chapter_blueprint_prompt({
            'novel_architecture': novel_architecture,
            'number_of_chapters': config.number_of_chapters,
            'user_guidance': config.user_guidance,
        })

        return self._call_api(prompt, config.temperature, config.max_tokens)

    def _generate_chunked_blueprint(
        self,
        config: SnowflakeConfig,
        novel_architecture: str,
        chapter_list: str,
        start_chapter: int,
        end_chapter: int
    ) -> str:
        """生成分块章节蓝图"""
        prompt = generate_chunked_chapter_blueprint_prompt({
            'novel_architecture': novel_architecture,
            'chapter_list': chapter_list,
            'number_of_chapters': config.number_of_chapters,
            'start_chapter': start_chapter,
            'end_chapter': end_chapter,
            'user_guidance': config.user_guidance,
        })

        return self._call_api(prompt, config.temperature, config.max_tokens)

    def _build_novel_architecture_text(
        self,
        config: SnowflakeConfig,
        architecture: SnowflakeArchitecture
    ) -> str:
        """构建小说架构文本"""
        return f"""#=== 0) 小说设定 ===
主题：{config.topic}，类型：{config.genre}，篇幅：约{config.number_of_chapters}章（每章{config.word_number}字）

#=== 1) 核心种子 ===
{architecture.core_seed}

#=== 2) 角色动力学 ===
{architecture.character_dynamics}

#=== 3) 世界观 ===
{architecture.world_building}

#=== 4) 三幕式情节架构 ===
{architecture.plot_architecture}"""

    def _calculate_chunk_size(
        self,
        number_of_chapters: int,
        max_tokens: int,
        manual_chunk_size: Optional[int] = None
    ) -> int:
        """计算分块大小"""
        if manual_chunk_size:
            return min(manual_chunk_size, number_of_chapters)

        # 基于每章200 tokens估算
        tokens_per_chapter = 200.0
        ratio = max_tokens / tokens_per_chapter
        chunk_size = int(ratio // 10) * 10 - 10

        if chunk_size < 1:
            chunk_size = 1
        if chunk_size > number_of_chapters:
            chunk_size = number_of_chapters

        return chunk_size

    def _parse_existing_chapters(self, blueprint: str) -> List[int]:
        """解析已有章节号"""
        import re
        pattern = r"第\s*(\d+)\s*章"
        matches = re.findall(pattern, blueprint)
        return [int(m) for m in matches if m.isdigit()]

    def _limit_blueprint(self, blueprint: str, limit: int) -> str:
        """限制蓝图到最近N章"""
        import re

        if not blueprint:
            return ""

        pattern = r"(第\s*\d+\s*章.*?)(?=第\s*\d+\s*章|$)"
        chapters = re.findall(pattern, blueprint, flags=re.DOTALL)

        if len(chapters) <= limit:
            return blueprint

        return "\n\n".join(chapters[-limit:]).strip()

    def _call_api(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """调用API"""
        try:
            messages = [
                {"role": "system", "content": "你是一位专业的小说作家，精通各种题材的创作。"},
                {"role": "user", "content": prompt}
            ]

            result = self.api_client.generate(
                messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return result.strip() if result else ""

        except Exception as e:
            logger.error(f"[雪花写作法] API调用失败: {e}")
            raise


# 便捷函数
def create_snowflake_manager(api_client) -> SnowflakeManager:
    """创建雪花写作法管理器"""
    return SnowflakeManager(api_client)
