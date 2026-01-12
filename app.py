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
from typing import List, Tuple, Optional
import os
import re

# 导入各个模块
from config import get_config, Backend
from logger import setup_logger, get_logger, get_performance_monitor
from api_client import get_api_client, reinit_api_client
from file_parser import parse_novel_file
from novel_generator import get_generator, OutlineParser, PRESET_TEMPLATES
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


# ==================== 重写功能 ====================
def handle_rewrite(paragraphs: List[str], rewritten_parts: List[str], style_template: str, progress=gr.Progress()):
    """处理段落重写（支持暂停续写）"""
    if not paragraphs:
        yield "", "", [], "无内容可重写"
        return
    
    set_generation_state(True, False)
    generator = get_generator()
    start_idx = len(rewritten_parts)
    total = len(paragraphs)
    
    try:
        for i in range(start_idx, total):
            if should_stop():
                logger.info(f"重写已暂停，已完成 {len(rewritten_parts)}/{total} 段")
                yield "\n\n".join(rewritten_parts), "\n\n".join(rewritten_parts), rewritten_parts[:], f"已暂停 - 完成 {len(rewritten_parts)}/{total} 段"
                return
            
            progress((i + 1 - start_idx) / (total - start_idx), desc=f"重写第 {i+1}/{total} 段")
            
            success, content = generator.rewrite_paragraph(paragraphs[i], style_template)
            
            if not success:
                logger.error(f"第 {i+1} 段重写失败: {content}")
                yield "\n\n".join(rewritten_parts), "\n\n".join(rewritten_parts), rewritten_parts[:], content
                return
            
            rewritten_parts.append(content)
            full = "\n\n".join(rewritten_parts)
            stats = f"进度 {len(rewritten_parts)}/{total} | 约 {sum(len(p) for p in rewritten_parts)} 字"
            yield full, full, rewritten_parts[:], stats
        
        logger.info("重写完成")
        yield full, full, rewritten_parts[:], stats + " | 重写完成"
    
    finally:
        set_generation_state(False)


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
def handle_generate_novel(current_text: str, outline_text: str, title: str, genre: str, char_setting: str, world_setting: str, plot_idea: str, progress=gr.Progress()):
    """生成小说（支持续写和暂停）"""
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
    
    # 检查已完成的章节
    completed = 0
    import re as regex
    chapter_matches = regex.findall(r'## 第(\d+)章', current_text)
    if chapter_matches:
        completed = max(int(x) for x in chapter_matches)
    
    # 确保标题存在
    full_text = current_text.strip()
    if not full_text.startswith(f"# {title}"):
        full_text = f"# {title}\n\n" + full_text
    
    try:
        for i in range(completed + 1, total_chapters + 1):
            if should_stop():
                logger.info(f"生成已暂停，已完成 {completed}/{total_chapters} 章")
                yield full_text, f"已暂停 - 已完成 {completed}/{total_chapters} 章"
                return
            
            chapter = chapters[i - 1]
            progress((i - 1) / total_chapters, desc=f"正在生成第 {i}/{total_chapters} 章：{chapter.title}")
            
            # 获取前文以保证连贯性
            previous_content = ""
            if full_text:
                lines = full_text.split('\n')
                previous_content = '\n'.join(lines[-50:])  # 最后50行
            
            content, success = generator.generate_chapter(
                chapter_num=i,
                chapter_title=chapter.title,
                chapter_desc=chapter.desc,
                novel_title=title,
                character_setting=char_setting,
                world_setting=world_setting,
                plot_idea=plot_idea,
                previous_content=previous_content
            )
            
            if not success:
                logger.error(f"第 {i} 章生成失败: {content}")
                yield full_text, f"生成失败：{content}"
                return
            
            # 直接保存API返回的内容到chapter对象
            chapter.content = content
            chapter.word_count = len(content)
            from datetime import datetime
            chapter.generated_at = datetime.now().isoformat()
            logger.info(f"章节 {i} 内容已保存: {len(content)} 字")
            
            chapter_block = f"## 第{i}章: {chapter.title}\n\n{content}\n\n"
            full_text += chapter_block
            completed = i
            
            yield full_text, f"已完成 {i}/{total_chapters} 章"
        
        logger.info(f"小说生成完成: {title}")
        
        # ==================== 自动保存项目 ====================
        # 创建并保存项目到ProjectManager
        project_result, project_msg = ProjectManager.create_project(
            title=title,
            genre=genre,  # 使用实际的类型参数
            character_setting=char_setting,
            world_setting=world_setting,
            plot_idea=plot_idea
        )
        
        if project_result:
            # 将生成的章节信息关联到项目对象
            from datetime import datetime
            
            # 更新项目的章节和时间戳
            project_result.chapters = chapters
            project_result.updated_at = datetime.now().isoformat()
            
            # 保存项目到磁盘
            save_success, save_msg = ProjectManager.save_project(project_result)
            
            if save_success:
                logger.info(f"项目保存成功: {project_result.id}")
                yield full_text, f"小说生成完成！已保存至项目库: {project_result.id}"
            else:
                logger.warning(f"项目保存失败: {save_msg}")
                yield full_text, f"小说生成完成！（保存失败: {save_msg}）"
        else:
            logger.warning(f"项目创建失败: {project_msg}")
            yield full_text, "小说生成完成！（项目保存失败）"    
    finally:
        set_generation_state(False)

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


def handle_export_project(project_title: str, export_format: str) -> str:
    """导出项目小说 - 从metadata.json读取完整内容"""
    import json
    from pathlib import Path
    from exporter import export_to_docx, export_to_txt, export_to_markdown, export_to_html
    
    if not project_title or not project_title.strip():
        return "❌ 请选择一个项目"

    try:
        # 获取项目信息
        project = ProjectManager.get_project_by_title(project_title)
        if not project:
            return f"❌ 项目'{project_title}'不存在"

        # 从metadata.json读取完整项目信息
        project_dir = Path("projects") / project["id"]
        metadata_file = project_dir / "metadata.json"
        
        if not metadata_file.exists():
            return f"❌ 项目元数据文件不存在: {metadata_file}"
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 构建完整的小说内容（从metadata中的chapters）
        content_parts = []
        content_parts.append(f"# {metadata['title']}")
        content_parts.append("")
        
        # 添加项目信息
        content_parts.append("## 项目信息")
        content_parts.append(f"- 类型: {metadata.get('genre', '未设置')}")
        content_parts.append(f"- 角色设定: {metadata.get('character_setting', '未设置')}")
        content_parts.append(f"- 世界观: {metadata.get('world_setting', '未设置')}")
        content_parts.append(f"- 剧情概要: {metadata.get('plot_idea', '未设置')}")
        content_parts.append("")
        
        # 添加章节内容
        chapters = metadata.get('chapters', [])
        if chapters:
            content_parts.append("## 正文")
            content_parts.append("")
            for chapter in chapters:
                # 使用章节标题（不包含章节号前缀）
                chapter_title = chapter.get('title', '')
                # 如果标题包含"第X章:"前缀，提取后面的部分
                if re.match(r'^第\d+章[:：]', chapter_title):
                    chapter_title = re.sub(r'^第\d+章[:：]\s*', '', chapter_title).strip()
                
                content_parts.append(f"### 第{chapter.get('num', 1)}章 {chapter_title}")
                content_parts.append("")
                
                # 优先使用content（实际生成的内容），如果没有则使用desc（大纲描述）
                chapter_content = chapter.get('content', '').strip()
                if chapter_content and chapter_content not in ['生成成功', '']:
                    content_parts.append(chapter_content)
                else:
                    content_parts.append(f"（大纲描述：{chapter.get('desc', '')}）")
                content_parts.append("")
        else:
            content_parts.append("## 正文")
            content_parts.append("")
            content_parts.append("暂无章节内容")
        
        novel_content = "\n".join(content_parts)
        
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
            return f"❌ 不支持的导出格式: {export_format}"

        file_ext, export_func = format_map[export_format]
        output_file = export_dir / f"{project_title}.{file_ext}"

        # 调用对应的导出函数
        success, msg = export_func(novel_content, project_title)

        if success:
            logger.info(f"项目导出成功: {output_file}")
            return f"✅ 导出成功！\n文件位置: {output_file}"
        else:
            logger.error(f"项目导出失败: {msg}")
            return f"❌ 导出失败: {msg}"

    except Exception as e:
        logger.error(f"导出过程出错: {e}")
        return f"❌ 导出出错: {str(e)}"


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

def refresh_backends_list():
    """刷新后端列表"""
    result = config_api.list_backends()
    if result["success"]:
        backends = result["data"]
        df_data = pd.DataFrame(backends)
        return df_data, "✅ 已刷新后端列表"
    else:
        return pd.DataFrame(), f"❌ {result['message']}"


def add_new_backend(name, backend_type, base_url, api_key, model, timeout, retry_times, enabled):
    """添加新的后端"""
    if not name or not base_url or not api_key or not model:
        return pd.DataFrame(), "❌ 请填写所有必填字段（名称、URL、API Key、模型）"
    
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
    gr.Markdown("_生产级别的智能小说创作系统 v2.0_")
    
    # ==================== Tab 1: 小说重写 ====================
    with gr.Tab("📝 小说重写"):
        gr.Markdown("### 上传小说 → 选择风格 → 智能重写")
        
        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(label="📤 上传文件 (txt/pdf/epub)", file_types=[".txt", ".pdf", ".epub"])
                parse_btn = gr.Button("解析文件", variant="primary")
            
            with gr.Column(scale=2):
                style_dropdown = gr.Dropdown(
                    choices=list(PRESET_TEMPLATES.keys()),
                    value="重写风格 - 默认",
                    label="预设风格"
                )
                custom_style = gr.Textbox(
                    label="自定义风格提示",
                    placeholder="留空则使用预设，或自定义风格要求",
                    lines=2
                )
        
        parse_status = gr.Textbox(label="解析状态", interactive=False)
        
        segments = gr.State([])
        rewritten_parts = gr.State([])
        
        with gr.Row():
            rewrite_btn = gr.Button("开始重写", variant="primary", scale=1)
            stop_rewrite_btn = gr.Button("停止重写", variant="stop", scale=1)
        
        with gr.Row():
            preview = gr.Textbox(label="实时预览", lines=8, interactive=False)
            full_rewritten = gr.Textbox(label="完整重写文本（可编辑）", lines=8, interactive=True)
        
        rewrite_stats = gr.Textbox(label="进度统计", interactive=False)
        
        # 事件绑定
        parse_btn.click(parse_novel_file, inputs=file_input, outputs=[segments, parse_status])
        stop_rewrite_btn.click(request_stop, outputs=[rewrite_stats, stop_rewrite_btn])
        rewrite_btn.click(
            handle_rewrite,
            inputs=[segments, rewritten_parts, custom_style],
            outputs=[preview, full_rewritten, rewritten_parts, rewrite_stats]
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
        
        novel_display = gr.Textbox(label="📚 小说正文（实时更新）", lines=15, interactive=True)
        gen_status = gr.Textbox(label="生成状态", value="就绪", interactive=False)
        
        # 事件绑定
        gen_outline_btn.click(
            handle_generate_outline,
            inputs=[title_input, genre_input, total_chapters, char_input, world_input, plot_input],
            outputs=[outline_display, gen_status]
        )
        
        start_gen_btn.click(
            handle_generate_novel,
            inputs=[novel_display, outline_display, title_input, genre_input, char_input, world_input, plot_input],
            outputs=[novel_display, gen_status]
        )
        
        pause_gen_btn.click(request_stop, outputs=[gen_status, pause_gen_btn])
    
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
        
        export_status = gr.Textbox(label="导出状态", interactive=False, lines=2)
        
        # 绑定导出事件
        export_btn.click(
            handle_export_project,
            inputs=[project_select, export_format],
            outputs=[export_status]
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
                    add_name = gr.Textbox(label="接口名称*", placeholder="例如: GLM-API")
                    add_type = gr.Dropdown(
                        choices=config_api.get_backend_types(),
                        value="openai",
                        label="接口类型*"
                    )
                
                with gr.Row():
                    add_base_url = gr.Textbox(
                        label="Base URL*",
                        placeholder="例如: https://api.example.com/v1"
                    )
                    add_model = gr.Textbox(
                        label="模型名称*",
                        placeholder="例如: gpt-4 或 glm-4"
                    )
                
                add_api_key = gr.Textbox(
                    label="API Key*",
                    type="password",
                    placeholder="输入您的API密钥（不会被明文保存）"
                )
                
                with gr.Row():
                    add_timeout = gr.Number(
                        value=30,
                        label="超时时间(秒)",
                        minimum=5,
                        maximum=10000
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
                add_btn.click(
                    add_new_backend,
                    inputs=[add_name, add_type, add_base_url, add_api_key, add_model, 
                            add_timeout, add_retry, add_enabled],
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
                    maximum=10000
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


    # ==================== Tab 6: 关于 ====================
    with gr.Tab("ℹ️ 关于"):
        gr.Markdown("""
# AI小说创作工具 Pro v2.0
## 生产级别的智能小说创作系统

### 🌟 主要功能
- **智能创作**: 从零开始创作长篇小说，支持自定义大纲
- **智能重写**: 上传已有小说文本，用多种风格进行高质量重写
- **多格式导出**: 支持 Word、TXT、Markdown、HTML 等多种格式
- **项目管理**: 管理多个创作项目，支持断点续写
- **灵活配置**: 支持多个 API 后端，细粒度的创作参数调整

### 🔧 技术特性
- **错误恢复**: 完整的错误处理和日志系统
- **缓存机制**: 智能缓存避免重复调用 API
- **速率限制**: 内置令牌桶算法防止 API 限流
- **负载均衡**: 多后端自动轮询
- **性能监控**: 实时性能统计和分析
- **线程安全**: 完全的并发安全设计

### 📋 系统要求
- Python 3.8+
- 依赖: gradio, pandas, openai, python-docx
- 可选: PyMuPDF (PDF支持), ebooklib+beautifulsoup4 (EPUB支持)

### 📞 技术支持
- 查看日志文件: `logs/` 目录
- 项目保存位置: `projects/` 目录
- 导出文件位置: `exports/` 目录
- 缓存位置: `cache/` 目录

### ⚖️ 许可证
MIT License
""")


# ==================== 启动应用 ====================
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("AI小说创作工具 Pro v2.0 启动")
    logger.info("=" * 60)
    
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
    logger.info("启动Gradio应用...")
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
