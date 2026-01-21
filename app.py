"""
生产级别的AI小说生成工具 - Gradio Web UI
支持：创作、重写、导出、项目管理、配置管理

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import gradio as gr
import pandas as pd
import logging
import threading
import socket
from typing import List, Tuple, Optional
import os
import re

# 导入各个模块
from config import get_config, Backend
from logger import setup_logger, get_logger, get_performance_monitor
from api_client import get_api_client, reinit_api_client
from file_parser import parse_novel_file, split_by_word_count, split_by_pattern
from novel_generator import (
    get_generator, OutlineParser, PRESET_TEMPLATES,
    save_generation_cache, load_generation_cache, clear_generation_cache,
    list_generation_caches, get_cache_size,
    generate_chapter_summary, save_chapter_summary, load_chapter_summaries,
    build_context_from_summaries, clear_chapter_summaries, list_summary_caches,
    get_summary_cache_size
)
from exporter import export_to_docx, export_to_txt, export_to_markdown, export_to_html, list_export_files
from project_manager import ProjectManager
from config_api import config_api

# 设置日志
logger = setup_logger("NovelToolUI", log_level=logging.INFO)
config = get_config()

# 可通过环境变量覆盖运行参数（production friendly）
WEB_HOST = os.getenv("NOVEL_TOOL_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("NOVEL_TOOL_PORT", os.getenv("PORT", "7860")))
WEB_SHOW_ERRORS = os.getenv("NOVEL_TOOL_SHOW_ERRORS", "false").lower() in ("1", "true", "yes")
WEB_CONCURRENCY = int(os.getenv("NOVEL_TOOL_CONCURRENCY", "4"))
WEB_QUEUE_MAX = int(os.getenv("NOVEL_TOOL_QUEUE_MAX", "50"))


def find_available_port(start_port: int = 7860, max_attempts: int = 100) -> int:
    """查找可用的端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    # 如果都找不到，返回原端口让系统报错
    return start_port

# 全局状态管理
generation_state = {
    "is_generating": False,
    "stop_requested": False,
    "lock": threading.Lock(),
    "current_project": None,  # 存储当前生成中的项目对象
    "current_chapters": None,  # 存储当前生成中的章节列表
    "current_full_text": None  # 存储当前生成的完整文本
}


def set_generation_state(is_generating: bool, stop_requested: bool = False) -> None:
    """线程安全地更新生成状态"""
    with generation_state["lock"]:
        generation_state["is_generating"] = is_generating
        generation_state["stop_requested"] = stop_requested


def request_stop() -> Tuple[str, gr.update]:
    """请求停止生成"""
    set_generation_state(False, True)
    logger.info("用户请求停止生成")
    return "已请求暂停（当前章节完成后停止）", gr.update(interactive=False)


def should_stop() -> bool:
    """检查是否应该停止"""
    with generation_state["lock"]:
        return generation_state["stop_requested"]


# ==================== 润色功能 ====================
def handle_polish(text: str, polish_type: str, custom_req: str, progress=gr.Progress()):
    """处理文本润色（支持分段处理）"""
    if not text or not text.strip():
        return "", "无内容可润色"

    set_generation_state(True, False)
    generator = get_generator()

    # 生成项目名称
    from datetime import datetime
    project_title = f"润色-{polish_type}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        polish_types_map = {
            "全面润色": "general",
            "查找错误": "find_errors",
            "改进建议": "suggest_improvements",
            "直接修改": "direct_modify",
            "去除AI味": "remove_ai_flavor",
            "增强细节": "enhance_details",
            "优化对话": "optimize_dialogue",
            "改善节奏": "improve_pacing",
        }

        actual_type = polish_types_map.get(polish_type, "general")

        # 检查文本长度，如果超过限制则自动分段处理
        max_single_segment = 8000  # 单段最大字数，留出余量
        if len(text) <= max_single_segment:
            # 文本较短，直接处理
            content, success_msg = generator.polish_text(
                text=text,
                polish_type=actual_type,
                custom_requirements=custom_req
            )

            if success_msg != "润色成功":
                logger.error(f"润色失败: {content}")
                return "", content

            # 验证content是否有效：检查是否为状态消息或过短
            if not content or not content.strip() or len(content.strip()) < 10:
                error_msg = f"润色返回了无效内容（长度: {len(content) if content else 0}字）"
                logger.error(error_msg)
                return "", error_msg

            # 检查是否为状态消息（如"润色成功"、"生成成功"等）
            status_messages = ["重写成功", "润色成功", "生成成功", "续写成功"]
            content_stripped = content.strip()
            for status_msg in status_messages:
                if status_msg in content_stripped and len(content_stripped) < 50:
                    error_msg = f"润色返回了状态消息而非实际内容: '{content_stripped}'"
                    logger.error(error_msg)
                    return "", error_msg

            logger.info("润色完成")
            polished_content = content
        else:
            # 文本较长，自动分段处理
            logger.info(f"文本过长（{len(text)}字），启用自动分段处理")
            from file_parser import split_by_word_count
            segments = split_by_word_count(text, max_single_segment)
            logger.info(f"已分为 {len(segments)} 段，开始逐段润色")

            polished_segments = []
            for i, segment in enumerate(segments):
                progress((i + 1) / len(segments), desc=f"润色第 {i+1}/{len(segments)} 段")

                segment_content, success_msg = generator.polish_text(
                    text=segment,
                    polish_type=actual_type,
                    custom_requirements=custom_req
                )

                if success_msg != "润色成功":
                    logger.error(f"第 {i+1} 段润色失败: {segment_content}")
                    return "", f"第 {i+1} 段润色失败: {segment_content}"

                # 验证内容
                if not segment_content or not segment_content.strip() or len(segment_content.strip()) < 10:
                    error_msg = f"第 {i+1} 段润色返回了无效内容（长度: {len(segment_content) if segment_content else 0}字）"
                    logger.error(error_msg)
                    return "", error_msg

                polished_segments.append(segment_content)

            # 合并所有润色后的段落
            polished_content = "\n\n".join(polished_segments)
            logger.info(f"分段润色完成，共 {len(polished_segments)} 段，总字数: {len(polished_content)}")

        # 保存到项目管理
        if polished_content:
            from novel_generator import NovelProject, Chapter
            project = NovelProject(
                title=project_title,
                genre="润色",
                character_setting=f"润色类型: {polish_type}",
                world_setting="",
                plot_idea=f"自定义要求: {custom_req}" if custom_req else "无自定义要求"
            )

            # 创建章节保存润色内容
            chapter = Chapter(
                num=1,
                title="润色内容",
                desc=f"使用{polish_type}进行润色",
                content=polished_content,
                word_count=len(polished_content),
                generated_at=datetime.now().isoformat()
            )
            project.chapters.append(chapter)

            # 保存项目
            save_success, save_msg = ProjectManager.save_project(project)
            if save_success:
                logger.info(f"润色结果已保存到项目: {project.id}")
                return polished_content, "润色完成 | 已保存至项目管理"
            else:
                logger.warning(f"润色结果保存失败: {save_msg}")
                return polished_content, "润色完成"
        else:
            return polished_content, "润色完成"
    finally:
        set_generation_state(False)


def handle_polish_with_suggestions(text: str, custom_req: str, progress=gr.Progress()):
    """处理润色并提供建议（支持分段处理）"""
    if not text or not text.strip():
        return "", "", "无内容可润色"

    set_generation_state(True, False)
    generator = get_generator()

    # 生成项目名称
    from datetime import datetime
    project_title = f"润色-改进建议-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        # 检查文本长度，如果超过限制则自动分段处理
        max_single_segment = 8000  # 单段最大字数，留出余量
        if len(text) <= max_single_segment:
            # 文本较短，直接处理
            polished, suggestions, msg = generator.polish_and_suggest(
                text=text,
                custom_requirements=custom_req
            )

            if msg != "润色成功":
                logger.error(f"润色失败: {msg}")
                return "", "", msg

            # 验证polished是否有效：检查是否为状态消息或过短
            if not polished or not polished.strip() or len(polished.strip()) < 10:
                error_msg = f"润色返回了无效内容（长度: {len(polished) if polished else 0}字）"
                logger.error(error_msg)
                return "", "", error_msg

            # 检查是否为状态消息（如"润色成功"、"生成成功"等）
            status_messages = ["重写成功", "润色成功", "生成成功", "续写成功"]
            polished_stripped = polished.strip()
            for status_msg in status_messages:
                if status_msg in polished_stripped and len(polished_stripped) < 50:
                    error_msg = f"润色返回了状态消息而非实际内容: '{polished_stripped}'"
                    logger.error(error_msg)
                    return "", "", error_msg

            logger.info("润色完成")
            polished_content = polished
            all_suggestions = suggestions
        else:
            # 文本较长，自动分段处理
            logger.info(f"文本过长（{len(text)}字），启用自动分段处理")
            from file_parser import split_by_word_count
            segments = split_by_word_count(text, max_single_segment)
            logger.info(f"已分为 {len(segments)} 段，开始逐段润色")

            polished_segments = []
            all_suggestions = []

            for i, segment in enumerate(segments):
                progress((i + 1) / len(segments), desc=f"润色第 {i+1}/{len(segments)} 段")

                segment_polished, segment_suggestions, msg = generator.polish_and_suggest(
                    text=segment,
                    custom_requirements=custom_req
                )

                if msg != "润色成功":
                    logger.error(f"第 {i+1} 段润色失败: {msg}")
                    return "", "", f"第 {i+1} 段润色失败: {msg}"

                # 验证内容
                if not segment_polished or not segment_polished.strip() or len(segment_polished.strip()) < 10:
                    error_msg = f"第 {i+1} 段润色返回了无效内容（长度: {len(segment_polished) if segment_polished else 0}字）"
                    logger.error(error_msg)
                    return "", "", error_msg

                polished_segments.append(segment_polished)
                if segment_suggestions:
                    all_suggestions.append(f"【第{i+1}段】\n{segment_suggestions}")

            # 合并所有润色后的段落和建议
            polished_content = "\n\n".join(polished_segments)
            all_suggestions = "\n\n".join(all_suggestions)
            logger.info(f"分段润色完成，共 {len(polished_segments)} 段，总字数: {len(polished_content)}")

        # 保存到项目管理
        if polished_content:
            from novel_generator import NovelProject, Chapter
            project = NovelProject(
                title=project_title,
                genre="润色",
                character_setting="润色类型: 改进建议",
                world_setting="",
                plot_idea=f"自定义要求: {custom_req}" if custom_req else "无自定义要求"
            )

            # 创建章节保存润色内容
            chapter = Chapter(
                num=1,
                title="润色内容",
                desc="润色并提供建议",
                content=polished_content,
                word_count=len(polished_content),
                generated_at=datetime.now().isoformat()
            )
            project.chapters.append(chapter)

            # 保存项目
            save_success, save_msg = ProjectManager.save_project(project)
            if save_success:
                logger.info(f"润色结果已保存到项目: {project.id}")
                return polished_content, all_suggestions, "润色完成 | 已保存至项目管理"
            else:
                logger.warning(f"润色结果保存失败: {save_msg}")
                return polished_content, all_suggestions, "润色完成"
        else:
            return polished_content, all_suggestions, "润色完成"
    finally:
        set_generation_state(False)


# ==================== 重写功能 ====================
def handle_rewrite(paragraphs: List[str], rewritten_parts: List[str], style_name: str, progress=gr.Progress()):
    """处理段落重写（支持暂停续写）"""
    if not paragraphs:
        yield "", "", [], "无内容可重写"
        return

    set_generation_state(True, False)
    generator = get_generator()
    start_idx = len(rewritten_parts)
    total = len(paragraphs)
    
    # 根据风格名称获取对应的模板
    style_template = PRESET_TEMPLATES.get(style_name, PRESET_TEMPLATES["重写风格 - 默认"])
    
    # 生成项目名称
    from datetime import datetime
    project_title = f"重写-{style_name}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        for i in range(start_idx, total):
            if should_stop():
                logger.info(f"重写已暂停，已完成 {len(rewritten_parts)}/{total} 段")
                yield "\n\n".join(rewritten_parts), "\n\n".join(rewritten_parts), rewritten_parts[:], f"已暂停 - 完成 {len(rewritten_parts)}/{total} 段"
                return

            progress((i + 1 - start_idx) / (total - start_idx), desc=f"重写第 {i+1}/{total} 段")

            content, success_msg = generator.rewrite_paragraph(paragraphs[i], style_template)

            if success_msg != "重写成功":
                logger.error(f"第 {i+1} 段重写失败: {success_msg}")
                yield "\n\n".join(rewritten_parts), "\n\n".join(rewritten_parts), rewritten_parts[:], success_msg
                return

            # 验证content是否有效：检查是否为状态消息或过短
            if not content or not content.strip() or len(content.strip()) < 10:
                error_msg = f"第 {i+1} 段重写返回了无效内容（长度: {len(content) if content else 0}字）"
                logger.error(error_msg)
                yield "\n\n".join(rewritten_parts), "\n\n".join(rewritten_parts), rewritten_parts[:], error_msg
                return

            # 检查是否为状态消息（如"重写成功"、"润色成功"等）
            status_messages = ["重写成功", "润色成功", "生成成功", "续写成功"]
            content_stripped = content.strip()
            for status_msg in status_messages:
                if status_msg in content_stripped and len(content_stripped) < 50:
                    error_msg = f"第 {i+1} 段重写返回了状态消息而非实际内容: '{content_stripped}'"
                    logger.error(error_msg)
                    yield "\n\n".join(rewritten_parts), "\n\n".join(rewritten_parts), rewritten_parts[:], error_msg
                    return

            rewritten_parts.append(content)
            full = "\n\n".join(rewritten_parts)
            stats = f"进度 {len(rewritten_parts)}/{total} | 约 {sum(len(p) for p in rewritten_parts)} 字"
            yield full, full, rewritten_parts[:], stats

        logger.info("重写完成")
        
        # 保存到项目管理
        if full:
            from novel_generator import NovelProject, Chapter
            project = NovelProject(
                title=project_title,
                genre="重写",
                character_setting=f"风格: {style_name}",
                world_setting="",
                plot_idea=f"原始段落数: {len(paragraphs)}"
            )
            
            # 创建章节保存完整内容
            chapter = Chapter(
                num=1,
                title="重写内容",
                desc=f"使用{style_name}风格重写",
                content=full,
                word_count=len(full),
                generated_at=datetime.now().isoformat()
            )
            project.chapters.append(chapter)
            
            # 保存项目
            save_success, save_msg = ProjectManager.save_project(project)
            if save_success:
                logger.info(f"重写结果已保存到项目: {project.id}")
                yield full, full, rewritten_parts[:], stats + " | 重写完成 | 已保存至项目管理"
            else:
                logger.warning(f"重写结果保存失败: {save_msg}")
                yield full, full, rewritten_parts[:], stats + " | 重写完成"
        else:
            yield full, full, rewritten_parts[:], stats + " | 重写完成"

    finally:
        set_generation_state(False)


# ==================== 续写功能 ====================
def handle_continue_writing(
    existing_text: str,
    title: str,
    char_setting: str,
    world_setting: str,
    plot_idea: str,
    target_words: int
):
    """处理小说续写"""
    if not existing_text or not existing_text.strip():
        yield "", "无内容可续写"
        return

    if not title or not title.strip():
        yield "", "请填写小说标题"
        return

    set_generation_state(True, False)
    generator = get_generator()
    
    # 生成项目名称
    from datetime import datetime
    project_title = f"续写-{title}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        content, success_msg = generator.continue_writing(
            existing_text=existing_text,
            novel_title=title,
            character_setting=char_setting,
            world_setting=world_setting,
            plot_idea=plot_idea,
            target_words=int(target_words) if target_words else 2500
        )

        if success_msg == "续写成功":
            # 验证content是否有效：检查是否为状态消息或过短
            if not content or not content.strip() or len(content.strip()) < 10:
                error_msg = f"续写返回了无效内容（长度: {len(content) if content else 0}字）"
                logger.error(error_msg)
                yield "", error_msg
                return

            # 检查是否为状态消息（如"续写成功"、"生成成功"等）
            status_messages = ["重写成功", "润色成功", "生成成功", "续写成功"]
            content_stripped = content.strip()
            for status_msg in status_messages:
                if status_msg in content_stripped and len(content_stripped) < 50:
                    error_msg = f"续写返回了状态消息而非实际内容: '{content_stripped}'"
                    logger.error(error_msg)
                    yield "", error_msg
                    return

            logger.info("续写完成")

            # 保存到项目管理
            if content:
                from novel_generator import NovelProject, Chapter
                project = NovelProject(
                    title=project_title,
                    genre="续写",
                    character_setting=char_setting,
                    world_setting=world_setting,
                    plot_idea=plot_idea
                )
                
                # 创建章节保存续写内容
                chapter = Chapter(
                    num=1,
                    title="续写内容",
                    desc=f"为《{title}》续写",
                    content=content,
                    word_count=len(content),
                    generated_at=datetime.now().isoformat()
                )
                project.chapters.append(chapter)
                
                # 保存项目
                save_success, save_msg = ProjectManager.save_project(project)
                if save_success:
                    logger.info(f"续写结果已保存到项目: {project.id}")
                    yield content, "续写完成 | 已保存至项目管理"
                else:
                    logger.warning(f"续写结果保存失败: {save_msg}")
                    yield content, "续写完成"
            else:
                yield content, "续写完成"
        else:
            logger.error(f"续写失败: {content}")
            yield "", content
    finally:
        set_generation_state(False)


# ==================== 文件解析（支持多种分段方式） ====================
def parse_novel_file_with_split(file_path, split_method="自动分段", word_count=2000, pattern="", keep_marker=True):
    """
    解析小说文件，支持多种分段方式

    Args:
        file_path: 文件路径
        split_method: 分段方式（自动分段、按字数分段、按固定文本分段）
        word_count: 每段字数（仅按字数分段时使用）
        pattern: 分段标记（仅按固定文本分段时使用）
        keep_marker: 是否保留分段标记（仅按固定文本分段时使用）

    Returns:
        (段落列表, 状态信息)
    """
    if not file_path:
        return [], "无文件"

    # 先使用现有的解析函数获取完整文本
    paragraphs, status = parse_novel_file(file_path)

    if not paragraphs:
        return paragraphs, status

    # 合并所有段落为完整文本
    full_text = "\n\n".join(paragraphs)

    # 根据分段方式进行处理
    if split_method == "自动分段":
        # 自动分段：直接使用原始段落
        return paragraphs, status
    elif split_method == "按字数分段":
        # 按字数分段
        try:
            segments = split_by_word_count(full_text, word_count)
            return segments, f"按字数分段完成，共 {len(segments)} 段，每段约 {word_count} 字"
        except ValueError as e:
            return [], f"分段失败: {str(e)}"
    elif split_method == "按固定文本分段":
        # 按固定文本分段
        if not pattern or not pattern.strip():
            return [], "请输入分段标记"

        try:
            segments = split_by_pattern(full_text, pattern.strip(), keep_marker)
            return segments, f"按固定文本分段完成，共 {len(segments)} 段"
        except ValueError as e:
            return [], f"分段失败: {str(e)}"
    else:
        return paragraphs, status


# ==================== 大纲生成 ====================
def handle_generate_outline(title: str, genre: str, total_chapters: int, char_setting: str, world_setting: str, plot_idea: str) -> Tuple[str, str]:
    """生成大纲"""
    generator = get_generator()
    outline_text, status = generator.generate_outline(
        title=title,
        genre=genre,
        total_chapters=int(total_chapters) if total_chapters > 0 else 20,
        character_setting=char_setting,
        world_setting=world_setting,
        plot_idea=plot_idea
    )
    
    return outline_text, status


# ==================== 小说生成 ====================
def handle_generate_novel(current_text: str, outline_text: str, title: str, genre: str, char_setting: str, world_setting: str, plot_idea: str, enable_context: bool = False, context_mode: str = "摘要模式", context_chapters: int = 3, context_max_length: int = 1000, progress=gr.Progress()):
    """生成小说（支持续写、暂停、自动保存、字数为0重试、缓存管理、上下文增强）"""
    if not outline_text or not outline_text.strip():
        yield current_text, "错误：大纲为空"
        return

    set_generation_state(True, False)
    generator = get_generator()

    # 解析大纲
    chapters, parse_msg = OutlineParser.parse(outline_text)

    if not chapters:
        logger.error(f"大纲解析失败: {parse_msg}")
        yield current_text, parse_msg
        set_generation_state(False)
        return

    total_chapters = len(chapters)

    # 检查已完成的章节（支持断点续传）
    completed = 0
    import re as regex
    chapter_matches = regex.findall(r'## 第(\d+)章', current_text)
    if chapter_matches:
        completed = max(int(x) for x in chapter_matches)

    # 确保标题存在
    full_text = current_text.strip()
    if not full_text.startswith(f"# {title}"):
        full_text = f"# {title}\n\n" + full_text

    # 创建或更新项目（在生成过程中就能看到）
    project_result = None
    project_id = None

    try:
        # 尝试获取现有项目或创建新项目
        existing_project = ProjectManager.get_project_by_title(title)
        if existing_project:
            from novel_generator import NovelProject
            project_result = NovelProject(
                title=title,
                genre=genre,
                character_setting=char_setting,
                world_setting=world_setting,
                plot_idea=plot_idea
            )
            project_result.id = existing_project['id']
            project_id = existing_project['id']
            # 加载已有的章节数据
            for i in range(len(chapters)):
                if i < len(existing_project.get('chapters', [])):
                    from novel_generator import Chapter
                    ch_data = existing_project['chapters'][i]
                    chapters[i].content = ch_data.get('content', '')
                    chapters[i].word_count = ch_data.get('word_count', 0)
                    chapters[i].generated_at = ch_data.get('generated_at', '')
        else:
            project_result, project_msg = ProjectManager.create_project(
                title=title,
                genre=genre,
                character_setting=char_setting,
                world_setting=world_setting,
                plot_idea=plot_idea
            )
            if project_result:
                project_result.chapters = chapters
                project_id = project_result.id

        # 检查是否有缓存
        cache_data = None
        if project_id:
            cache_data, cache_msg = load_generation_cache(project_id)
            if cache_data:
                logger.info(f"发现缓存: {cache_msg}")
                # 从缓存恢复章节内容
                cached_chapters = cache_data.get('generated_content', {})
                for ch in chapters:
                    if str(ch.num) in cached_chapters:
                        ch.content = cached_chapters[str(ch.num)].get('content', '')
                        ch.word_count = cached_chapters[str(ch.num)].get('word_count', 0)
                        ch.generated_at = cached_chapters[str(ch.num)].get('generated_at', '')
                        logger.info(f"从缓存恢复章节 {ch.num}: {ch.word_count} 字")

        retry_count = 0
        max_retries = 3  # 最大重试次数

        for i in range(completed + 1, total_chapters + 1):
            if should_stop():
                logger.info(f"生成已暂停，已完成 {completed}/{total_chapters} 章")
                # 保存当前进度到项目
                if project_result:
                    project_result.chapters = chapters
                    ProjectManager.save_project(project_result)
                # 保存缓存
                if project_id:
                    cache_data = {
                        "project_id": project_id,
                        "title": title,
                        "current_chapter": completed,
                        "total_chapters": total_chapters,
                        "generated_content": {str(ch.num): ch.to_dict() for ch in chapters},
                        "generation_status": "stopped",
                        "timestamp": datetime.now().isoformat(),
                        "config": {
                            "genre": genre,
                            "character_setting": char_setting,
                            "world_setting": world_setting,
                            "plot_idea": plot_idea
                        }
                    }
                    save_generation_cache(project_id, cache_data)
                yield full_text, f"已暂停 - 已完成 {completed}/{total_chapters} 章，项目已保存"
                return

            chapter = chapters[i - 1]
            progress((i - 1) / total_chapters, desc=f"正在生成第 {i}/{total_chapters} 章：{chapter.title}")

            # 如果章节已生成（从缓存），跳过
            if chapter.content and chapter.content.strip():
                logger.info(f"章节 {i} 已存在，跳过生成")
                chapter_block = f"## 第{i}章: {chapter.title}\n\n{chapter.content}\n\n"
                full_text += chapter_block
                completed = i
                yield full_text, f"已完成 {i}/{total_chapters} 章（从缓存恢复）"
                continue

            # 获取前文以保证连贯性
            previous_content = ""
            if full_text:
                lines = full_text.split('\n')
                previous_content = '\n'.join(lines[-50:])  # 最后50行

            # 构建上下文（如果启用上下文增强）
            context_summary = ""
            if enable_context and i > 1:
                if context_mode == "摘要模式":
                    # 摘要模式：使用前面章节的摘要
                    summaries, summary_msg = load_chapter_summaries(project_id)
                    if summaries:
                        # 根据设置的章节数筛选摘要
                        start_chapter = max(1, i - context_chapters)
                        filtered_summaries = [s for s in summaries if start_chapter <= s.get('chapter_num', 0) < i]
                        
                        # 构建上下文
                        if filtered_summaries:
                            context_summary = build_context_from_summaries(filtered_summaries, context_max_length)
                            logger.info(f"使用摘要模式上下文增强，加载 {len(filtered_summaries)} 个章节摘要")
                elif context_mode == "全文模式":
                    # 全文模式：使用前面所有章节的完整内容
                    full_context_parts = []
                    start_chapter = max(1, i - context_chapters) if context_chapters else 1
                    for ch_idx in range(start_chapter - 1, i - 1):
                        if ch_idx < len(chapters) and chapters[ch_idx].content:
                            full_context_parts.append(f"## 第{chapters[ch_idx].num}章: {chapters[ch_idx].title}\n\n{chapters[ch_idx].content}")
                    
                    if full_context_parts:
                        context_summary = "\n\n".join(full_context_parts)
                        # 限制最大长度
                        if len(context_summary) > context_max_length:
                            context_summary = context_summary[:context_max_length] + "\n\n[内容已截断...]"
                        logger.info(f"使用全文模式上下文增强，加载 {len(full_context_parts)} 个章节的完整内容（{len(context_summary)} 字）")

            # 生成章节内容，支持重试（处理字数为0的情况）
            content = ""
            success_msg = ""
            for attempt in range(max_retries):
                content, success_msg = generator.generate_chapter(
                    chapter_num=i,
                    chapter_title=chapter.title,
                    chapter_desc=chapter.desc,
                    novel_title=title,
                    character_setting=char_setting,
                    world_setting=world_setting,
                    plot_idea=plot_idea,
                    previous_content=previous_content,
                    context_summary=context_summary
                )

                # 检查是否生成成功且字数大于0
                if success_msg == "生成成功" and content and len(content.strip()) > 0:
                    break

                # 如果生成失败或字数为0，记录并重试
                if attempt < max_retries - 1:
                    logger.warning(f"第 {i} 章生成失败或字数为0（尝试 {attempt + 1}/{max_retries}），正在重试...")
                    retry_count += 1
                else:
                    logger.error(f"第 {i} 章生成失败，已达最大重试次数")
                    # 保存缓存以便重试
                    if project_id:
                        cache_data = {
                            "project_id": project_id,
                            "title": title,
                            "current_chapter": completed,
                            "total_chapters": total_chapters,
                            "generated_content": {str(ch.num): ch.to_dict() for ch in chapters},
                            "generation_status": "stopped",
                            "timestamp": datetime.now().isoformat(),
                            "config": {
                                "genre": genre,
                                "character_setting": char_setting,
                                "world_setting": world_setting,
                                "plot_idea": plot_idea
                            }
                        }
                        save_generation_cache(project_id, cache_data)
                    yield full_text, f"生成失败：第 {i} 章生成失败（已重试{max_retries}次）"
                    return

            if not success_msg or success_msg != "生成成功":
                logger.error(f"第 {i} 章生成失败: {success_msg}")
                yield full_text, f"生成失败：{success_msg}"
                return

            # 保存章节内容
            chapter.content = content
            chapter.word_count = len(content)
            from datetime import datetime
            chapter.generated_at = datetime.now().isoformat()
            logger.info(f"章节 {i} 内容已保存: {len(content)} 字")

            # 如果启用上下文增强，生成并保存章节摘要
            if enable_context and success_msg == "生成成功":
                summary, summary_msg = generate_chapter_summary(content, chapter.title)
                if summary_msg == "摘要生成成功":
                    save_success, save_msg = save_chapter_summary(project_id, i, summary)
                    if save_success:
                        logger.info(f"章节 {i} 摘要已保存")
                    else:
                        logger.warning(f"章节 {i} 摘要保存失败: {save_msg}")
                else:
                    logger.warning(f"章节 {i} 摘要生成失败: {summary_msg}")

            chapter_block = f"## 第{i}章: {chapter.title}\n\n{content}\n\n"
            full_text += chapter_block
            completed = i

            # 每生成完一章就自动保存项目（支持断点续传）
            if project_result and i % 1 == 0:  # 每章都保存
                project_result.chapters = chapters
                project_result.updated_at = datetime.now().isoformat()
                save_success, save_msg = ProjectManager.save_project(project_result)
                if save_success:
                    logger.info(f"项目进度已保存: {project_result.id}")

                # 保存缓存
                cache_data = {
                    "project_id": project_id,
                    "title": title,
                    "current_chapter": completed,
                    "total_chapters": total_chapters,
                    "generated_content": {str(ch.num): ch.to_dict() for ch in chapters},
                    "generation_status": "generating",
                    "timestamp": datetime.now().isoformat(),
                    "config": {
                        "genre": genre,
                        "character_setting": char_setting,
                        "world_setting": world_setting,
                        "plot_idea": plot_idea
                    }
                }
                save_generation_cache(project_id, cache_data)

            yield full_text, f"已完成 {i}/{total_chapters} 章"

        logger.info(f"小说生成完成: {title}")

        # 最终保存项目
        if project_result:
            project_result.chapters = chapters
            project_result.updated_at = datetime.now().isoformat()
            save_success, save_msg = ProjectManager.save_project(project_result)

            if save_success:
                logger.info(f"项目最终保存成功: {project_result.id}")
                # 清理缓存
                if project_id:
                    clear_generation_cache(project_id)
                    logger.info(f"缓存已清理: {project_id}")
                yield full_text, f"小说生成完成！已保存至项目库: {project_result.id}"
            else:
                logger.warning(f"项目最终保存失败: {save_msg}")
                yield full_text, f"小说生成完成！（保存失败: {save_msg}）"
        else:
            logger.warning(f"项目创建失败")
            yield full_text, "小说生成完成！（项目保存失败）"

    finally:
        set_generation_state(False)


def handle_export_current_progress(current_text: str, title: str, export_format: str) -> Tuple[Optional[str], str]:
    """导出当前进度"""
    if not current_text or not current_text.strip():
        return None, "❌ 没有内容可导出"

    if not title or not title.strip():
        return None, "❌ 请填写小说标题"

    try:
        # 确定导出格式
        format_map = {
            "Word (.docx)": ("docx", export_to_docx),
            "文本 (.txt)": ("txt", export_to_txt),
            "Markdown (.md)": ("md", export_to_markdown),
            "HTML (.html)": ("html", export_to_html),
        }

        if export_format not in format_map:
            return None, f"❌ 不支持的导出格式: {export_format}"

        file_ext, export_func = format_map[export_format]

        # 调用对应的导出函数
        success, result = export_func(current_text, title)

        if success:
            logger.info(f"当前进度导出成功: {result}")
            return result, f"✅ 导出成功！"
        else:
            logger.error(f"当前进度导出失败: {result}")
            return None, f"❌ 导出失败: {result}"

    except Exception as e:
        logger.error(f"导出过程出错: {e}")
        return None, f"❌ 导出出错: {str(e)}"


def check_cache_status(title: str) -> Tuple[str, str, bool]:
    """检查缓存状态"""
    if not title or not title.strip():
        return "无缓存", "", False

    try:
        # 获取项目
        existing_project = ProjectManager.get_project_by_title(title)
        if not existing_project:
            return "无缓存", "", False

        project_id = existing_project['id']

        # 检查缓存
        cache_data, cache_msg = load_generation_cache(project_id)
        if not cache_data:
            return "无缓存", "", False

        # 返回缓存信息
        current_chapter = cache_data.get('current_chapter', 0)
        total_chapters = cache_data.get('total_chapters', 0)
        status = cache_data.get('generation_status', 'unknown')
        timestamp = cache_data.get('timestamp', '')

        cache_info = f"发现缓存：已完成 {current_chapter}/{total_chapters} 章"
        timestamp_info = f"缓存时间: {timestamp[:19] if timestamp else '未知'}"

        return cache_info, timestamp_info, True

    except Exception as e:
        logger.error(f"检查缓存状态失败: {e}")
        return "检查失败", "", False


def handle_list_caches() -> Tuple[pd.DataFrame, str]:
    """列出所有缓存"""
    try:
        caches = list_generation_caches()
        if not caches:
            return pd.DataFrame(columns=["项目名", "当前章节", "总章节", "状态", "缓存时间", "大小(KB)"]), "暂无缓存"

        df = pd.DataFrame([
            {
                "项目名": c["title"],
                "当前章节": c["current_chapter"],
                "总章节": c["total_chapters"],
                "状态": c["status"],
                "缓存时间": c["timestamp"][:19] if c["timestamp"] else "",
                "大小(KB)": round(c["size"] / 1024, 2)
            }
            for c in caches
        ])
        return df, f"找到 {len(caches)} 个缓存"
    except Exception as e:
        logger.error(f"列出缓存失败: {e}")
        return pd.DataFrame(), f"列出缓存失败: {str(e)}"


def handle_clear_cache(project_id: str) -> Tuple[pd.DataFrame, str]:
    """清理指定项目的缓存"""
    if not project_id or not project_id.strip():
        return pd.DataFrame(), "❌ 请选择要清理的缓存"

    try:
        success, msg = clear_generation_cache(project_id)
        if success:
            # 刷新缓存列表
            return handle_list_caches()
        else:
            return pd.DataFrame(), f"❌ {msg}"
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        return pd.DataFrame(), f"❌ 清理缓存失败: {str(e)}"


def handle_clear_all_caches() -> Tuple[pd.DataFrame, str]:
    """清理所有缓存"""
    try:
        caches = list_generation_caches()
        if not caches:
            return pd.DataFrame(), "❌ 没有缓存可清理"

        cleared_count = 0
        for cache in caches:
            project_id = cache["project_id"]
            success, _ = clear_generation_cache(project_id)
            if success:
                cleared_count += 1

        # 刷新缓存列表
        df, msg = handle_list_caches()
        return df, f"✅ 已清理 {cleared_count}/{len(caches)} 个缓存"
    except Exception as e:
        logger.error(f"清理所有缓存失败: {e}")
        return pd.DataFrame(), f"❌ 清理所有缓存失败: {str(e)}"


def handle_get_cache_size() -> str:
    """获取缓存总大小"""
    try:
        size_bytes = get_cache_size()
        size_mb = size_bytes / (1024 * 1024)
        if size_mb < 1:
            return f"缓存总大小: {round(size_bytes / 1024, 2)} KB"
        else:
            return f"缓存总大小: {round(size_mb, 2)} MB"
    except Exception as e:
        logger.error(f"获取缓存大小失败: {e}")
        return "获取缓存大小失败"


# ==================== 上下文摘要缓存管理 ====================

def handle_list_summary_caches() -> Tuple[pd.DataFrame, str]:
    """列出所有摘要缓存"""
    try:
        caches = list_summary_caches()
        if not caches:
            return pd.DataFrame(columns=["项目ID", "章节数", "总大小(KB)"]), "暂无摘要缓存"

        df = pd.DataFrame([
            {
                "项目ID": c["project_id"],
                "章节数": c["chapter_count"],
                "总大小(KB)": c["size_kb"]
            }
            for c in caches
        ])
        return df, f"找到 {len(caches)} 个摘要缓存"
    except Exception as e:
        logger.error(f"列出摘要缓存失败: {e}")
        return pd.DataFrame(), f"列出摘要缓存失败: {str(e)}"


def handle_get_summary_cache_size() -> str:
    """获取摘要缓存总大小"""
    try:
        size_bytes = get_summary_cache_size()
        size_mb = size_bytes / (1024 * 1024)
        if size_mb < 1:
            return f"摘要缓存总大小: {round(size_bytes / 1024, 2)} KB"
        else:
            return f"摘要缓存总大小: {round(size_mb, 2)} MB"
    except Exception as e:
        logger.error(f"获取摘要缓存大小失败: {e}")
        return "获取摘要缓存大小失败"


def handle_clear_all_summary_caches() -> Tuple[pd.DataFrame, str]:
    """清理所有摘要缓存"""
    try:
        caches = list_summary_caches()
        if not caches:
            return pd.DataFrame(), "❌ 没有摘要缓存可清理"

        cleared_count = 0
        for cache in caches:
            project_id = cache["project_id"]
            success, _ = clear_chapter_summaries(project_id)
            if success:
                cleared_count += 1

        # 刷新摘要缓存列表
        df, msg = handle_list_summary_caches()
        return df, f"✅ 已清理 {cleared_count}/{len(caches)} 个摘要缓存"
    except Exception as e:
        logger.error(f"清理所有摘要缓存失败: {e}")
        return pd.DataFrame(), f"❌ 清理所有摘要缓存失败: {str(e)}"

# ==================== 项目管理 ====================
def load_projects_list():
    """加载项目列表"""
    projects = ProjectManager.list_projects()
    
    if not projects:
        return pd.DataFrame(columns=["项目名", "类型", "创建时间", "更新时间", "章节数", "完成度"]), "暂无项目"
    
    df = pd.DataFrame([
        {
            "项目名": p["title"],
            "类型": p["genre"],
            "创建时间": p["created_at"][:10],
            "更新时间": p["updated_at"][:10],
            "章节数": f"{p['completed_chapters']}/{p['chapter_count']}",
            "完成度": f"{int(p['completed_chapters']/max(p['chapter_count'],1)*100)}%"
        }
        for p in projects
    ])
    
    return df, f"找到 {len(projects)} 个项目"


def get_project_choices():
    """获取项目列表用于下拉框"""
    projects = ProjectManager.list_projects()
    if not projects:
        return []
    return [p["title"] for p in projects]


def handle_export_project(project_title: str, export_format: str) -> Tuple[Optional[str], str]:
    """导出项目小说 - 从metadata.json读取完整内容，返回文件路径供下载"""
    import json
    from pathlib import Path
    from exporter import export_to_docx, export_to_txt, export_to_markdown, export_to_html

    if not project_title or not project_title.strip():
        return None, "❌ 请选择一个项目"

    try:
        # 获取项目信息
        project = ProjectManager.get_project_by_title(project_title)
        if not project:
            return None, f"❌ 项目'{project_title}'不存在"

        # 从metadata.json读取完整项目信息
        project_dir = Path("projects") / project["id"]
        metadata_file = project_dir / "metadata.json"

        if not metadata_file.exists():
            return None, f"❌ 项目元数据文件不存在: {metadata_file}"

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # 构建完整的小说内容（从metadata中的chapters）
        content_parts = []
        content_parts.append(f"# {metadata['title']}")
        content_parts.append("")

        # 添加章节内容
        chapters = metadata.get('chapters', [])
        if chapters:
            for chapter in chapters:
                # 使用章节标题（不包含章节号前缀）
                chapter_title = chapter.get('title', '')
                # 如果标题包含"第X章:"前缀，提取后面的部分
                if re.match(r'^第\d+章[:：]', chapter_title):
                    chapter_title = re.sub(r'^第\d+章[:：]\s*', '', chapter_title).strip()

                content_parts.append(f"## 第{chapter.get('num', 1)}章 {chapter_title}")
                content_parts.append("")

                # 优先使用content（实际生成的内容），如果没有则使用desc（大纲描述）
                chapter_content = chapter.get('content', '').strip()
                if chapter_content and chapter_content not in ['生成成功', '']:
                    content_parts.append(chapter_content)
                else:
                    content_parts.append(f"（大纲描述：{chapter.get('desc', '')}）")
                content_parts.append("")

        novel_content = "\n".join(content_parts)

        # 检查是否有实际内容
        if not novel_content.strip() or novel_content.strip() == f"# {metadata['title']}":
            return None, "❌ 项目没有可导出的内容，请先生成章节内容"

        # 创建导出目录
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)

        # 确定导出格式
        format_map = {
            "Word (.docx)": ("docx", export_to_docx),
            "文本 (.txt)": ("txt", export_to_txt),
            "Markdown (.md)": ("md", export_to_markdown),
            "HTML (.html)": ("html", export_to_html),
        }

        if export_format not in format_map:
            return None, f"❌ 不支持的导出格式: {export_format}"

        file_ext, export_func = format_map[export_format]

        # 调用对应的导出函数
        success, result = export_func(novel_content, project_title)

        if success:
            logger.info(f"项目导出成功: {result}")
            # 将相对路径转换为绝对路径
            if result:
                abs_path = str(Path(result).resolve())
                # 验证文件是否存在
                if Path(abs_path).exists():
                    logger.info(f"文件绝对路径: {abs_path}")
                    return abs_path, f"✅ 导出成功！"
                else:
                    logger.error(f"文件不存在: {abs_path}")
                    return None, f"❌ 导出文件不存在: {result}"
            else:
                return None, f"❌ 导出失败: 未返回文件路径"
        else:
            logger.error(f"项目导出失败: {result}")
            return None, f"❌ 导出失败: {result}"

    except Exception as e:
        logger.error(f"导出过程出错: {e}")
        return None, f"❌ 导出出错: {str(e)}"


# ==================== 配置管理 ====================
def load_backends_table():
    """加载后端配置表格"""
    config = get_config()
    
    if not config.backends:
        empty_df = pd.DataFrame({
            "名称": [""],
            "类型": [""],
            "Base URL": [""],
            "模型": [""],
            "启用": [True],
            "超时(秒)": [30],
            "重试次数": [3]
        })
        return empty_df
    
    data = []
    for backend in config.backends:
        data.append({
            "名称": backend.name,
            "类型": backend.type,
            "Base URL": backend.base_url,
            "模型": backend.model,
            "启用": backend.enabled,
            "超时(秒)": backend.timeout,
            "重试次数": backend.retry_times
        })
    
    df = pd.DataFrame(data)
    
    # 添加空行用于新增
    for _ in range(3):
        df = pd.concat([df, pd.DataFrame({
            "名称": [""],
            "类型": [""],
            "Base URL": [""],
            "模型": [""],
            "启用": [True],
            "超时(秒)": [30],
            "重试次数": [3]
        })], ignore_index=True)
    
    return df


def save_backends_config(temperature, top_p, top_k, max_tokens, target_words, writing_style, writing_tone, character_dev, plot_complexity):
    """保存生成参数"""
    try:
        config = get_config()
        
        # 保存生成参数
        success, msg = config.update_generation_config(
            temperature=float(temperature),
            top_p=float(top_p),
            top_k=int(top_k),
            max_tokens=int(max_tokens),
            chapter_target_words=int(target_words),
            writing_style=str(writing_style),
            writing_tone=str(writing_tone),
            character_development=str(character_dev),
            plot_complexity=str(plot_complexity)
        )
        
        if not success:
            logger.error(f"保存配置失败: {msg}")
            return msg
        
        reinit_api_client()
        logger.info("生成参数已保存")
        return "保存成功"
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return f"保存失败: {str(e)}"


def test_backends_connection():
    """测试后端连接"""
    api_client = get_api_client()
    results = api_client.test_backends()
    
    status_text = "后端连接测试结果：\n"
    for name, success in results.items():
        status = "✓ 可用" if success else "✗ 不可用"
        status_text += f"{name}: {status}\n"
    
    return status_text



# ==================== Web 接口管理函数 ====================

def handle_provider_selection(provider_name):
    """处理API提供商选择，自动填充配置"""
    if not provider_name:
        return gr.update(), gr.update(), gr.update(), gr.update()
    
    provider_key = config.get_api_provider_key_by_name(provider_name)
    if not provider_key:
        return gr.update(), gr.update(), gr.update(), gr.update()
    
    provider_info = config.get_api_provider_info(provider_key)
    if not provider_info:
        return gr.update(), gr.update(), gr.update(), gr.update()
    
    # 自动填充配置
    base_url = provider_info.get("base_url", "")
    model = provider_info.get("default_model", "")
    requires_custom_url = provider_info.get("requires_custom_url", False)
    
    # 如果需要自定义URL，清空base_url让用户填写
    if requires_custom_url:
        base_url = ""
    
    # 根据提供商设置接口类型
    type_mapping = {
        "openai": "openai",
        "openai_compatible": "openai",
        "anthropic": "claude",
        "google": "other",
        "alibaba": "other",
        "deepseek": "openai",
        "zhipu": "openai"
    }
    backend_type = type_mapping.get(provider_key, "openai")
    
    return (
        gr.update(value=base_url),  # 更新base_url
        gr.update(value=model),      # 更新model
        gr.update(value=backend_type), # 更新type
        gr.update(interactive=requires_custom_url) # base_url是否可编辑
    )


def validate_api_key(api_key: str, provider_name: str) -> tuple[bool, str]:
    """验证API密钥格式"""
    if not api_key or not api_key.strip():
        return False, "API密钥不能为空"
    
    provider_key = config.get_api_provider_key_by_name(provider_name)
    if not provider_key:
        return False, "未知的API提供商"
    
    provider_info = config.get_api_provider_info(provider_key)
    if not provider_info:
        return False, "未知的API提供商"
    
    # 根据提供商验证密钥格式
    if provider_key == "openai":
        if not api_key.startswith("sk-"):
            return False, "OpenAI API密钥应该以'sk-'开头"
    elif provider_key == "anthropic":
        if not api_key.startswith("sk-ant-"):
            return False, "Anthropic API密钥应该以'sk-ant-'开头"
    elif provider_key == "google":
        if len(api_key) < 20:
            return False, "Google API密钥格式不正确"
    elif provider_key in ["alibaba", "deepseek", "zhipu"]:
        if len(api_key) < 10:
            return False, "API密钥格式不正确"
    
    return True, "密钥格式验证通过"


def validate_model_name(model: str, provider_name: str) -> tuple[bool, str]:
    """验证模型名称"""
    if not model or not model.strip():
        return False, "模型名称不能为空"
    
    provider_key = config.get_api_provider_key_by_name(provider_name)
    if not provider_key:
        return False, "未知的API提供商"
    
    provider_info = config.get_api_provider_info(provider_key)
    if not provider_info:
        return False, "未知的API提供商"
    
    # 基本验证：模型名称应该包含字母、数字、下划线、点或连字符
    import re
    if not re.match(r'^[a-zA-Z0-9._-]+$', model):
        return False, "模型名称只能包含字母、数字、下划线、点和连字符"
    
    return True, "模型名称验证通过"


def refresh_backends_list():
    """刷新后端列表"""
    result = config_api.list_backends()
    if result["success"]:
        backends = result["data"]
        df_data = pd.DataFrame(backends)
        return df_data, "✅ 已刷新后端列表"
    else:
        return pd.DataFrame(), f"❌ {result['message']}"


def add_new_backend(name, backend_type, base_url, api_key, model, timeout, retry_times, enabled, provider_name=None):
    """添加新的后端"""
    if not name or not base_url or not model:
        return pd.DataFrame(), "❌ 请填写所有必填字段（名称、URL、模型）"

    # 非ollama类型必须填写api_key
    if backend_type != "ollama" and not api_key:
        return pd.DataFrame(), "❌ 该类型接口必须填写API密钥"

    # 如果是ollama且未填写api_key，使用默认值
    if backend_type == "ollama" and not api_key:
        api_key = "ollama"

    # 如果选择了API提供商，进行验证
    if provider_name:
        # 验证API密钥
        key_valid, key_msg = validate_api_key(api_key, provider_name)
        if not key_valid:
            return pd.DataFrame(), f"❌ {key_msg}"
        
        # 验证模型名称
        model_valid, model_msg = validate_model_name(model, provider_name)
        if not model_valid:
            return pd.DataFrame(), f"❌ {model_msg}"

    result = config_api.add_backend(
        name=name,
        type=backend_type,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=int(timeout) if timeout else 30,
        retry_times=int(retry_times) if retry_times else 3,
        enabled=enabled
    )

    if result["success"]:
        # 刷新列表
        backends_result = config_api.list_backends()
        if backends_result["success"]:
            df_data = pd.DataFrame(backends_result["data"])
            return df_data, f"✅ {result['message']}"
        return pd.DataFrame(), f"✅ {result['message']}"
    else:
        return pd.DataFrame(), f"❌ {result['message']}"


def test_single_backend(backend_name):
    """测试单个后端连接"""
    if not backend_name:
        return "❌ 请输入后端名称"
    
    result = config_api.test_backend(backend_name)
    if result["success"]:
        return f"✅ {result['message']}"
    else:
        return f"❌ {result['message']}"


def delete_backend_by_name(backend_name):
    """删除后端"""
    if not backend_name:
        return pd.DataFrame(), "❌ 请输入要删除的后端名称"
    
    result = config_api.delete_backend(backend_name)
    
    if result["success"]:
        backends_result = config_api.list_backends()
        if backends_result["success"]:
            df_data = pd.DataFrame(backends_result["data"])
            return df_data, f"✅ {result['message']}"
        return pd.DataFrame(), f"✅ {result['message']}"
    else:
        return pd.DataFrame(), f"❌ {result['message']}"


def toggle_backend_status(backend_name, enabled):
    """启用/禁用后端"""
    if not backend_name:
        return pd.DataFrame(), "❌ 请输入后端名称"
    
    result = config_api.toggle_backend(backend_name, enabled)
    
    if result["success"]:
        backends_result = config_api.list_backends()
        if backends_result["success"]:
            df_data = pd.DataFrame(backends_result["data"])
            return df_data, f"✅ {result['message']}"
        return pd.DataFrame(), f"✅ {result['message']}"
    else:
        return pd.DataFrame(), f"❌ {result['message']}"


# ==================== Gradio UI ====================
with gr.Blocks(title="AI小说创作工具 Pro - 生产级版本") as demo:
    gr.Markdown("# AI小说创作工具 Pro")
    gr.Markdown("_生产级别的智能小说创作系统 v4.0 正式版_")
    
    # ==================== Tab 1: 小说重写 ====================
    with gr.Tab("📝 小说重写"):
        gr.Markdown("### 上传小说 → 选择模式 → 智能处理")

        # 模式选择
        mode_radio = gr.Radio(
            choices=["重写模式", "续写模式"],
            value="重写模式",
            label="功能模式",
            interactive=True
        )

        # 重写模式界面
        with gr.Group() as rewrite_group:
            gr.Markdown("#### 🔄 重写模式：上传小说 → 选择风格 → 智能重写")

            with gr.Row():
                with gr.Column(scale=1):
                    file_input = gr.File(label="📤 上传文件 (txt/pdf/epub/md/docx)", file_types=[".txt", ".pdf", ".epub", ".md", ".docx"])

                    # 分段方式选择
                    split_method_rewrite = gr.Radio(
                        choices=["自动分段", "按字数分段", "按固定文本分段"],
                        value="自动分段",
                        label="分段方式",
                        interactive=True
                    )

                    # 按字数分段的参数
                    with gr.Group(visible=False) as word_count_group_rewrite:
                        word_count_rewrite = gr.Number(
                            label="每段字数",
                            value=2000,
                            minimum=100,
                            maximum=100000,
                            info="按字数均匀分段"
                        )

                    # 按固定文本分段的参数
                    with gr.Group(visible=False) as pattern_group_rewrite:
                        pattern_rewrite = gr.Textbox(
                            label="分段标记",
                            placeholder="支持变量：%章、%节、%回，或自定义文本如---、***等",
                            info="使用%章匹配'第X章'，%节匹配'第X节'，%回匹配'第X回'"
                        )
                        keep_marker_rewrite = gr.Checkbox(
                            label="保留分段标记",
                            value=True,
                            info="是否在分段中保留标记文本"
                        )

                    parse_btn = gr.Button("解析文件", variant="primary")

                with gr.Column(scale=2):
                    style_dropdown = gr.Dropdown(
                        choices=list(PRESET_TEMPLATES.keys()),
                        value="重写风格 - 默认",
                        label="预设风格",
                        interactive=True
                    )

            parse_status = gr.Textbox(label="解析状态", interactive=False)

            segments = gr.State([])
            rewritten_parts = gr.State([])

            with gr.Row():
                rewrite_btn = gr.Button("开始重写", variant="primary", scale=1)
                stop_rewrite_btn = gr.Button("停止重写", variant="stop", scale=1)

            with gr.Row():
                preview = gr.Textbox(label="实时预览", lines=20, interactive=False)
                full_rewritten = gr.Textbox(label="完整重写文本（可编辑）", lines=20, interactive=True)

            rewrite_stats = gr.Textbox(label="进度统计", interactive=False)

        # 续写模式界面
        with gr.Group(visible=False) as continue_group:
            gr.Markdown("#### ✍️ 续写模式：上传已有小说 → AI智能续写")

            with gr.Row():
                with gr.Column(scale=1):
                    continue_file_input = gr.File(label="📤 上传已有小说 (txt/pdf/epub/md/docx)", file_types=[".txt", ".pdf", ".epub", ".md", ".docx"])

                    # 分段方式选择
                    split_method_continue = gr.Radio(
                        choices=["自动分段", "按字数分段", "按固定文本分段"],
                        value="自动分段",
                        label="分段方式",
                        interactive=True
                    )

                    # 按字数分段的参数
                    with gr.Group(visible=False) as word_count_group_continue:
                        word_count_continue = gr.Number(
                            label="每段字数",
                            value=2000,
                            minimum=100,
                            maximum=100000,
                            info="按字数均匀分段"
                        )

                    # 按固定文本分段的参数
                    with gr.Group(visible=False) as pattern_group_continue:
                        pattern_continue = gr.Textbox(
                            label="分段标记",
                            placeholder="支持变量：%章、%节、%回，或自定义文本如---、***等",
                            info="使用%章匹配'第X章'，%节匹配'第X节'，%回匹配'第X回'"
                        )
                        keep_marker_continue = gr.Checkbox(
                            label="保留分段标记",
                            value=True,
                            info="是否在分段中保留标记文本"
                        )

                    continue_parse_btn = gr.Button("解析文件", variant="primary")

                with gr.Column(scale=2):
                    continue_title = gr.Textbox(label="📖 小说标题", placeholder="输入小说标题")
                    continue_target_words = gr.Number(label="📊 目标字数", value=2500, minimum=500, maximum=65536)

            # 设定信息
            with gr.Row():
                continue_char_setting = gr.Textbox(label="👥 人物设定", lines=2, placeholder="主角姓名、性格、背景等（可选）")
                continue_world_setting = gr.Textbox(label="🌍 世界观设定", lines=2, placeholder="时代背景、世界规则等（可选）")

            continue_plot_idea = gr.Textbox(label="📖 主线剧情想法", lines=3, placeholder="核心冲突、发展方向、结局走向等（可选）")

            continue_parse_status = gr.Textbox(label="解析状态", interactive=False)
            continue_segments = gr.State([])

            continue_btn = gr.Button("开始续写", variant="primary", scale=2)

            with gr.Row():
                continue_original = gr.Textbox(label="已有内容（可编辑）", lines=20, interactive=True)
                continue_result = gr.Textbox(label="续写结果", lines=20, interactive=True)

            continue_status = gr.Textbox(label="续写状态", interactive=False)

        # 模式切换
        def toggle_mode(mode):
            if mode == "重写模式":
                return gr.update(visible=True), gr.update(visible=False)
            else:
                return gr.update(visible=False), gr.update(visible=True)

        mode_radio.change(
            toggle_mode,
            inputs=[mode_radio],
            outputs=[rewrite_group, continue_group]
        )

        # 事件绑定 - 重写模式
        # 分段方式切换
        def update_split_ui_rewrite(split_method):
            if split_method == "按字数分段":
                return gr.update(visible=True), gr.update(visible=False)
            elif split_method == "按固定文本分段":
                return gr.update(visible=False), gr.update(visible=True)
            else:
                return gr.update(visible=False), gr.update(visible=False)

        split_method_rewrite.change(
            update_split_ui_rewrite,
            inputs=[split_method_rewrite],
            outputs=[word_count_group_rewrite, pattern_group_rewrite]
        )

        # 解析文件（使用新的分段函数）
        parse_btn.click(
            parse_novel_file_with_split,
            inputs=[file_input, split_method_rewrite, word_count_rewrite, pattern_rewrite, keep_marker_rewrite],
            outputs=[segments, parse_status]
        )
        stop_rewrite_btn.click(request_stop, outputs=[rewrite_stats, stop_rewrite_btn])

        rewrite_btn.click(
            handle_rewrite,
            inputs=[segments, rewritten_parts, style_dropdown],
            outputs=[preview, full_rewritten, rewritten_parts, rewrite_stats],
            show_progress=True
        )

        # 事件绑定 - 续写模式
        # 分段方式切换
        def update_split_ui_continue(split_method):
            if split_method == "按字数分段":
                return gr.update(visible=True), gr.update(visible=False)
            elif split_method == "按固定文本分段":
                return gr.update(visible=False), gr.update(visible=True)
            else:
                return gr.update(visible=False), gr.update(visible=False)

        split_method_continue.change(
            update_split_ui_continue,
            inputs=[split_method_continue],
            outputs=[word_count_group_continue, pattern_group_continue]
        )

        # 解析文件（使用新的分段函数）
        continue_parse_btn.click(
            parse_novel_file_with_split,
            inputs=[continue_file_input, split_method_continue, word_count_continue, pattern_continue, keep_marker_continue],
            outputs=[continue_segments, continue_parse_status]
        )

        # 当解析完成后，将内容填充到已有内容框
        continue_parse_btn.click(
            lambda segments: "\n\n".join(segments) if segments else "",
            inputs=[continue_segments],
            outputs=[continue_original]
        )

        continue_btn.click(
            handle_continue_writing,
            inputs=[continue_original, continue_title, continue_char_setting, continue_world_setting, continue_plot_idea, continue_target_words],
            outputs=[continue_result, continue_status]
        )

    # ==================== Tab 1.5: 小说润色 ====================
    with gr.Tab("✨ 小说润色"):
        gr.Markdown("### 上传小说 → 选择润色类型 → 智能优化")

        with gr.Row():
            with gr.Column(scale=1):
                polish_file_input = gr.File(label="📤 上传文件 (txt/pdf/epub/md/docx)", file_types=[".txt", ".pdf", ".epub", ".md", ".docx"])

                # 分段方式选择
                split_method_polish = gr.Radio(
                    choices=["自动分段", "按字数分段", "按固定文本分段"],
                    value="自动分段",
                    label="分段方式",
                    interactive=True
                )

                # 按字数分段的参数
                with gr.Group(visible=False) as word_count_group_polish:
                    word_count_polish = gr.Number(
                        label="每段字数",
                        value=2000,
                        minimum=100,
                        maximum=100000,
                        info="按字数均匀分段"
                    )

                # 按固定文本分段的参数
                with gr.Group(visible=False) as pattern_group_polish:
                    pattern_polish = gr.Textbox(
                        label="分段标记",
                        placeholder="支持变量：%章、%节、%回，或自定义文本如---、***等",
                        info="使用%章匹配'第X章'，%节匹配'第X节'，%回匹配'第X回'"
                    )
                    keep_marker_polish = gr.Checkbox(
                        label="保留分段标记",
                        value=True,
                        info="是否在分段中保留标记文本"
                    )

                polish_parse_btn = gr.Button("解析文件", variant="primary")

            with gr.Column(scale=2):
                polish_type_dropdown = gr.Dropdown(
                    choices=["全面润色", "查找错误", "改进建议", "直接修改", "去除AI味", "增强细节", "优化对话", "改善节奏"],
                    value="全面润色",
                    label="润色类型",
                    interactive=True
                )

        polish_custom_req = gr.Textbox(
            label="自定义要求（可选）",
            placeholder="例如：加强人物性格描写、增加环境氛围、优化对话流畅度等",
            lines=2
        )

        polish_parse_status = gr.Textbox(label="解析状态", interactive=False)

        polish_segments = gr.State([])

        with gr.Row():
            polish_btn = gr.Button("开始润色", variant="primary", scale=1)
            polish_all_btn = gr.Button("润色并提供建议", variant="primary", scale=1)

        with gr.Row():
            original_text = gr.Textbox(label="原文（可编辑）", lines=20, interactive=True)
            polished_text = gr.Textbox(label="润色结果", lines=20, interactive=True)

        polish_suggestions = gr.Textbox(label="改进建议", lines=5, interactive=False)
        polish_status = gr.Textbox(label="润色状态", interactive=False)

        # 事件绑定
        # 分段方式切换
        def update_split_ui_polish(split_method):
            if split_method == "按字数分段":
                return gr.update(visible=True), gr.update(visible=False)
            elif split_method == "按固定文本分段":
                return gr.update(visible=False), gr.update(visible=True)
            else:
                return gr.update(visible=False), gr.update(visible=False)

        split_method_polish.change(
            update_split_ui_polish,
            inputs=[split_method_polish],
            outputs=[word_count_group_polish, pattern_group_polish]
        )

        # 解析文件（使用新的分段函数）
        polish_parse_btn.click(
            parse_novel_file_with_split,
            inputs=[polish_file_input, split_method_polish, word_count_polish, pattern_polish, keep_marker_polish],
            outputs=[polish_segments, polish_parse_status]
        )

        # 简单润色
        polish_btn.click(
            handle_polish,
            inputs=[original_text, polish_type_dropdown, polish_custom_req],
            outputs=[polished_text, polish_status],
            show_progress=True
        )

        # 润色并提供建议
        polish_all_btn.click(
            handle_polish_with_suggestions,
            inputs=[original_text, polish_custom_req],
            outputs=[polished_text, polish_suggestions, polish_status],
            show_progress=True
        )

        # 当解析完成后，将内容填充到原文框
        polish_parse_btn.click(
            lambda segments: "\n\n".join(segments) if segments else "",
            inputs=[polish_segments],
            outputs=[original_text]
        )
    
    # ==================== Tab 2: 小说创作 ====================
    with gr.Tab("✍️ 从零开始创作"):
        gr.Markdown("### 填写设定 → 生成大纲 → 自动创作（支持续写、暂停）")

        with gr.Row():
            title_input = gr.Textbox(label="📖 小说标题", value="未命名小说")
            genre_input = gr.Dropdown(
                ["玄幻仙侠", "都市言情", "科幻", "武侠", "悬疑", "历史", "军事", "游戏", "恐怖", "其他"],
                label="📚 小说类型",
                value="玄幻仙侠"
            )

        with gr.Row():
            char_input = gr.Textbox(label="👥 人物设定", lines=3, placeholder="主角姓名、性格、背景等")
            world_input = gr.Textbox(label="🌍 世界观设定", lines=3, placeholder="时代背景、世界规则、特色设置等")

        plot_input = gr.Textbox(label="📖 主线剧情想法", lines=4, placeholder="核心冲突、发展方向、结局走向等")

        with gr.Row():
            total_chapters = gr.Number(label="📊 章节数目（留空为20）", value=20, minimum=1)
            gen_outline_btn = gr.Button("生成大纲", variant="primary")

        outline_display = gr.Textbox(label="📋 大纲（可手动编辑）", lines=10, interactive=True)

        # 上下文增强设置
        gr.Markdown("---")
        gr.Markdown("### 🔄 上下文增强设置（可选）")

        with gr.Row():
            enable_context = gr.Checkbox(
                label="启用上下文增强",
                value=False,
                info="开启后，将使用前面章节的摘要/全文作为生成新章节的上下文"
            )

        with gr.Row():
            context_mode = gr.Radio(
                choices=["摘要模式", "全文模式"],
                value="摘要模式",
                label="上下文模式",
                info="摘要模式：使用前面章节的摘要；全文模式：使用前面所有章节的完整内容"
            )

        with gr.Group(visible=False) as context_summary_group:
            context_chapters = gr.Number(
                label="上下文章节数",
                value=3,
                minimum=1,
                maximum=10,
                info="使用前面多少章的摘要作为上下文"
            )
            context_max_length = gr.Number(
                label="上下文最大长度",
                value=1000,
                minimum=500,
                maximum=5000,
                info="上下文的最大字符数"
            )
        
        gr.Markdown("""
#### 📝 大纲格式说明
请按以下格式编写大纲（任选其一）：

**格式1** (推荐)：
- 第1章: 开篇 - 介绍主人公和世界观
- 第2章: 冲突 - 主人公遇到第一个重大挑战

**格式2**：
- 1. 开篇 - 介绍主人公和世界观
- 2. 冲突 - 主人公遇到第一个重大挑战

**注意**: 标题和描述用英文破折号 `-` 分隔，每行一章
""")
        
        with gr.Row():
            start_gen_btn = gr.Button("开始生成 / 续写", variant="primary", scale=2)
            pause_gen_btn = gr.Button("暂停生成", variant="stop", scale=1)

        # 缓存状态显示
        cache_status_display = gr.Textbox(label="💾 缓存状态", value="无缓存", interactive=False, lines=2)
        cache_timestamp_display = gr.Textbox(label="⏰ 缓存时间", value="", interactive=False)

        # 导出当前进度
        with gr.Row():
            export_progress_format = gr.Radio(
                choices=["Word (.docx)", "文本 (.txt)", "Markdown (.md)", "HTML (.html)"],
                value="Word (.docx)",
                label="📄 导出格式"
            )
            export_progress_btn = gr.Button("📥 导出当前进度", variant="secondary")

        export_progress_file = gr.File(label="下载文件")
        export_progress_status = gr.Textbox(label="导出状态", interactive=False)

        novel_display = gr.Textbox(label="📚 小说正文（实时更新）", lines=20, interactive=True)
        gen_status = gr.Textbox(label="生成状态", value="就绪", interactive=False)
        
        # 事件绑定
        gen_outline_btn.click(
            handle_generate_outline,
            inputs=[title_input, genre_input, total_chapters, char_input, world_input, plot_input],
            outputs=[outline_display, gen_status]
        )

        # 检查缓存状态（当标题改变时）
        title_input.change(
            check_cache_status,
            inputs=[title_input],
            outputs=[cache_status_display, cache_timestamp_display]
        )

        # 根据上下文模式显示/隐藏摘要设置
        def update_context_ui(enable_context, context_mode):
            if enable_context and context_mode == "摘要模式":
                return gr.update(visible=True)
            else:
                return gr.update(visible=False)

        enable_context.change(
            update_context_ui,
            inputs=[enable_context, context_mode],
            outputs=[context_summary_group]
        )

        context_mode.change(
            update_context_ui,
            inputs=[enable_context, context_mode],
            outputs=[context_summary_group]
        )

        start_gen_btn.click(
            handle_generate_novel,
            inputs=[novel_display, outline_display, title_input, genre_input, char_input, world_input, plot_input, enable_context, context_mode, context_chapters, context_max_length],
            outputs=[novel_display, gen_status]
        )

        pause_gen_btn.click(request_stop, outputs=[gen_status, pause_gen_btn])

        # 导出当前进度
        export_progress_btn.click(
            handle_export_current_progress,
            inputs=[novel_display, title_input, export_progress_format],
            outputs=[export_progress_file, export_progress_status]
        )
    
    # ==================== Tab 3: 导出与分享 ====================
    with gr.Tab("💾 导出与分享"):
        gr.Markdown("### 将创作导出为多种格式")
        
        novel_content = gr.Textbox(label="粘贴小说内容", lines=10, placeholder="从创作页面复制完整小说文本")
        export_title = gr.Textbox(label="小说标题", placeholder="用于文件名")
        
        with gr.Row():
            export_docx_btn = gr.Button("导出为 Word (.docx)", variant="primary")
            export_txt_btn = gr.Button("导出为纯文本 (.txt)", variant="primary")
            export_md_btn = gr.Button("导出为 Markdown (.md)", variant="primary")
            export_html_btn = gr.Button("导出为网页 (.html)", variant="primary")
        
        export_file = gr.File(label="下载文件")
        export_status = gr.Textbox(label="导出状态", interactive=False)
        
        export_files_df = gr.Dataframe(label="最近导出的文件", interactive=False)
        
        # 事件绑定
        export_docx_btn.click(
            lambda text, title: export_to_docx(text, title) if text else (None, "内容为空"),
            inputs=[novel_content, export_title],
            outputs=[export_file, export_status]
        )
        
        export_txt_btn.click(
            lambda text, title: export_to_txt(text, title) if text else (None, "内容为空"),
            inputs=[novel_content, export_title],
            outputs=[export_file, export_status]
        )
        
        export_md_btn.click(
            lambda text, title: export_to_markdown(text, title) if text else (None, "内容为空"),
            inputs=[novel_content, export_title],
            outputs=[export_file, export_status]
        )
        
        export_html_btn.click(
            lambda text, title: export_to_html(text, title) if text else (None, "内容为空"),
            inputs=[novel_content, export_title],
            outputs=[export_file, export_status]
        )
        
        gr.Button("刷新文件列表").click(
            lambda: pd.DataFrame(list_export_files()),
            outputs=export_files_df
        )
    
    # ==================== Tab 4: 项目管理 ====================
    with gr.Tab("📂 项目管理"):
        gr.Markdown("### 管理所有创作项目")

        refresh_btn = gr.Button("🔄 刷新项目列表")
        projects_df = gr.Dataframe(label="我的项目", interactive=False)
        status_text = gr.Textbox(label="状态", interactive=False)

        refresh_btn.click(load_projects_list, outputs=[projects_df, status_text])

        # 初始加载
        demo.load(load_projects_list, outputs=[projects_df, status_text])
        
        # ========== 导出功能 ==========
        gr.Markdown("### 📥 导出项目")

        with gr.Row():
            project_select = gr.Dropdown(
                choices=get_project_choices(),
                label="📖 选择要导出的项目",
                interactive=True
            )
            export_format = gr.Radio(
                choices=["Word (.docx)", "文本 (.txt)", "Markdown (.md)", "HTML (.html)"],
                value="Word (.docx)",
                label="📄 导出格式"
            )

        with gr.Row():
            export_btn = gr.Button("📥 导出项目", variant="primary", scale=2)

        export_file = gr.File(label="下载文件")
        export_status = gr.Textbox(label="导出状态", interactive=False, lines=2)

        # 绑定导出事件 - 返回文件路径供下载
        export_btn.click(
            handle_export_project,
            inputs=[project_select, export_format],
            outputs=[export_file, export_status]
        )
        
        # 刷新项目列表时同步更新导出下拉框
        refresh_btn.click(
            lambda: gr.update(choices=get_project_choices()),
            outputs=[project_select]
        )

    # ==================== Tab 5: 系统设置 ====================
    with gr.Tab("⚙️ 系统设置"):
        gr.Markdown("### 🔧 API 接口配置与写作参数")
        
        # 创建子标签
        with gr.Tabs():
            # ========== 接口管理子标签 ==========
            with gr.Tab("🌐 接口管理"):
                gr.Markdown("#### 📋 配置后端接口")
                
                with gr.Row():
                    refresh_btn = gr.Button("🔄 刷新列表", variant="secondary", scale=1)
                    test_all_btn = gr.Button("✅ 测试所有接口", variant="secondary", scale=1)
                
                # 显示已有的接口列表
                backends_df = gr.Dataframe(
                    value=load_backends_table(),
                    label="已配置的后端列表",
                    interactive=False,
                    wrap=True
                )
                
                gr.Markdown("#### ➕ 添加新接口")
                
                with gr.Row():
                    add_provider = gr.Dropdown(
                        choices=config.get_api_provider_choices(),
                        label="API提供商",
                        info="选择API提供商后自动填充默认配置"
                    )
                    add_name = gr.Textbox(label="接口名称*", placeholder="例如: 我的OpenAI")
                
                with gr.Row():
                    add_type = gr.Dropdown(
                        choices=config_api.get_backend_types(),
                        value="openai",
                        label="接口类型*"
                    )
                    add_base_url = gr.Textbox(
                        label="Base URL",
                        placeholder="例如: https://api.example.com/v1（仅OpenAI兼容接口需要填写）"
                    )
                
                with gr.Row():
                    add_model = gr.Textbox(
                        label="模型名称*",
                        placeholder="选择提供商后自动填充，可修改"
                    )
                    add_api_key = gr.Textbox(
                        label="API Key (Ollama可留空)*",
                        type="password",
                        placeholder="输入您的API密钥（不会被明文保存）"
                    )
                
                with gr.Row():
                    add_timeout = gr.Number(
                        value=30,
                        label="超时时间(秒)",
                        minimum=5,
                        maximum=3600
                    )
                    add_retry = gr.Number(
                        value=3,
                        label="重试次数",
                        minimum=1,
                        maximum=10
                    )
                
                with gr.Row():
                    add_enabled = gr.Checkbox(value=True, label="启用此接口")
                    add_btn = gr.Button("➕ 添加接口", variant="primary")
                
                add_status = gr.Textbox(label="操作结果", interactive=False)
                
                gr.Markdown("---")
                gr.Markdown("#### 🔍 测试与管理")
                
                with gr.Row():
                    test_name = gr.Textbox(
                        label="要测试的接口名称",
                        placeholder="输入接口名称来测试连接"
                    )
                    test_btn = gr.Button("🧪 测试连接", variant="secondary")
                
                test_result = gr.Textbox(label="测试结果", interactive=False, lines=3)
                
                with gr.Row():
                    delete_name = gr.Textbox(
                        label="要删除的接口名称",
                        placeholder="输入接口名称来删除"
                    )
                    delete_btn = gr.Button("🗑️ 删除接口", variant="stop")
                
                delete_status = gr.Textbox(label="删除结果", interactive=False)
                
                # 事件绑定
                refresh_btn.click(refresh_backends_list, outputs=[backends_df, add_status])
                
                # API提供商选择事件
                add_provider.change(
                    handle_provider_selection,
                    inputs=[add_provider],
                    outputs=[add_base_url, add_model, add_type, add_base_url]
                )
                
                add_btn.click(
                    add_new_backend,
                    inputs=[add_name, add_type, add_base_url, add_api_key, add_model, 
                            add_timeout, add_retry, add_enabled, add_provider],
                    outputs=[backends_df, add_status]
                )
                test_btn.click(test_single_backend, inputs=[test_name], outputs=[test_result])
                test_all_btn.click(test_backends_connection, outputs=[test_result])
                delete_btn.click(delete_backend_by_name, inputs=[delete_name], 
                                outputs=[backends_df, delete_status])
            
            # ========== 生成参数子标签 ==========
            with gr.Tab("📝 生成参数"):
                gr.Markdown("#### 调整小说生成的各项参数")
                
                config = get_config()
                
                with gr.Row():
                    temp_slider = gr.Slider(
                        0.1, 2.0,
                        value=config.generation.temperature,
                        step=0.1,
                        label="Temperature (创意度)",
                        info="越高越有创意，越低越保守"
                    )
                    topp_slider = gr.Slider(
                        0.1, 1.0,
                        value=config.generation.top_p,
                        step=0.1,
                        label="Top P",
                        info="控制输出的多样性"
                    )
                
                with gr.Row():
                    topk_slider = gr.Slider(
                        1, 100,
                        value=config.generation.top_k,
                        step=1,
                        label="Top K",
                        info="从最可能的K个token中选择"
                    )
                    maxtokens_num = gr.Number(
                        value=config.generation.max_tokens,
                        label="Max Tokens",
                        minimum=100,
                        maximum=100000,
                        info="每次生成的最大token数"
                    )
                
                target_words = gr.Number(
                    value=config.generation.chapter_target_words,
                    label="每章目标字数",
                    minimum=500,
                    maximum=65536
                )
                
                with gr.Row():
                    style_dd = gr.Dropdown(
                        ["流畅自然，情节紧凑，人物刻画细腻",
                         "文笔优美，意境深远",
                         "快节奏，情节跌宕起伏",
                         "细腻描写，情感丰富",
                         "诙谐趣味，轻松活泼"],
                        value=config.generation.writing_style,
                        label="写作风格"
                    )
                    tone_dd = gr.Dropdown(
                        ["中立", "严肃", "轻松", "怀疑", "温和", "激情"],
                        value=config.generation.writing_tone,
                        label="语调"
                    )
                
                with gr.Row():
                    char_dd = gr.Dropdown(
                        ["详细", "中等", "简洁"],
                        value=config.generation.character_development,
                        label="人物塑造"
                    )
                    plot_dd = gr.Dropdown(
                        ["简单", "中等", "复杂"],
                        value=config.generation.plot_complexity,
                        label="情节复杂度"
                    )
                
                save_btn = gr.Button("💾 保存生成参数", variant="primary")
                save_status = gr.Textbox(label="保存状态", interactive=False)
                
                # 事件绑定
                save_btn.click(
                    save_backends_config,
                    inputs=[temp_slider, topp_slider, topk_slider, maxtokens_num,
                            target_words, style_dd, tone_dd, char_dd, plot_dd],
                    outputs=[save_status]
                )

            # ========== 缓存管理子标签 ==========
            with gr.Tab("💾 缓存管理"):
                gr.Markdown("#### 📋 管理生成缓存")

                # 显示缓存总大小
                cache_size_display = gr.Textbox(label="缓存大小", value="", interactive=False)

                with gr.Row():
                    list_caches_btn = gr.Button("🔄 刷新缓存列表", variant="secondary", scale=1)
                    get_cache_size_btn = gr.Button("📊 获取缓存大小", variant="secondary", scale=1)

                caches_df = gr.Dataframe(label="缓存列表", interactive=False)

                with gr.Row():
                    clear_selected_cache_btn = gr.Button("🗑️ 清理选中缓存", variant="stop", scale=1)
                    clear_all_caches_btn = gr.Button("🗑️ 清理所有缓存", variant="stop", scale=1)

                cache_operation_status = gr.Textbox(label="操作状态", interactive=False, lines=2)

                # 事件绑定
                list_caches_btn.click(handle_list_caches, outputs=[caches_df, cache_operation_status])
                get_cache_size_btn.click(handle_get_cache_size, outputs=[cache_size_display])
                clear_selected_cache_btn.click(handle_clear_cache, inputs=[gr.State("")], outputs=[caches_df, cache_operation_status])
                clear_all_caches_btn.click(handle_clear_all_caches, outputs=[caches_df, cache_operation_status])

                gr.Markdown("---")
                gr.Markdown("#### 📋 管理上下文摘要缓存")

                # 显示摘要缓存总大小
                summary_cache_size_display = gr.Textbox(label="摘要缓存大小", value="", interactive=False)

                with gr.Row():
                    list_summary_caches_btn = gr.Button("🔄 刷新摘要列表", variant="secondary", scale=1)
                    get_summary_cache_size_btn = gr.Button("📊 获取摘要大小", variant="secondary", scale=1)

                summary_caches_df = gr.Dataframe(label="摘要缓存列表", interactive=False)

                with gr.Row():
                    clear_summary_cache_btn = gr.Button("🗑️ 清理所有摘要缓存", variant="stop", scale=1)

                summary_cache_operation_status = gr.Textbox(label="操作状态", interactive=False, lines=2)

                # 事件绑定
                list_summary_caches_btn.click(handle_list_summary_caches, outputs=[summary_caches_df, summary_cache_operation_status])
                get_summary_cache_size_btn.click(handle_get_summary_cache_size, outputs=[summary_cache_size_display])
                clear_summary_cache_btn.click(handle_clear_all_summary_caches, outputs=[summary_caches_df, summary_cache_operation_status])


    # ==================== Tab 7: 关于 ====================
    with gr.Tab("ℹ️ 关于"):
        gr.Markdown("""
# AI小说创作工具 Pro v4.0 正式版
## 生产级别的智能小说创作系统

### 🌟 主要功能
- **智能创作**: 从零开始创作长篇小说，支持自定义大纲
- **断点续传**: 支持暂停后续写，每章自动保存，生成中途也能在项目管理中看到
- **智能重写**: 上传已有小说文本，用17种预设风格进行高质量重写
- **智能续写**: 新增续写模式，上传别人写一半的小说，AI自动续写后续内容
- **小说润色**: 全新的润色功能，支持全面润色、查找错误、改进建议、去除AI味等8种润色类型
- **灵活文件解析**: 支持自定义章节模板，可识别各种格式的小说文件
- **多格式导出**: 支持 Word、TXT、Markdown、HTML 等多种格式，导出可直接下载
- **项目管理**: 管理多个创作项目，支持断点续写，自动保存进度
- **灵活配置**: 支持多个 API 后端，Ollama密钥可选配置，细粒度的创作参数调整
- **错误重试**: 生成章节时字数为0会自动重试，确保每章都有内容
- **端口自动查找**: 默认端口被占用时自动查找可用端口

### 🔧 技术特性
- **错误恢复**: 完整的错误处理和日志系统
- **缓存机制**: 智能缓存避免重复调用 API
- **速率限制**: 内置令牌桶算法防止 API 限流
- **负载均衡**: 多后端自动轮询
- **性能监控**: 实时性能统计和分析
- **线程安全**: 完全的并发安全设计

### 🆕 v4.0 新增功能
1. **断点续传**: 小说生成支持暂停后续写，每章自动保存
2. **字数为0重试**: 章节生成失败或字数为0时自动重试3次
3. **17种重写风格**: 新增古代宫斗、现代军事、历史演义等多种风格
4. **智能续写模式**: 上传别人写一半的小说，AI自动续写后续内容
5. **小说润色模块**: 全新润色功能，支持8种润色类型
6. **灵活章节解析**: 支持5种预设模板和自定义章节格式
7. **Ollama优化**: Ollama接口的API Key现在可以留空
8. **直接下载**: 项目导出现在支持直接下载，无需到文件夹查找
9. **端口自动查找**: 默认端口被占用时自动查找可用端口
10. **打包支持**: 支持打包成exe，无需Python环境也可运行

### 📋 系统要求
- Python 3.8+
- 依赖: gradio, pandas, openai, python-docx
- 可选: PyMuPDF (PDF支持), ebooklib+beautifulsoup4 (EPUB支持)

### 📦 打包成exe
使用 `python build_exe.py` 命令可将应用打包成Windows可执行文件
详见 `打包说明.md`

### 📞 技术支持
- 查看日志文件: `logs/` 目录
- 项目保存位置: `projects/` 目录
- 导出文件位置: `exports/` 目录
- 缓存位置: `cache/` 目录
- GitHub: [GitHub](https://github.com/yangqi1309134997-coder/ai-novel-generator)
- 幻城云笔记: [幻城云笔记](https://hcnote.cn/)

### ⚖️ 许可证
MIT License
""")


# ==================== 启动应用 ====================
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("AI小说创作工具 Pro v4.0 正式版启动")
    logger.info("=" * 60)

    # 查找可用端口
    available_port = find_available_port(WEB_PORT)
    if available_port != WEB_PORT:
        logger.warning(f"端口 {WEB_PORT} 被占用，使用端口 {available_port}")
        WEB_PORT = available_port

    # 测试初始化
    try:
        api_client = get_api_client()
        backends = get_config().get_enabled_backends()
        logger.info(f"已加载 {len(backends)} 个后端")

        if not backends:
            logger.warning("⚠️  没有启用的后端！请在设置中添加 API 配置")
    except Exception as e:
        logger.error(f"初始化失败: {e}")

    # 启动Web应用
    logger.info(f"启动Gradio应用... (端口: {WEB_PORT})")
    # Gradio 6.0+ 中 queue 参数在 launch 中配置
    demo.queue(max_size=WEB_QUEUE_MAX)
    try:
        demo.launch(
            server_name=WEB_HOST,
            server_port=WEB_PORT,
            share=False,
            show_error=WEB_SHOW_ERRORS,
            max_threads=WEB_CONCURRENCY,
            theme=gr.themes.Soft()
        )
    except Exception as e:
        logger.exception(f"Gradio 启动失败: {e}")
        raise
