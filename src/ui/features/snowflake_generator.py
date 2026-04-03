"""
雪花写作法生成器UI
整合雪花写作法到Gradio界面，与现有系统完全集成

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import gradio as gr
import logging
from typing import Tuple, Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class SnowflakeGeneratorUI:
    """雪花写作法生成器UI - 与现有系统集成"""

    def __init__(self, api_client, project_manager, auto_generator=None, coherence_system=None):
        """
        初始化雪花写作法UI

        Args:
            api_client: API客户端
            project_manager: 项目管理器
            auto_generator: 自动生成器实例（可选，用于章节生成）
            coherence_system: 连贯性系统（可选）
        """
        self.api_client = api_client
        self.project_manager = project_manager
        self.auto_generator = auto_generator
        self.coherence_system = coherence_system

        # 延迟导入雪花写作法模块
        from src.core.prompts.snowflake import (
            SnowflakeManager,
            SnowflakeConfig,
            create_snowflake_manager,
            parse_chapter_blueprint,
        )

        self.SnowflakeManager = SnowflakeManager
        self.SnowflakeConfig = SnowflakeConfig
        self.create_snowflake_manager = create_snowflake_manager
        self.parse_chapter_blueprint = parse_chapter_blueprint

        # 当前状态
        self.current_architecture = None
        self.current_blueprint = ""
        self.snowflake_manager = None
        self.current_config = None  # 保存当前配置
        self.current_project_id = None  # 当前项目ID

        # 生成控制
        self.is_generating = False
        self.should_stop = False

    def set_auto_generator(self, auto_generator):
        """设置自动生成器"""
        self.auto_generator = auto_generator

    def set_coherence_system(self, coherence_system):
        """设置连贯性系统"""
        self.coherence_system = coherence_system

    def create_ui(self) -> gr.Blocks:
        """创建雪花写作法UI"""
        with gr.Blocks() as snowflake_ui:
            gr.Markdown("## ❄️ 雪花写作法生成器")
            gr.Markdown("基于雪花写作法的智能小说生成系统，从核心种子到完整章节。完全集成连贯性系统、上下文机制和缓存系统。")

            with gr.Tab("步骤1: 基础设置"):
                with gr.Row():
                    with gr.Column(scale=1):
                        topic_input = gr.Textbox(
                            label="小说主题",
                            placeholder="例如：一个被遗忘的剑客，在江湖中寻找失落的记忆",
                            lines=2
                        )
                        genre_input = gr.Dropdown(
                            label="小说类型",
                            choices=[
                                "玄幻", "仙侠", "武侠", "都市", "言情",
                                "悬疑", "科幻", "历史", "军事", "灵异", "其他",
                            ],
                            value="玄幻"
                        )
                    with gr.Column(scale=1):
                        chapter_count_input = gr.Slider(
                            label="章节数量",
                            minimum=10,
                            maximum=5000,  # 支持5000章节
                            value=100,
                            step=10
                        )
                        word_count_input = gr.Slider(
                            label="每章字数",
                            minimum=1000,
                            maximum=10000,
                            value=3000,
                            step=500
                        )

                user_guidance_input = gr.Textbox(
                    label="用户指导（可选）",
                    placeholder="例如：偏向古龙风格，要有江湖气",
                    lines=2
                )

                with gr.Row():
                    generate_arch_btn = gr.Button("🚀 生成小说架构", variant="primary")
                    clear_btn = gr.Button("🗑️ 清空", variant="secondary")

            with gr.Tab("步骤2: 架构预览"):
                architecture_output = gr.Markdown(label="生成结果")

                with gr.Row():
                    core_seed_output = gr.Textbox(label="核心种子", lines=3)
                    character_output = gr.Textbox(label="角色动力学", lines=5)
                with gr.Row():
                    world_output = gr.Textbox(label="世界观", lines=5)
                    plot_output = gr.Textbox(label="情节架构", lines=5)
                with gr.Row():
                    character_state_output = gr.Textbox(label="角色状态", lines=5)

                generate_blueprint_btn = gr.Button("📋 生成章节蓝图", variant="primary")

            with gr.Tab("步骤3: 章节蓝图"):
                blueprint_output = gr.Textbox(
                    label="章节蓝图",
                    lines=20,
                    placeholder="章节蓝图将在这里显示..."
                )

                with gr.Row():
                    parse_blueprint_btn = gr.Button("🔍 解析蓝图", variant="secondary")
                    export_blueprint_btn = gr.Button("📤 导出蓝图", variant="secondary")

                parsed_chapters_output = gr.Markdown(label="解析结果")

            with gr.Tab("步骤4: 生成小说"):
                gr.Markdown("### 章节生成")
                gr.Markdown("基于生成的架构和蓝图，逐章生成小说内容。使用与自动生成相同的连贯性系统、上下文机制和缓存系统。")

                with gr.Row():
                    start_chapter_input = gr.Number(label="开始章节", value=1, minimum=1, maximum=5000)
                    end_chapter_input = gr.Number(label="结束章节", value=10, minimum=1, maximum=5000)

                # 生成选项
                with gr.Row():
                    use_context_check = gr.Checkbox(label="启用上下文机制", value=True)
                    use_coherence_check = gr.Checkbox(label="启用连贯性系统", value=True)
                    use_cache_check = gr.Checkbox(label="启用缓存", value=True)

                with gr.Row():
                    generate_chapters_btn = gr.Button("✍️ 开始生成章节", variant="primary")
                    stop_generation_btn = gr.Button("⏹️ 停止生成", variant="stop")

                generation_progress = gr.Textbox(label="生成进度", lines=8)
                generation_output = gr.Textbox(label="生成内容", lines=20)

            with gr.Tab("步骤5: 导出"):
                gr.Markdown("### 导出小说")

                with gr.Row():
                    export_txt_btn = gr.Button("📄 导出为TXT")
                    export_md_btn = gr.Button("📝 导出为Markdown")
                    export_json_btn = gr.Button("📦 导出为JSON")

                export_output = gr.Textbox(label="导出结果", lines=3)

            # ========== 事件绑定 ==========

            # 生成架构
            generate_arch_btn.click(
                fn=self._generate_architecture,
                inputs=[
                    topic_input,
                    genre_input,
                    chapter_count_input,
                    word_count_input,
                    user_guidance_input,
                ],
                outputs=[
                    architecture_output,
                    core_seed_output,
                    character_output,
                    world_output,
                    plot_output,
                    character_state_output,
                ]
            )

            # 生成章节蓝图
            generate_blueprint_btn.click(
                fn=self._generate_blueprint,
                inputs=[],
                outputs=[blueprint_output]
            )

            # 解析蓝图
            parse_blueprint_btn.click(
                fn=self._parse_blueprint,
                inputs=[blueprint_output],
                outputs=[parsed_chapters_output]
            )

            # 生成章节
            generate_chapters_btn.click(
                fn=self._generate_chapters,
                inputs=[
                    start_chapter_input,
                    end_chapter_input,
                    use_context_check,
                    use_coherence_check,
                    use_cache_check,
                ],
                outputs=[
                    generation_progress,
                    generation_output,
                ]
            )

            # 停止生成
            stop_generation_btn.click(
                fn=self._stop_generation,
                inputs=[],
                outputs=[generation_progress]
            )

            # 清空
            clear_btn.click(
                fn=self._clear_all,
                inputs=[],
                outputs=[
                    topic_input,
                    user_guidance_input,
                    architecture_output,
                    core_seed_output,
                    character_output,
                    world_output,
                    plot_output,
                    character_state_output,
                    blueprint_output,
                    parsed_chapters_output,
                    generation_progress,
                    generation_output,
                ]
            )

        return snowflake_ui

    # ========== 事件处理函数 ==========

    def _generate_architecture(
        self,
        topic: str,
        genre: str,
        chapter_count: int,
        word_count: int,
        user_guidance: str
    ) -> Tuple[str, str, str, str, str, str]:
        """生成小说架构"""
        try:
            logger.info(f"[雪花写作法] 开始生成架构: {topic}")

            # 创建配置
            config = self.SnowflakeConfig(
                topic=topic,
                genre=genre,
                number_of_chapters=int(chapter_count),
                word_number=int(word_count),
                user_guidance=user_guidance,
            )

            # 保存配置供后续使用
            self.current_config = config

            # 创建管理器
            self.snowflake_manager = self.create_snowflake_manager(self.api_client)

            # 生成架构
            success, message, architecture = self.snowflake_manager.generate_architecture(
                config,
                on_progress=lambda msg, step, total: logger.info(f"[{step}/{total}] {msg}")
            )

            if not success:
                return f"❌ 生成失败: {message}", "", "", "", "", ""

            # 保存架构
            self.current_architecture = architecture

            # 创建项目ID
            self.current_project_id = f"snowflake_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 构建输出
            architecture_text = f"""## 架构生成完成

✅ **核心种子**: 已生成 ({len(architecture.core_seed)} 字)
✅ **角色动力学**: 已生成 ({len(architecture.character_dynamics)} 字)
✅ **世界观**: 已生成 ({len(architecture.world_building)} 字)
✅ **情节架构**: 已生成 ({len(architecture.plot_architecture)} 字)
✅ **角色状态**: 已生成 ({len(architecture.character_state or '')} 字)

**项目ID**: {self.current_project_id}
**章节数**: {chapter_count}

---

### 下一步
点击 "生成章节蓝图" 继续...
"""

            return (
                architecture_text,
                architecture.core_seed,
                architecture.character_dynamics,
                architecture.world_building,
                architecture.plot_architecture,
                architecture.character_state or "",
            )

        except Exception as e:
            logger.error(f"[雪花写作法] 架构生成失败: {e}", exc_info=True)
            error_msg = f"❌ 生成失败: {str(e)}\n\n请检查:\n1. API配置是否正确\n2. 网络连接是否正常\n3. API额度是否充足"
            return error_msg, "", "", "", "", ""

    def _generate_blueprint(self) -> str:
        """生成章节蓝图"""
        try:
            if not self.current_architecture:
                return "❌ 请先生成小说架构"

            logger.info("[雪花写作法] 开始生成章节蓝图")

            # 使用保存的配置，如果没有则使用默认值
            if self.current_config:
                config = self.current_config
            else:
                config = self.SnowflakeConfig(
                    number_of_chapters=50,  # 默认值
                )
                logger.warning("[雪花写作法] 未找到保存的配置，使用默认章节数: 50")

            success, message, blueprint = self.snowflake_manager.generate_chapter_blueprint(
                config,
                self.current_architecture,
                existing_blueprint="",
                on_progress=lambda msg, step, total: logger.info(f"[{step}/{total}] {msg}")
            )

            if not success:
                return f"❌ 生成失败: {message}"

            self.current_blueprint = blueprint

            # 统计章节数
            chapters = self.parse_chapter_blueprint(blueprint)
            chapter_count = len(chapters) if chapters else 0

            return f"✅ 章节蓝图生成完成! 共 {chapter_count} 章\n\n{blueprint}"

        except Exception as e:
            logger.error(f"[雪花写作法] 蓝图生成失败: {e}", exc_info=True)
            return f"❌ 生成失败: {str(e)}"

    def _parse_blueprint(self, blueprint: str) -> str:
        """解析章节蓝图"""
        try:
            chapters = self.parse_chapter_blueprint(blueprint)

            if not chapters:
                return "❌ 未解析到章节信息"

            result = f"## 解析到 {len(chapters)} 个章节\n\n"

            for chapter in chapters[:10]:  # 只显示前10章
                result += f"""### 第{chapter.number}章: {chapter.title}

- **定位**: {chapter.position}
- **作用**: {chapter.purpose}
- **悬念**: {chapter.suspense}
- **伏笔**: {chapter.foreshadowing}
- **张力**: {chapter.twist_level}
- **简述**: {chapter.summary}

---

"""

            if len(chapters) > 10:
                result += f"\n... 还有 {len(chapters) - 10} 章"

            return result

        except Exception as e:
            logger.error(f"[雪花写作法] 蓝图解析失败: {e}", exc_info=True)
            return f"❌ 解析失败: {str(e)}"

    def _generate_chapters(
        self,
        start_chapter: int,
        end_chapter: int,
        use_context: bool,
        use_coherence: bool,
        use_cache: bool,
    ) -> Tuple[str, str]:
        """生成章节 - 使用现有系统集成"""
        try:
            if not self.current_architecture:
                return "❌ 请先生成小说架构", ""

            if not self.current_blueprint:
                return "❌ 请先生成章节蓝图", ""

            # 解析章节信息
            chapters = self.parse_chapter_blueprint(self.current_blueprint)
            if not chapters:
                return "❌ 未能解析章节信息", ""

            # 验证章节范围
            start_chapter = int(start_chapter)
            end_chapter = int(end_chapter)
            if start_chapter < 1:
                start_chapter = 1
            if end_chapter > len(chapters):
                end_chapter = len(chapters)
            if start_chapter > end_chapter:
                return "❌ 起始章节不能大于结束章节", ""

            self.is_generating = True
            self.should_stop = False

            logger.info(f"[雪花写作法] 开始生成第 {start_chapter} 到 {end_chapter} 章")

            # 构建小说设定
            novel_setting = f"""【核心种子】
{self.current_architecture.core_seed}

【角色动力学】
{self.current_architecture.character_dynamics}

【世界观】
{self.current_architecture.world_building}

【情节架构】
{self.current_architecture.plot_architecture}

【角色状态】
{self.current_architecture.character_state or '未设置'}
"""

            progress_text = f"开始生成章节 {start_chapter} 到 {end_chapter}...\n"
            all_content = ""
            generated_chapters: List[Dict] = []

            # 读取目标字数配置
            target_words = self.current_config.word_number if self.current_config else 3000

            for i, chapter in enumerate(chapters):
                if self.should_stop:
                    progress_text += "\n⏹️ 生成已停止\n"
                    break

                chapter_num = chapter.number
                if chapter_num < start_chapter or chapter_num > end_chapter:
                    continue

                progress_text += f"\n正在生成第 {chapter_num} 章《{chapter.title}》...\n"

                try:
                    # 构建章节描述
                    chapter_desc = f"""【章节定位】{chapter.position}
【章节作用】{chapter.purpose}
【悬念设置】{chapter.suspense}
【伏笔埋设】{chapter.foreshadowing}
【张力等级】{chapter.twist_level}
【章节简述】{chapter.summary}"""

                    # 获取下一章信息（用于后续章节生成）
                    next_chapter_info = None
                    if i + 1 < len(chapters):
                        next_ch = chapters[i + 1]
                        next_chapter_info = {
                            'number': next_ch.number,
                            'title': next_ch.title,
                            'position': next_ch.position,
                            'purpose': next_ch.purpose,
                            'suspense': next_ch.suspense,
                            'foreshadowing': next_ch.foreshadowing,
                            'twist_level': next_ch.twist_level,
                            'summary': next_ch.summary
                        }

                    # 使用自动生成器的章节生成逻辑（如果可用）
                    if self.auto_generator and use_context:
                        chapter_info = {
                            "num": chapter_num,
                            "title": chapter.title,
                            "description": chapter_desc,
                            "scenes": []
                        }

                        success, message, chapter_data = self.auto_generator.generate_chapter(
                            project_id=self.current_project_id or "snowflake_temp",
                            chapter_info=chapter_info,
                            previous_chapters=generated_chapters,
                            use_context=use_context
                        )

                        if success and chapter_data:
                            content = chapter_data.get("content", "")
                            # 保存到连贯性系统
                            if use_coherence and self.coherence_system:
                                self._update_coherence(chapter_num, chapter_data)
                        else:
                            content = self._generate_chapter_fallback(
                                chapter_num, chapter.title, chapter_desc,
                                novel_setting, generated_chapters, target_words,
                                next_chapter_info
                            )
                    else:
                        # 回退到简单生成
                        content = self._generate_chapter_fallback(
                            chapter_num, chapter.title, chapter_desc,
                            novel_setting, generated_chapters, target_words,
                            next_chapter_info
                        )

                    if content:
                        chapter_header = f"\n\n{'='*50}\n第 {chapter_num} 章 {chapter.title}\n{'='*50}\n\n"
                        all_content += chapter_header + content

                        # 记录已生成的章节
                        generated_chapters.append({
                            "num": chapter_num,
                            "title": chapter.title,
                            "desc": chapter_desc,
                            "content": content,
                            "word_count": len(content),
                            "summary": content[:200] + "..." if len(content) > 200 else content
                        })

                        # 保存到缓存
                        if use_cache:
                            self._save_chapter_cache(chapter_num, {
                                "num": chapter_num,
                                "title": chapter.title,
                                "content": content,
                                "word_count": len(content)
                            })

                        progress_text += f"✅ 第 {chapter_num} 章生成完成 ({len(content)} 字)\n"
                    else:
                        progress_text += f"❌ 第 {chapter_num} 章生成失败: API返回空内容\n"

                except Exception as e:
                    logger.error(f"生成第 {chapter_num} 章失败: {e}")
                    progress_text += f"❌ 第 {chapter_num} 章生成失败: {str(e)}\n"

            self.is_generating = False
            generated_count = len([ch for ch in generated_chapters if start_chapter <= ch["num"] <= end_chapter])
            progress_text += f"\n\n🎉 完成！共生成 {generated_count} 章"

            return progress_text, all_content

        except Exception as e:
            self.is_generating = False
            logger.error(f"[雪花写作法] 章节生成失败: {e}", exc_info=True)
            return f"❌ 生成失败: {str(e)}", ""

    def _generate_chapter_fallback(
        self,
        chapter_num: int,
        chapter_title: str,
        chapter_desc: str,
        novel_setting: str,
        previous_chapters: List[Dict],
        target_words: int,
        next_chapter_info: Optional[Dict] = None
    ) -> str:
        """回退的章节生成方法（不使用自动生成器）"""
        try:
            # 构建上下文
            context = ""
            if previous_chapters:
                recent_chapters = previous_chapters[-5:]  # 最近5章
                for prev_ch in recent_chapters:
                    context += f"第{prev_ch['num']}章 {prev_ch['title']}:\n{prev_ch.get('summary', '')[:200]}\n\n"

            # 导入章节生成prompt
            from src.core.prompts.snowflake.chapter_generation import (
                create_first_chapter_prompt,
                create_next_chapter_prompt,
            )

            if chapter_num == 1:
                prompt = create_first_chapter_prompt(
                    chapter_number=chapter_num,
                    chapter_title=chapter_title,
                    chapter_role=chapter_desc,
                    chapter_purpose="",
                    suspense_level="",
                    foreshadowing="",
                    plot_twist_level="",
                    chapter_summary="",
                    novel_setting=novel_setting,
                    word_number=target_words,
                    user_guidance=""
                )
            else:
                prev_excerpt = ""
                global_summary = ""
                if previous_chapters:
                    last_chapter = previous_chapters[-1]
                    prev_excerpt = last_chapter.get("content", "")[-800:]
                    global_summary = "\n".join([
                        f"第{ch['num']}章: {ch.get('summary', '')[:100]}"
                        for ch in previous_chapters[-10:]
                    ])

                # 获取下一章信息，如果没有则使用默认值
                if next_chapter_info:
                    next_num = next_chapter_info.get('number', chapter_num + 1)
                    next_title = next_chapter_info.get('title', '')
                    next_role = next_chapter_info.get('position', '')
                    next_purpose = next_chapter_info.get('purpose', '')
                    next_suspense = next_chapter_info.get('suspense', '')
                    next_fore = next_chapter_info.get('foreshadowing', '')
                    next_twist = next_chapter_info.get('twist_level', '')
                    next_summary = next_chapter_info.get('summary', '')
                else:
                    next_num = chapter_num + 1
                    next_title = ''
                    next_role = ''
                    next_purpose = ''
                    next_suspense = '中等'
                    next_fore = ''
                    next_twist = ''
                    next_summary = ''

                prompt = create_next_chapter_prompt(
                    chapter_number=chapter_num,
                    chapter_title=chapter_title,
                    chapter_role=chapter_desc,
                    chapter_purpose="",
                    suspense_level="",
                    foreshadowing="",
                    plot_twist_level="",
                    chapter_summary="",
                    word_number=target_words,
                    global_summary=global_summary,
                    previous_chapter_excerpt=prev_excerpt,
                    character_state="",
                    next_chapter_number=next_num,
                    next_chapter_title=next_title,
                    next_chapter_role=next_role,
                    next_chapter_purpose=next_purpose,
                    next_suspense_level=next_suspense,
                    next_foreshadowing=next_fore,
                    next_plot_twist_level=next_twist,
                    next_chapter_summary=next_summary,
                )

            # 调用API生成
            messages = [
                {"role": "system", "content": "你是专业的小说作家，擅长创作引人入胜的故事。"},
                {"role": "user", "content": prompt}
            ]

            content = self.api_client.generate(
                messages=messages,
                temperature=0.8,
                max_tokens=4000
            )

            return content.strip() if content else ""

        except Exception as e:
            logger.error(f"回退章节生成失败: {e}")
            return ""

    def _update_coherence(self, chapter_num: int, chapter_data: Dict):
        """更新连贯性系统"""
        try:
            if not self.coherence_system:
                return

            # 更新角色追踪
            character_tracker = self.coherence_system.get("character_tracker")
            if character_tracker:
                from src.core.coherence import analyze_characters_from_chapter
                analyze_characters_from_chapter(
                    character_tracker,
                    chapter_data.get("content", ""),
                    chapter_num,
                    self.current_project_id or "snowflake_temp"
                )

            # 更新剧情管理
            plot_manager = self.coherence_system.get("plot_manager")
            if plot_manager:
                from src.core.coherence import analyze_plot_from_chapter
                analyze_plot_from_chapter(
                    plot_manager,
                    chapter_data.get("desc", ""),
                    chapter_num,
                    self.current_project_id or "snowflake_temp"
                )

            # 更新世界观
            world_db = self.coherence_system.get("world_db")
            if world_db:
                from src.core.coherence import extract_world_setting_from_chapter
                extract_world_setting_from_chapter(
                    world_db,
                    chapter_data.get("content", ""),
                    chapter_num,
                    self.current_project_id or "snowflake_temp"
                )

            logger.debug(f"已更新连贯性系统: 第{chapter_num}章")

        except Exception as e:
            logger.warning(f"更新连贯性系统失败: {e}")

    def _save_chapter_cache(self, chapter_num: int, chapter_data: Dict):
        """保存章节缓存"""
        try:
            cache_dir = Path("cache/snowflake")
            cache_dir.mkdir(parents=True, exist_ok=True)

            cache_file = cache_dir / f"{self.current_project_id}_chapters.json"

            # 读取现有缓存
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            else:
                cache = {"chapters": {}}

            # 添加新章节
            cache["chapters"][str(chapter_num)] = {
                **chapter_data,
                "cached_at": datetime.now().isoformat()
            }

            # 保存缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

            logger.debug(f"已缓存第{chapter_num}章")

        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")

    def _stop_generation(self) -> str:
        """停止生成"""
        self.should_stop = True
        if self.auto_generator:
            self.auto_generator.stop_generation()
        return "⏹️ 正在停止生成..."

    def _clear_all(self) -> tuple:
        """清空所有内容"""
        self.current_architecture = None
        self.current_blueprint = ""
        self.current_config = None
        self.current_project_id = None

        return (
            "",  # topic
            "",  # user_guidance
            "",  # architecture_output
            "",  # core_seed
            "",  # character
            "",  # world
            "",  # plot
            "",  # character_state
            "",  # blueprint
            "",  # parsed_chapters
            "",  # generation_progress
            "",  # generation_output
        )


# 便捷函数
def create_snowflake_ui(
    api_client,
    project_manager,
    auto_generator=None,
    coherence_system=None
) -> gr.Blocks:
    """创建雪花写作法UI的便捷函数"""
    ui = SnowflakeGeneratorUI(
        api_client,
        project_manager,
        auto_generator,
        coherence_system
    )
    return ui.create_ui()
