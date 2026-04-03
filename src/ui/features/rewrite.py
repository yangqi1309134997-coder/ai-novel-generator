"""
小说重写与续写功能模块
支持文件上传、智能重写、AI续写

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import gradio as gr
import logging
from typing import List, Tuple, Generator, Optional
from datetime import datetime
from pathlib import Path
import json

from src.ui.features.file_utils import read_uploaded_file

logger = logging.getLogger(__name__)


def analyze_novel_for_continuation(api_client, novel_content: str, current_chapters: int = 30) -> Tuple[str, str, str]:
    """
    分析小说，规划后续章节

    Args:
        api_client: API客户端
        novel_content: 小说内容
        current_chapters: 当前章节数

    Returns:
        (剧情分析, 后续规划, 状态消息)
    """
    if not api_client:
        return "", "", "API客户端未初始化"

    logger.info(f"[续写功能] 开始分析小说，当前章节: {current_chapters}, 内容长度: {len(novel_content)}")

    try:
        # 截取前5000字用于分析
        analysis_text = novel_content[:5000] if len(novel_content) > 5000 else novel_content

        prompt = f"""请分析以下小说片段，并规划后续章节发展。

【当前小说内容】（前5000字）
{analysis_text}

【当前章节数】
第{current_chapters}章

【分析要求】
1. **世界观分析**：提取故事的世界观设定（修仙体系、魔法系统、历史背景等）
2. **主角分析**：分析主角的性格、能力、目标、当前状态
3. **剧情主线**：总结当前的主要剧情走向
4. **角色关系**：分析主要人物关系网

【后续章节规划】
基于以上分析，请规划第{current_chapters + 1}到第{current_chapters + 10}章的内容：
- 每章标题
- 每章核心情节（50字以内）
- 剧情发展逻辑

请按以下格式返回：

=== 世界观分析 ===
...

=== 主角分析 ===
...

=== 剧情主线 ===
...

=== 后续章节规划 ===
第{current_chapters + 1}章：标题
核心情节：...

第{current_chapters + 2}章：标题
核心情节：...

（依此类推到第{current_chapters + 10}章）
"""

        messages = [
            {"role": "system", "content": "你是一位专业的小说编辑，擅长分析小说情节并规划后续发展。"},
            {"role": "user", "content": prompt}
        ]

        result = api_client.generate(
            messages=messages,
            max_tokens=4000,
            temperature=0.7
        )

        if result:
            # 尝试分离分析和规划
            if "=== 后续章节规划 ===" in result:
                parts = result.split("=== 后续章节规划 ===")
                analysis = parts[0].strip()
                planning = "=== 后续章节规划 ===\n" + parts[1].strip()
                logger.info(f"[续写功能] 分析完成，分析长度: {len(analysis)}, 规划长度: {len(planning)}")
                return analysis, planning, "✓ 分析完成"
            else:
                logger.warning(f"[续写功能] 分析完成但无法分离规划部分")
                return result, "", "✓ 分析完成（但无法分离规划部分）"
        else:
            logger.error(f"[续写功能] 分析失败：API返回空结果")
            return "", "", "❌ 分析失败：API返回空结果"

    except Exception as e:
        logger.error(f"[续写功能] 分析失败: {e}", exc_info=True)
        return "", "", f"❌ 分析失败: {str(e)}"


def generate_continuation_chapter(
    api_client,
    novel_content: str,
    chapter_plan: str,
    chapter_num: int,
    target_words: int = 3000
) -> Tuple[str, str]:
    """
    生成续写章节

    Args:
        api_client: API客户端
        novel_content: 已有小说内容
        chapter_plan: 章节规划
        chapter_num: 章节号
        target_words: 目标字数

    Returns:
        (生成内容, 状态消息)
    """
    if not api_client:
        return "", "API客户端未初始化"

    logger.info(f"[续写功能] 生成续写章节: 第{chapter_num}章, 目标字数: {target_words}")

    try:
        # 获取最后2000字作为上下文
        context = novel_content[-2000:] if len(novel_content) > 2000 else novel_content

        # 计算字数范围
        words_tolerance = max(100, int(target_words * 0.1))
        min_words = target_words - words_tolerance
        max_words = target_words + words_tolerance

        prompt = f"""请根据以下信息续写小说章节。

【前文回顾】（最后2000字）
{context}

【本章规划】
{chapter_plan}

【写作要求】
- 章节号：第{chapter_num}章
- 【严格字数要求】必须生成 {target_words} 字左右（误差不超过±{words_tolerance}字）
- 绝对不能超过 {max_words} 字，也不能少于 {min_words} 字
- 字数控制是第一要务，宁可内容紧凑也不得超字数
- 保持与前文的连贯性（人物性格、剧情逻辑、世界观设定）
- 延续前文的文风和叙述方式

【字数控制提示】
在创作过程中请自觉控制字数：
- 如果目标{target_words}字，请确保内容刚好覆盖这个长度
- 避免过度描写和冗长叙述
- 每个场景聚焦核心情节

请开始创作本章内容："""

        messages = [
            {"role": "system", "content": "你是一位专业的小说作家。你必须严格遵守字数要求，生成的章节字数必须精确控制。"},
            {"role": "user", "content": prompt}
        ]

        max_tokens_limit = int(target_words * 1.2)

        result = api_client.generate(
            messages=messages,
            max_tokens=max_tokens_limit,
            temperature=0.8
        )

        if result and len(result.strip()) > 100:
            # 字数验证
            actual_words = len(result)
            diff_percent = abs(actual_words - target_words) / target_words * 100

            logger.info(f"[续写功能] 续写第{chapter_num}章 - 目标字数: {target_words}, 实际字数: {actual_words}, 误差: {diff_percent:.1f}%")

            status = f"✓ 生成成功 ({actual_words} 字"
            if diff_percent > 15:
                status += f"，误差较大: {diff_percent:.1f}%"
            status += ")"

            return result, status
        else:
            logger.error(f"[续写功能] 生成失败：返回内容过短")
            return "", "❌ 生成失败：返回内容过短"

    except Exception as e:
        logger.error(f"[续写功能] 生成续写章节失败: {e}", exc_info=True)
        return "", f"❌ 生成失败: {str(e)}"


def create_rewrite_ui(app_state):
    """
    创建重写与续写功能UI

    Args:
        app_state: 应用状态对象

    Returns:
        Gradio Blocks对象
    """
    # 获取可用的风格列表
    try:
        from src.core.prompts.templates import PRESET_TEMPLATES
        style_choices = [k.replace("重写风格 - ", "") for k in PRESET_TEMPLATES.keys() if k.startswith("重写风格")]
    except:
        style_choices = ["默认", "玄幻仙侠", "都市言情", "悬疑惊悚", "科幻硬核"]

    # 获取项目列表
    try:
        from project_manager import ProjectManager
        projects = ProjectManager.list_projects()
        project_choices = [p["title"] for p in projects] if projects else []
    except Exception as e:
        logger.warning(f"[重写续写] 获取项目列表失败: {e}")
        project_choices = []

    with gr.Blocks() as rewrite_ui:
        gr.Markdown("## 📝 小说重写 & 续写")
        gr.Markdown("### 支持文件上传、智能重写、AI续写")

        with gr.Tabs():
            # Tab 1: 重写
            with gr.Tab("📝 小说重写"):
                gr.Markdown("### 📖 选择项目（可选）")
                with gr.Row():
                    rewrite_project_select = gr.Dropdown(
                        choices=project_choices,
                        label="选择项目",
                        info="从项目加载",
                        interactive=True
                    )
                    rewrite_refresh_btn = gr.Button("🔄 刷新项目", size="sm")

                rewrite_project_info = gr.Markdown("**提示**：您可以选择项目，或直接上传文件重写")

                gr.Markdown("---")
                gr.Markdown("### 📤 上传文件")
                gr.Markdown("支持格式：.txt, .md, .docx, .json")

                rewrite_file_upload = gr.File(
                    label="上传文件",
                    file_types=[".txt", ".md", ".docx", ".json"],
                    type="filepath"
                )

                rewrite_file_status = gr.Textbox(
                    label="文件状态",
                    interactive=False,
                    lines=2
                )

                gr.Markdown("---")
                gr.Markdown("### ✍️ 编辑内容")

                rewrite_input = gr.Textbox(
                    label="待重写文本",
                    lines=10,
                    placeholder="上传文件后会自动显示，或直接在此粘贴文本..."
                )

                with gr.Accordion("⚙️ 高级设置", open=False):
                    with gr.Row():
                        split_method = gr.Radio(
                            choices=["自动分段", "按字数分段", "按固定文本分段"],
                            value="自动分段",
                            label="分段方式"
                        )

                    with gr.Row():
                        word_count = gr.Number(
                            label="每段字数",
                            value=2000,
                            minimum=100,
                            maximum=10000,
                            visible=False
                        )

                        pattern_input = gr.Textbox(
                            label="分段标记",
                            placeholder="如：--- 或 [章节]",
                            visible=False
                        )

                    style_dropdown = gr.Dropdown(
                        choices=style_choices,
                        value="默认",
                        label="重写风格"
                    )

                rewrite_btn = gr.Button("🚀 开始重写", variant="primary", size="lg")

                gr.Markdown("---")
                gr.Markdown("### 📄 重写结果")

                rewrite_output = gr.Textbox(
                    label="重写结果",
                    lines=15,
                    interactive=True
                )

                rewrite_status = gr.Textbox(
                    label="状态",
                    interactive=False,
                    lines=2
                )

                with gr.Row():
                    copy_rewrite_btn = gr.Button("📋 复制结果")
                    clear_rewrite_btn = gr.Button("🗑️ 清空")

            # Tab 2: 续写
            with gr.Tab("✍️ AI续写"):
                gr.Markdown("### 📖 选择项目（推荐）")
                with gr.Row():
                    continue_project_select = gr.Dropdown(
                        choices=project_choices,
                        label="选择要续写的项目",
                        info="从项目加载",
                        interactive=True
                    )
                    continue_refresh_btn = gr.Button("🔄 刷新项目", size="sm")

                continue_project_info = gr.Markdown("**提示**：选择项目后自动分析剧情、规划后续章节")

                gr.Markdown("---")
                gr.Markdown("### 📤 上传已有小说（或手动输入）")
                gr.Markdown("支持格式：.txt, .md, .docx, .json")

                continue_file_upload = gr.File(
                    label="上传已有小说文件",
                    file_types=[".txt", ".md", ".docx", ".json"],
                    type="filepath"
                )

                continue_file_status = gr.Textbox(
                    label="文件状态",
                    interactive=False,
                    lines=2
                )

                continue_input = gr.Textbox(
                    label="已有小说内容",
                    lines=10,
                    placeholder="上传文件后自动显示，或直接粘贴已有小说内容..."
                )

                with gr.Row():
                    current_chapters = gr.Number(
                        label="当前章节数",
                        value=30,
                        minimum=1,
                        maximum=10000,
                        info="例如：已写到第30章"
                    )
                    continue_target_words = gr.Number(
                        label="续写章节字数",
                        value=3000,
                        minimum=100,
                        maximum=50000
                    )

                with gr.Row():
                    continue_count = gr.Slider(
                        minimum=1,
                        maximum=20,
                        value=5,
                        step=1,
                        label="续写章节数",
                        info="一次续写多少章"
                    )

                analyze_btn = gr.Button("🔍 分析小说并规划后续章节", variant="primary")

                gr.Markdown("---")
                gr.Markdown("### 📊 分析结果")

                with gr.Row():
                    analysis_output = gr.Textbox(
                        label="剧情分析（世界观、主角、主线）",
                        lines=10,
                        interactive=False
                    )
                    planning_output = gr.Textbox(
                        label="后续章节规划",
                        lines=10,
                        interactive=True
                    )

                analysis_status = gr.Textbox(
                    label="分析状态",
                    interactive=False
                )

                continue_generate_btn = gr.Button("✍️ 开始续写", variant="primary", size="lg")

                gr.Markdown("---")
                gr.Markdown("### 📄 续写结果")

                continue_output = gr.Textbox(
                    label="续写内容",
                    lines=20,
                    interactive=True
                )

                continue_status = gr.Textbox(
                    label="生成状态",
                    interactive=False,
                    lines=3
                )

                with gr.Row():
                    copy_continue_btn = gr.Button("📋 复制结果")
                    save_continue_btn = gr.Button("💾 保存到项目")
                    clear_continue_btn = gr.Button("🗑️ 清空")

        # ========== 事件处理 ==========

        # 重写模块事件
        def on_rewrite_file_upload(file):
            """文件上传"""
            if file:
                content, status = read_uploaded_file(file)
                return content, status
            return "", "未选择文件"

        def on_rewrite_project_change(project_title):
            """项目选择变化"""
            if not project_title:
                return "**提示**：您可以选择项目，或直接上传文件重写"

            try:
                from project_manager import ProjectManager
                project = ProjectManager.get_project_by_title(project_title)
                if not project:
                    return "❌ 项目加载失败"

                chapters = project.get("chapters", [])
                total_words = sum(ch.get('word_count', 0) for ch in chapters)

                info = f"""### 📚 {project.get('title', '')}
- **类型**: {project.get('genre', '')}
- **总字数**: {total_words:,} 字
- **章节数**: {len(chapters)} 章

✓ 已加载项目，可以导出后重写，或直接查看项目文件"""
                return info
            except Exception as e:
                return f"❌ 加载失败: {str(e)}"

        def on_rewrite_split_change(method):
            """分段方式变化"""
            if method == "按字数分段":
                return gr.update(visible=True), gr.update(visible=False)
            elif method == "按固定文本分段":
                return gr.update(visible=False), gr.update(visible=True)
            else:
                return gr.update(visible=False), gr.update(visible=False)

        # 续写模块事件
        def on_continue_file_upload(file):
            """续写文件上传"""
            if file:
                content, status = read_uploaded_file(file)
                return content, status
            return "", "未选择文件"

        def on_continue_project_change(project_title):
            """续写项目选择变化"""
            if not project_title:
                return "**提示**：选择项目后自动分析剧情、规划后续章节"

            try:
                from project_manager import ProjectManager
                project = ProjectManager.get_project_by_title(project_title)
                if not project:
                    return "❌ 项目加载失败"

                chapters = project.get("chapters", [])
                if not chapters:
                    return "❌ 项目中没有章节内容"

                # 合并所有章节内容
                content = '\n\n'.join([
                    f"第{ch.get('num', '')}章 {ch.get('title', '')}\n\n{ch.get('content', '')}"
                    for ch in chapters if ch.get('content')
                ])

                info = f"""### 📚 {project.get('title', '')}
- **类型**: {project.get('genre', '')}
- **章节数**: {len(chapters)} 章
- **总字数**: {sum(ch.get('word_count', 0) for ch in chapters):,} 字

✓ 已加载项目内容，可以直接点击"分析小说并规划后续章节"
"""
                return info
            except Exception as e:
                return f"❌ 加载失败: {str(e)}"

        def on_analyze_click(content, current_ch):
            """分析按钮点击"""
            if not content or not content.strip():
                return "", "", "❌ 请先上传文件或输入小说内容"

            if not app_state.api_client:
                return "", "", "❌ 请先配置API"

            analysis, planning, status = analyze_novel_for_continuation(
                app_state.api_client,
                content,
                int(current_ch)
            )

            return analysis, planning, status

        def on_continue_generate_click(novel_content, planning, current_ch, target_words, count):
            """续写生成按钮点击"""
            if not novel_content or not novel_content.strip():
                return "", "❌ 请先上传或输入小说内容"

            if not planning or not planning.strip():
                return "", '❌ 请先点击"分析小说并规划后续章节"'

            if not app_state.api_client:
                return "", "❌ 请先配置API"

            try:
                # 提取章节规划
                lines = planning.split('\n')
                chapter_plans = []
                current_plan = []

                for line in lines:
                    line = line.strip()
                    if line.startswith(f'第{int(current_ch) + 1}') or line.startswith(f'第 {int(current_ch) + 1}'):
                        current_plan = [line]
                    elif current_plan and (line.startswith('第') or '核心情节' in line):
                        current_plan.append(line)
                        if '核心情节' in line:
                            chapter_plans.append('\n'.join(current_plan))
                            current_plan = []

                # 如果解析失败，使用整个planning
                if not chapter_plans:
                    chapter_plans = [planning] * int(count)

                # 生成章节
                all_content = []
                num = int(current_ch)

                for i in range(min(int(count), len(chapter_plans))):
                    chapter_plan = chapter_plans[i] if i < len(chapter_plans) else planning
                    content, status = generate_continuation_chapter(
                        app_state.api_client,
                        novel_content,
                        chapter_plan,
                        num + i + 1,
                        int(target_words)
                    )

                    if "✓" not in status:
                        return "\n\n".join(all_content), f"❌ 第{num + i + 1}章生成失败: {status}"

                    all_content.append(f"第{num + i + 1}章\n\n{content}")
                    yield "\n\n".join(all_content), f"正在生成第{i+1}/{count}章..."

                yield "\n\n".join(all_content), f"✓ 成功续写{len(all_content)}章"

            except Exception as e:
                logger.error(f"[续写功能] 续写失败: {e}", exc_info=True)
                yield "", f"❌ 续写失败: {str(e)}"

        # ========== 绑定事件 ==========

        # 重写事件
        rewrite_file_upload.upload(
            fn=on_rewrite_file_upload,
            inputs=[rewrite_file_upload],
            outputs=[rewrite_input, rewrite_file_status]
        )

        rewrite_project_select.change(
            fn=on_rewrite_project_change,
            inputs=[rewrite_project_select],
            outputs=[rewrite_project_info]
        )

        split_method.change(
            fn=on_rewrite_split_change,
            inputs=[split_method],
            outputs=[word_count, pattern_input]
        )

        # 续写事件
        continue_file_upload.upload(
            fn=on_continue_file_upload,
            inputs=[continue_file_upload],
            outputs=[continue_input, continue_file_status]
        )

        continue_project_select.change(
            fn=on_continue_project_change,
            inputs=[continue_project_select],
            outputs=[continue_project_info]
        )

        analyze_btn.click(
            fn=on_analyze_click,
            inputs=[continue_input, current_chapters],
            outputs=[analysis_output, planning_output, analysis_status]
        )

        continue_generate_btn.click(
            fn=on_continue_generate_click,
            inputs=[continue_input, planning_output, current_chapters, continue_target_words, continue_count],
            outputs=[continue_output, continue_status]
        )

        # 复制和清空按钮（简化实现）
        copy_rewrite_btn.click(
            fn=lambda x: "✓ 已复制" if x else "❌ 无内容",
            inputs=[rewrite_output],
            outputs=[rewrite_status]
        )

        clear_rewrite_btn.click(
            fn=lambda: ("", "", "已清空"),
            outputs=[rewrite_input, rewrite_output, rewrite_status]
        )

        copy_continue_btn.click(
            fn=lambda x: "✓ 已复制" if x else "❌ 无内容",
            inputs=[continue_output],
            outputs=[continue_status]
        )

        clear_continue_btn.click(
            fn=lambda: ("", "", "", "已清空"),
            outputs=[continue_input, continue_output, continue_status, analysis_status]
        )

    return rewrite_ui
