"""
AI Novel Generator 4.5 - 主应用
集成连贯性系统、提示词系统、统一API客户端

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""

import gradio as gr
import logging
import threading
import json
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import os

# 导入新的系统
from src.api import UnifiedAPIClient, create_api_client, get_api_client
from src.core.coherence import (
    CharacterTracker,
    PlotManager,
    WorldDatabase,
    ContextBuilder,
    CoherenceValidator,
    build_context_for_generation,
    validate_chapter_coherence
)
from src.core.prompts import PromptManager
from src.config.providers import ProviderFactory, PRESET_PROVIDERS

# 导入功能模块
from .features import (
    create_polish_ui,
    create_rewrite_ui,
    create_cache_manager_ui,
    create_params_config_ui,
    create_auto_generation_ui,
    AutoNovelGenerator
)
from .components.coherence_viz import CoherenceVizUI

# ==================== 日志配置 ====================

# 创建日志目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 配置根日志记录器
def setup_logging():
    """配置日志系统"""
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 文件处理器 - 主日志（INFO级别）
    main_log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(main_log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # 文件处理器 - 调试日志（DEBUG级别，用于详细诊断）
    debug_log_file = log_dir / f"debug_{datetime.now().strftime('%Y%m%d')}.log"
    debug_handler = logging.FileHandler(debug_log_file, encoding='utf-8')
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)

    # 文件处理器 - 错误日志
    error_log_file = log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(debug_handler)
    root_logger.addHandler(error_handler)

    # 关闭第三方库的DEBUG日志，减少噪音
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('gradio').setLevel(logging.INFO)

    # 返回当前模块的日志记录器
    return logging.getLogger(__name__)

# 设置日志
logger = setup_logging()
logger.info("=" * 60)
logger.info("AI Novel Generator 4.5 - 日志系统初始化完成")
logger.info(f"日志目录: {log_dir.absolute()}")

# 获取当前日期字符串
date_str = datetime.now().strftime('%Y%m%d')
logger.info(f"主日志文件: {log_dir / f'app_{date_str}.log'}")
logger.info(f"错误日志文件: {log_dir / f'error_{date_str}.log'}")
logger.info("=" * 60)

# 环境变量配置
# 默认使用 0.0.0.0 让局域网可访问，如需仅本地访问请设置环境变量 NOVEL_TOOL_HOST=127.0.0.1
WEB_HOST = os.getenv("NOVEL_TOOL_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("NOVEL_TOOL_PORT", os.getenv("PORT", "7860")))
WEB_SHARE = os.getenv("NOVEL_TOOL_SHARE", "false").lower() in ("1", "true", "yes")


# ==================== 全局状态管理 ====================

class AppState:
    """应用状态管理"""

    def __init__(self):
        # 生成状态
        self.is_generating = False
        self.stop_requested = False
        self.lock = threading.Lock()

        # 当前项目
        self.current_project_id: Optional[str] = None
        self.current_project_data: Optional[Dict] = None

        # 连贯性系统
        self.character_tracker: Optional[CharacterTracker] = None
        self.plot_manager: Optional[PlotManager] = None
        self.world_db: Optional[WorldDatabase] = None

        # 提示词系统
        self.prompt_manager: Optional[PromptManager] = None

        # API客户端
        self.api_client: Optional[UnifiedAPIClient] = None

        # 自动生成器
        self.auto_generator: Optional[AutoNovelGenerator] = None

        # 项目管理器
        self.project_dir = Path("projects")
        self.project_dir.mkdir(exist_ok=True)

    def init_coherence_systems(self, project_id: str):
        """初始化连贯性系统"""
        logger.info(f"[应用] 初始化连贯性系统: {project_id}")
        cache_dir = Path("cache/coherence")
        self.character_tracker = CharacterTracker(project_id, cache_dir)
        self.plot_manager = PlotManager(project_id, cache_dir)
        self.world_db = WorldDatabase(project_id, cache_dir)
        logger.info(f"[应用] 连贯性系统已初始化: {project_id}")

    def init_prompt_system(self):
        """初始化提示词系统"""
        logger.info("[应用] 初始化提示词系统")
        config_dir = Path("config")
        self.prompt_manager = PromptManager(config_dir)
        logger.info("[应用] 提示词系统已初始化")

    def init_api_client(self, provider_configs: List[Dict]):
        """初始化API客户端"""
        logger.info(f"[应用] 初始化API客户端，提供商数量: {len(provider_configs)}")
        self.api_client = create_api_client(provider_configs)
        logger.info("[应用] API客户端已初始化")

    def load_api_config(self) -> bool:
        """
        加载API配置并初始化客户端

        Returns:
            是否成功加载配置
        """
        config_file = Path("config/user_config.json")
        if not config_file.exists():
            logger.info("[应用] 未找到API配置文件，跳过自动加载")
            return False

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            providers = config.get("providers", [])
            if not providers:
                logger.info("[应用] API配置中没有提供商配置")
                return False

            # 初始化API客户端
            self.init_api_client(providers)
            logger.info(f"[应用] 已自动加载 {len(providers)} 个API提供商配置")
            return True

        except Exception as e:
            logger.error(f"[应用] 加载API配置失败: {e}", exc_info=True)
            return False

    def init_auto_generator(self, project_id: Optional[str] = None):
        """初始化自动生成器"""
        if not self.api_client:
            logger.warning("API客户端未初始化，无法创建自动生成器")
            return

        if not self.prompt_manager:
            self.init_prompt_system()

        # 从生成参数配置中读取max_tokens
        max_tokens = 20000  # 默认值
        gen_config_file = Path("config/generation_config.json")
        if gen_config_file.exists():
            try:
                with open(gen_config_file, 'r', encoding='utf-8') as f:
                    gen_config = json.load(f)
                    max_tokens = gen_config.get("max_tokens", 20000)
                    logger.info(f"从生成参数配置读取max_tokens: {max_tokens}")
            except Exception as e:
                logger.warning(f"读取生成参数配置失败: {e}，使用默认值20000")

        # 如果有project_id，先初始化连贯性系统
        if project_id and not self.character_tracker:
            self.init_coherence_systems(project_id)

        coherence_system = {
            "character_tracker": self.character_tracker,
            "plot_manager": self.plot_manager,
            "world_db": self.world_db
        }

        self.auto_generator = AutoNovelGenerator(
            api_client=self.api_client,
            prompt_manager=self.prompt_manager,
            coherence_system=coherence_system,
            project_dir=self.project_dir,
            outline_max_tokens=max_tokens  # 使用生成参数配置的max_tokens
        )
        logger.info("自动生成器已初始化")


# 全局应用状态
app_state = AppState()


# ==================== 项目管理 ====================

def create_new_project(
    title: str,
    genre: str,
    character_setting: str,
    world_setting: str,
    plot_idea: str,
    chapter_count: int
) -> Tuple[str, str]:
    """
    创建新项目

    Returns:
        (状态消息, 项目ID)
    """
    try:
        # 生成项目ID
        project_id = datetime.now().strftime("%Y%m%d-%H%M%S")

        # 创建项目数据
        project_data = {
            "id": project_id,
            "title": title,
            "genre": genre,
            "character_setting": character_setting,
            "world_setting": world_setting,
            "plot_idea": plot_idea,
            "chapter_count": chapter_count,
            "chapters": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # 保存项目文件
        project_file = app_state.project_dir / f"{project_id}.json"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

        # 初始化连贯性系统
        app_state.init_coherence_systems(project_id)

        # 提取世界观设定
        if app_state.api_client and app_state.world_db:
            from src.core.coherence import extract_world_setting_from_chapter
            extract_world_setting_from_chapter(
                world_setting,
                0,
                app_state.world_db,
                app_state.api_client
            )

        # 更新状态
        app_state.current_project_id = project_id
        app_state.current_project_data = project_data

        logger.info(f"项目创建成功: {title} (ID: {project_id})")
        return f"✓ 项目创建成功：{title}", project_id

    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        return f"✗ 创建项目失败: {str(e)}", ""


def load_project(project_id: str) -> Tuple[str, Dict]:
    """
    加载项目

    Returns:
        (状态消息, 项目数据)
    """
    try:
        project_file = app_state.project_dir / f"{project_id}.json"

        if not project_file.exists():
            return f"✗ 项目文件不存在: {project_id}", {}

        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)

        # 初始化连贯性系统
        app_state.init_coherence_systems(project_id)

        # 更新状态
        app_state.current_project_id = project_id
        app_state.current_project_data = project_data

        logger.info(f"项目加载成功: {project_id}")
        return f"✓ 项目加载成功：{project_data.get('title', project_id)}", project_data

    except Exception as e:
        logger.error(f"加载项目失败: {e}")
        return f"✗ 加载项目失败: {str(e)}", {}


def list_projects():
    """
    列出所有项目（支持新旧两种格式）

    Returns:
        list: 列表格式，每行包含 [ID, 标题, 类型, 创建时间, 章节数]
    """
    projects = []

    # 列出新版格式（JSON文件在根目录）
    for project_file in app_state.project_dir.glob("*.json"):
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
                created_at = project_data.get("created_at", "")
                # 格式化时间显示
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at)
                        created_at = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass

                projects.append([
                    project_data.get("id", project_file.stem),
                    project_data.get("title", ""),
                    project_data.get("genre", ""),
                    created_at,
                    len(project_data.get("chapters", []))
                ])
        except Exception as e:
            logger.warning(f"读取项目文件失败 {project_file}: {e}")

    # 列出旧版格式（子目录）
    for project_dir in app_state.project_dir.iterdir():
        if project_dir.is_dir() and project_dir.name != "backups":
            metadata_file = project_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        created_at = metadata.get("created_at", "")
                        # 格式化时间显示
                        if created_at:
                            try:
                                dt = datetime.fromisoformat(created_at)
                                created_at = dt.strftime("%Y-%m-%d %H:%M")
                            except:
                                pass

                        projects.append([
                            project_dir.name,
                            metadata.get("title", "未命名"),
                            metadata.get("genre", ""),
                            created_at,
                            len(metadata.get("chapters", []))
                        ])
                except Exception as e:
                    logger.warning(f"读取旧版项目失败 {project_dir}: {e}")

    # 按创建时间倒序排序（索引3是创建时间）
    projects.sort(key=lambda x: x[3] if x[3] else "", reverse=True)

    logger.info(f"列出 {len(projects)} 个项目")
    return projects


def list_project_titles():
    """
    列出所有项目标题（用于下拉框）

    Returns:
        list: 项目标题列表
    """
    projects = list_projects()
    # 提取标题（索引1），过滤掉空标题
    titles = [p[1] for p in projects if p and len(p) > 1 and p[1]]
    logger.debug(f"列出 {len(titles)} 个项目标题")
    return titles


def delete_project(project_id: str) -> Tuple[bool, str]:
    """
    删除项目（支持新旧两种格式）

    Args:
        project_id: 项目ID

    Returns:
        (成功标志, 状态信息)
    """
    try:
        # 尝试新版格式（JSON文件）
        project_file = app_state.project_dir / f"{project_id}.json"
        if project_file.exists():
            import shutil
            # 删除JSON文件
            project_file.unlink()
            # 检查是否有子目录（旧版格式遗留）
            project_dir = app_state.project_dir / project_id
            if project_dir.exists():
                shutil.rmtree(project_dir)
            return True, f"项目已删除: {project_id}"

        # 尝试旧版格式（子目录）
        project_dir = app_state.project_dir / project_id
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
            return True, f"项目已删除: {project_id}"

        return False, f"项目不存在: {project_id}"

    except Exception as e:
        logger.error(f"删除项目失败: {e}")
        return False, f"删除项目失败: {str(e)}"


def export_project(project_id: str, export_format: str = "json") -> Tuple[Optional[str], str]:
    """
    导出项目（支持新旧两种格式）

    Args:
        project_id: 项目ID
        export_format: 导出格式 (json/docx/txt/md/html)

    Returns:
        (文件路径, 状态信息)
    """
    try:
        # 创建导出目录
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)

        # 加载项目数据
        project_data = None
        project_file = app_state.project_dir / f"{project_id}.json"

        if project_file.exists():
            # 新版格式
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
        else:
            # 旧版格式
            project_dir = app_state.project_dir / project_id
            metadata_file = project_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    # 转换为新版格式
                    project_data = {
                        "id": project_id,
                        "title": metadata.get("title", ""),
                        "genre": metadata.get("genre", ""),
                        "character_setting": metadata.get("character_setting", ""),
                        "world_setting": metadata.get("world_setting", ""),
                        "plot_idea": metadata.get("plot_idea", ""),
                        "created_at": metadata.get("created_at", ""),
                        "updated_at": metadata.get("updated_at", ""),
                        "chapters": metadata.get("chapters", [])
                    }

        if not project_data:
            return None, f"项目不存在: {project_id}"

        title = project_data.get("title", "未命名")
        chapters = project_data.get("chapters", [])

        if export_format == "json":
            # 导出为JSON
            filename = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = export_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)

            return str(filepath), f"项目已导出: {filename}"

        elif export_format in ["docx", "txt", "md", "html"]:
            # 导出为文本格式（使用exporter模块）
            try:
                from exporter import export_to_docx, export_to_txt, export_to_markdown, export_to_html

                # 构建完整文本
                full_text = f"# {title}\n\n"
                for chapter in chapters:
                    if chapter.get("content"):
                        full_text += f"## 第{chapter['num']}章 {chapter.get('title', '')}\n\n"
                        full_text += chapter["content"] + "\n\n"

                # 导出 - exporter函数返回 (filepath, message)
                if export_format == "docx":
                    filepath, message = export_to_docx(full_text, title)
                elif export_format == "txt":
                    filepath, message = export_to_txt(full_text, title)
                elif export_format == "md":
                    filepath, message = export_to_markdown(full_text, title)
                elif export_format == "html":
                    filepath, message = export_to_html(full_text, title)
                else:
                    return None, f"不支持的导出格式: {export_format}"

                if filepath:
                    return filepath, message  # ✅ 返回文件路径和消息
                else:
                    return None, message  # ✅ 失败时返回None和错误消息

            except ImportError:
                return None, "导出功能需要安装exporter模块"
            except Exception as e:
                logger.error(f"导出失败: {e}")
                return None, f"导出失败: {str(e)}"

        else:
            return None, f"不支持的导出格式: {export_format}"

    except Exception as e:
        logger.error(f"导出项目失败: {e}")
        return None, f"导出项目失败: {str(e)}"


# ==================== 章节生成（集成连贯性系统）====================

def generate_chapter(
    chapter_num: int,
    chapter_title: str,
    chapter_desc: str,
    target_words: int,
    use_coherence: bool = True,
    generation_style: str = "默认",
    custom_prompt: str = "",
    progress=None
) -> Tuple[str, str, str]:
    """
    生成章节（集成连贯性系统）

    Args:
        chapter_num: 章节号
        chapter_title: 章节标题
        chapter_desc: 章节描述
        target_words: 目标字数
        use_coherence: 是否使用连贯性系统
        generation_style: 写作风格
        custom_prompt: 自定义提示词

    Returns:
        (生成内容, 状态消息, 验证报告)
    """
    if not app_state.api_client:
        return "", "✗ API客户端未初始化", ""

    if not app_state.current_project_data:
        return "", "✗ 请先创建或加载项目", ""

    try:
        project = app_state.current_project_data

        # 构建上下文
        context = ""
        if use_coherence and app_state.character_tracker:
            context = build_context_for_generation(
                current_chapter=chapter_num,
                chapter_outline=chapter_desc,
                chapter_desc=chapter_desc,
                character_tracker=app_state.character_tracker,
                plot_manager=app_state.plot_manager,
                world_db=app_state.world_db,
                api_client=app_state.api_client,
                max_length=2000
            )

        # 获取提示词模板（根据选择的风格）
        template = None
        if app_state.prompt_manager:
            template = app_state.prompt_manager.get_template(
                "generation",
                generation_style
            )

        if not template:
            template = """请根据以下信息生成小说章节：

【小说信息】
标题：{title}
类型：{genre}

【本章信息】
章节：第{chapter_num}章 - {chapter_title}
大纲：{chapter_desc}

【前文回顾】
{context}

【写作要求】
- 【严格字数要求】必须生成 {target_words} 字左右（误差不超过±{words_tolerance}字）
- 绝对不能超过 {max_words} 字，也不能少于 {min_words} 字
- 字数控制是第一要务，宁可内容紧凑也不得超字数
- 保持与前文的连贯性
- 人物性格保持一致

【字数控制提示】
在创作过程中请自觉控制字数：
- 如果目标{target_words}字，请确保内容刚好覆盖这个长度
- 避免过度描写和冗长叙述
- 每个场景聚焦核心情节

请开始创作："""

        # 应用变量
        # 计算严格的字数范围
        words_tolerance = max(100, int(target_words * 0.1))  # 10%误差，最少100字
        min_words = target_words - words_tolerance
        max_words = target_words + words_tolerance

        variables = {
            "title": project.get("title", ""),
            "genre": project.get("genre", ""),
            "chapter_num": chapter_num,
            "chapter_title": chapter_title,
            "chapter_desc": chapter_desc,
            "context": context,
            "target_words": target_words,
            "words_tolerance": words_tolerance,
            "min_words": min_words,
            "max_words": max_words
        }

        if app_state.prompt_manager:
            prompt = app_state.prompt_manager.apply_variables(template, variables)
        else:
            # 简单替换
            prompt = template
            for key, value in variables.items():
                prompt = prompt.replace(f"{{{key}}}", str(value))

        # 添加自定义提示词
        if custom_prompt and custom_prompt.strip():
            prompt += f"\n\n【额外要求】\n{custom_prompt.strip()}"

        # 调用API生成
        messages = [
            {"role": "system", "content": "你是一位专业的小说作家。你必须严格遵守字数要求，生成的章节字数必须精确控制。"},
            {"role": "user", "content": prompt}
        ]

        # 计算max_tokens - 严格控制token数量
        # token与字数的比例约为1.2-1.5:1，使用1.3作为中间值
        # 设置最大上限不超过目标字数的1.2倍，强制模型控制输出
        max_tokens_limit = int(target_words * 1.2)

        content = app_state.api_client.generate(
            messages=messages,
            max_tokens=max_tokens_limit
        )

        # 字数验证和调整
        actual_word_count = len(content)
        word_diff = actual_word_count - target_words
        diff_percent = abs(word_diff) / target_words * 100

        logger.info(f"目标字数: {target_words}, 实际字数: {actual_word_count}, 误差: {word_diff:+d} ({diff_percent:.1f}%)")

        # 如果字数偏差超过15%，尝试调整
        if diff_percent > 15:
            logger.warning(f"字数偏差过大: {diff_percent:.1f}%，尝试调整...")

            # 如果字数太多，智能截断
            if actual_word_count > max_words:
                # 尝试找到合适的截断点（句号、段落等）
                truncated = False
                for _ in range(3):  # 最多尝试3次
                    # 从后往前找合适的截断点
                    cut_pos = max_words
                    while cut_pos > min_words and cut_pos < len(content):
                        # 在当前目标位置前后50字范围内寻找句号
                        search_range = content[max(0, cut_pos-50):min(len(content), cut_pos+50)]
                        period_pos = search_range.rfind("。")
                        if period_pos != -1:
                            actual_cut = max(0, cut_pos-50) + period_pos + 1
                            content = content[:actual_cut]
                            truncated = True
                            logger.info(f"已截断内容，新字数: {len(content)}")
                            break

                        # 如果没找到句号，降低目标
                        cut_pos = int(cut_pos * 0.95)

                    if truncated:
                        break

            # 如果字数太少，记录警告但不强制调整（避免质量下降）
            elif actual_word_count < min_words:
                logger.warning(f"内容偏短，建议检查质量。目标: {target_words}, 实际: {actual_word_count}")

        # AI分析并更新连贯性系统
        validation_report = ""
        if use_coherence:
            # 分析角色
            from src.core.coherence import analyze_characters_from_chapter
            analyze_characters_from_chapter(
                content,
                chapter_num,
                app_state.character_tracker,
                app_state.api_client
            )

            # 分析剧情
            from src.core.coherence import analyze_plot_from_chapter
            analyze_plot_from_chapter(
                content,
                chapter_desc,
                chapter_num,
                app_state.plot_manager,
                app_state.api_client
            )

            # 分析世界观
            from src.core.coherence import extract_world_setting_from_chapter
            extract_world_setting_from_chapter(
                content,
                chapter_num,
                app_state.world_db,
                app_state.api_client
            )

            # 验证连贯性
            result = validate_chapter_coherence(
                content,
                chapter_num,
                chapter_desc,
                app_state.character_tracker,
                app_state.plot_manager,
                app_state.world_db,
                app_state.api_client
            )
            validation_report = f"连贯性评分: {result.score:.1f}/100\n{result.summary}"

        # 保存章节
        chapter_data = {
            "num": chapter_num,
            "title": chapter_title,
            "desc": chapter_desc,
            "content": content,
            "word_count": len(content),
            "generated_at": datetime.now().isoformat()
        }

        project["chapters"].append(chapter_data)
        project["updated_at"] = datetime.now().isoformat()

        # 保存项目文件
        project_file = app_state.project_dir / f"{project['id']}.json"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project, f, ensure_ascii=False, indent=2)

        logger.info(f"章节生成成功: 第{chapter_num}章")
        return content, f"✓ 生成成功！字数: {len(content)}", validation_report

    except Exception as e:
        logger.error(f"生成章节失败: {e}")
        return "", f"✗ 生成失败: {str(e)}", ""


# ==================== API配置UI ====================

def create_api_config_ui():
    """创建API配置UI"""
    with gr.Blocks() as api_config_tab:
        gr.Markdown("## 📡 API配置与负载均衡")
        gr.Markdown("支持配置多个API接口，自动实现负载均衡（轮询策略）")

        # 已配置提供商列表
        with gr.Accordion("📋 已配置的提供商", open=True):
            providers_list = gr.Markdown("尚未配置任何提供商")

        # 添加/编辑提供商
        gr.Markdown("---")
        gr.Markdown("### 添加或编辑提供商配置")

        # 提供商列表
        providers_info = ProviderFactory.list_providers_with_info()

        provider_names = [p["name"] for p in providers_info]
        provider_icons = [p.get("icon", "🔌") for p in providers_info]

        # 提供商选择
        with gr.Row():
            provider_dropdown = gr.Dropdown(
                choices=[f"{icon} {name}" for icon, name in zip(provider_icons, provider_names)],
                label="选择提供商",
                value=provider_icons[0] + " " + provider_names[0] if provider_names else None,
                interactive=True
            )

        # API Key输入
        with gr.Row():
            api_key_input = gr.Textbox(
                label="API Key",
                type="password",
                placeholder="输入API Key...",
                interactive=True
            )

        # 高级设置（折叠）
        with gr.Accordion("高级设置", open=False):
            with gr.Row():
                custom_url = gr.Textbox(
                    label="自定义URL（可选）",
                    placeholder="https://api.example.com/v1",
                    interactive=True
                )

            with gr.Row():
                model_input = gr.Textbox(
                    label="模型名称",
                    placeholder="使用默认模型",
                    interactive=True
                )

            with gr.Row():
                timeout_input = gr.Slider(
                    minimum=10,
                    maximum=600,
                    value=60,
                    step=10,
                    label="请求超时时间（秒）",
                    info="API请求的最长等待时间，建议60-180秒。生成可能需要较长时间，建议设置至少120秒",
                    interactive=True
                )

            with gr.Row():
                max_retries_input = gr.Slider(
                    minimum=0,
                    maximum=10,
                    value=3,
                    step=1,
                    label="最大重试次数",
                    info="API调用失败时的重试次数。0=不重试，建议2-5次。网络不稳定时增加",
                    interactive=True
                )

            gr.Markdown("**注意**：Temperature 和 Max Tokens 已移至「系统设置 > 生成参数」，请在那里配置这些参数。")

        # 操作按钮
        with gr.Row():
            test_btn = gr.Button("🔗 测试连接", variant="primary")
            save_btn = gr.Button("💾 保存配置", variant="secondary")
            delete_btn = gr.Button("🗑️ 删除当前提供商配置", variant="stop")
            clear_all_btn = gr.Button("⚠️ 清空所有配置", variant="stop")

        # 状态输出
        status_output = gr.Textbox(
            label="状态",
            interactive=False,
            lines=3
        )

        # 事件处理
        def on_provider_change(provider_display):
            """提供商切换时更新默认值"""
            # 提取提供商名称
            name = provider_display.split(" ", 1)[-1] if " " in provider_display else provider_display

            # 查找配置
            config = ProviderFactory.get_provider_by_name(name)
            if config:
                # 尝试从用户配置中读取该提供商的配置
                config_file = Path("config/user_config.json")
                timeout_val = 60  # 默认值
                max_retries_val = 3  # 默认值
                if config_file.exists():
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            user_config = json.load(f)
                            for provider in user_config.get("providers", []):
                                if provider.get("provider_id") == config.id:
                                    timeout_val = provider.get("timeout", 60)
                                    max_retries_val = provider.get("max_retries", 3)
                                    break
                    except Exception:
                        pass

                updates = {
                    custom_url: config.base_url,
                    model_input: config.default_model,
                    timeout_input: timeout_val,
                    max_retries_input: max_retries_val,
                    api_key_input: "" if config.requires_key else "不需要API Key"
                }
                return updates

        def on_test_connection(provider_display, api_key, url, model, timeout_val, max_retries_val):
            """测试连接"""
            name = provider_display.split(" ", 1)[-1] if " " in provider_display else provider_display
            config = ProviderFactory.get_provider_by_name(name)

            if not config:
                return "✗ 未找到提供商配置"

            # 使用输入的URL或默认URL
            base_url = url if url.strip() else config.base_url

            # 检查是否需要API Key
            if config.requires_key and not api_key:
                return "✗ 该提供商需要API Key"

            try:
                # 创建临时客户端测试（包含超时时间和重试次数）
                temp_client = create_api_client([{
                    "provider_id": config.id,
                    "api_key": api_key,
                    "base_url": base_url,
                    "model": model if model.strip() else config.default_model,
                    "timeout": int(timeout_val),
                    "max_retries": int(max_retries_val),
                    "enabled": True
                }])

                results = temp_client.test_connection()
                result = results.get(config.name, False)

                if result:
                    return f"✓ 连接测试成功！{config.name} 可用（超时: {timeout_val}秒，重试: {max_retries_val}次）"
                else:
                    return f"✗ 连接测试失败：{config.name}"

            except Exception as e:
                return f"✗ 连接测试失败：{str(e)}"

        def on_save_config(provider_display, api_key, url, model, timeout_val, max_retries_val):
            """保存配置"""
            name = provider_display.split(" ", 1)[-1] if " " in provider_display else provider_display
            config = ProviderFactory.get_provider_by_name(name)

            if not config:
                error_msg = "✗ 未找到提供商配置"
                return error_msg, get_providers_list()

            # 保存到配置文件
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "user_config.json"

            # 加载现有配置
            existing_config = {}
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)

            # 更新配置
            if "providers" not in existing_config:
                existing_config["providers"] = []

            provider_config = {
                "id": f"{config.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",  # 唯一ID
                "provider_id": config.id,
                "name": config.name,
                "api_key": api_key,
                "base_url": url if url.strip() else config.base_url,
                "model": model if model.strip() else config.default_model,
                "timeout": int(timeout_val),
                "max_retries": int(max_retries_val),
                "enabled": True,
                "created_at": datetime.now().isoformat()
            }

            # 查找是否已存在该提供商
            existing_config["providers"] = [
                p for p in existing_config["providers"]
                if p.get("provider_id") != config.id
            ]
            existing_config["providers"].append(provider_config)

            # 保存
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, ensure_ascii=False, indent=2)

            # 重新初始化API客户端
            try:
                app_state.init_api_client(existing_config["providers"])
                success_msg = f"✓ 配置已保存：{config.name}\n• 超时: {timeout_val}秒\n• 重试: {max_retries_val}次\n• 注意：Temperature 和 Max Tokens 请在「生成参数」中配置"
                return success_msg, get_providers_list()
            except Exception as e:
                error_msg = f"✗ 保存成功但初始化失败：{str(e)}"
                return error_msg, get_providers_list()

        def on_delete_config(provider_display):
            """删除当前提供商的配置"""
            name = provider_display.split(" ", 1)[-1] if " " in provider_display else provider_display
            config = ProviderFactory.get_provider_by_name(name)

            if not config:
                return "✗ 未找到提供商配置", get_providers_list()

            # 保存到配置文件
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "user_config.json"

            # 加载现有配置
            existing_config = {}
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                except Exception:
                    pass

            # 获取现有提供商列表
            providers = existing_config.get("providers", [])

            # 过滤掉要删除的提供商
            original_count = len(providers)
            providers = [p for p in providers if p.get("provider_id") != config.id]
            deleted_count = original_count - len(providers)

            if deleted_count == 0:
                return f"ℹ️ 该提供商没有配置可以删除", get_providers_list()

            # 保存更新后的配置
            existing_config["providers"] = providers
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, ensure_ascii=False, indent=2)

            # 重新初始化API客户端
            try:
                if providers:
                    app_state.init_api_client(providers)
                else:
                    app_state.api_client = None
                return f"✓ 已删除 {config.name} 的配置", get_providers_list()
            except Exception as e:
                return f"✗ 删除成功但重新初始化失败：{str(e)}", get_providers_list()

        def on_clear_all_configs():
            """清空所有API配置"""
            config_file = Path("config/user_config.json")

            if not config_file.exists():
                return "ℹ️ 没有配置需要清空", get_providers_list()

            try:
                # 备份原配置
                backup_file = config_file.with_suffix(".backup.json")
                import shutil
                shutil.copy2(config_file, backup_file)

                # 读取当前配置数量
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
                    count = len(existing_config.get("providers", []))

                # 清空配置
                existing_config["providers"] = []
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_config, f, ensure_ascii=False, indent=2)

                # 清空API客户端
                app_state.api_client = None

                return f"✓ 已清空所有配置（共{count}个提供商）\n💾 备份已保存到 {backup_file.name}", get_providers_list()
            except Exception as e:
                return f"✗ 清空失败：{str(e)}", get_providers_list()

        # 绑定事件
        provider_dropdown.change(
            fn=on_provider_change,
            inputs=[provider_dropdown],
            outputs={custom_url, model_input, timeout_input, max_retries_input, api_key_input}
        )

        test_btn.click(
            fn=on_test_connection,
            inputs=[provider_dropdown, api_key_input, custom_url, model_input, timeout_input, max_retries_input],
            outputs=[status_output]
        )

        save_btn.click(
            fn=on_save_config,
            inputs=[provider_dropdown, api_key_input, custom_url, model_input, timeout_input, max_retries_input],
            outputs=[status_output, providers_list]
        )

        delete_btn.click(
            fn=on_delete_config,
            inputs=[provider_dropdown],
            outputs=[status_output, providers_list]
        )

        clear_all_btn.click(
            fn=on_clear_all_configs,
            outputs=[status_output, providers_list]
        )

        # 页面加载时自动显示已保存的配置
        def on_load():
            """页面加载时显示已保存的配置"""
            return get_providers_list()

        def get_providers_list():
            """获取已配置提供商列表"""
            config_file = Path("config/user_config.json")
            if not config_file.exists():
                return "**尚未配置任何API接口**\n\n请选择提供商并配置"

            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                providers = config.get("providers", [])
                if not providers:
                    return "**配置文件为空**\n\n请添加API提供商配置"

                # 构建显示信息
                provider_list = []
                for p in providers:
                    enabled = "✅" if p.get("enabled", True) else "❌"
                    name = p.get("name", "未知")
                    timeout = p.get("timeout", 60)
                    model = p.get("model", "默认模型")
                    config_id = p.get("id", "未知")
                    created_at = p.get("created_at", "")

                    provider_list.append(f"{enabled} **{name}**")
                    provider_list.append(f"  - ID: `{config_id[-12:]}`")  # 显示ID后12位
                    provider_list.append(f"  - 模型: `{model}`")
                    provider_list.append(f"  - 超时: {timeout}秒")
                    if created_at:
                        provider_list.append(f"  - 创建时间: {created_at[:10]}")
                    provider_list.append("")

                header = f"### 📋 已配置 {len(providers)} 个API提供商\n\n"
                details = "\n".join(provider_list)

                if len(providers) > 1:
                    note = "\n---\n\n🔄 **负载均衡已启用**：多个接口将自动轮询分配请求，提高可用性和性能。\n\n💡 提示：选择上方提供商可查看或修改配置"
                else:
                    note = "\n---\n\nℹ️ **单接口模式**：配置多个接口可启用负载均衡。\n\n💡 提示：选择上方提供商可查看或修改配置"

                return header + details + note

            except Exception as e:
                return f"❌ 读取配置文件失败: {str(e)}"

        # 页面加载事件
        api_config_tab.load(
            fn=on_load,
            outputs=[providers_list]
        )

        # 刷新提供商列表按钮
        def on_refresh_list():
            return get_providers_list()

        refresh_btn = gr.Button("🔄 刷新列表", size="sm")
        refresh_btn.click(
            fn=on_refresh_list,
            outputs=[providers_list]
        )

    return api_config_tab


# ==================== 提示词编辑器UI ====================

def create_prompt_editor_ui():
    """创建提示词编辑器UI"""
    with gr.Blocks() as prompt_editor_tab:
        gr.Markdown("## 📝 提示词编辑器")

        # 模板选择
        with gr.Row():
            category_dropdown = gr.Dropdown(
                choices=["generation", "rewrite", "outline"],
                label="类别",
                value="generation",
                interactive=True
            )

            template_dropdown = gr.Dropdown(
                choices=[],
                label="模板",
                interactive=True
            )

        # 模板内容
        template_content = gr.Textbox(
            label="模板内容",
            lines=15,
            interactive=True
        )

        # 变量说明
        with gr.Accordion("可用变量", open=False):
            variables_info = gr.Markdown("""
            可用变量：
            - `{title}` - 小说标题
            - `{genre}` - 小说类型
            - `{chapter_num}` - 章节号
            - `{chapter_title}` - 章节标题
            - `{chapter_desc}` - 章节描述
            - `{context}` - 前文回顾
            - `{target_words}` - 目标字数
            """)

        # 操作按钮
        with gr.Row():
            save_template_btn = gr.Button("💾 保存模板", variant="primary")
            reset_btn = gr.Button("🔄 重置为预设", variant="secondary")
            export_btn = gr.Button("📤 导出配置", variant="secondary")
            import_btn = gr.Button("📥 导入配置", variant="secondary")

        # 状态输出
        status_output = gr.Textbox(
            label="状态",
            interactive=False
        )

        # 事件处理
        def on_category_change(category):
            """类别切换时更新模板列表"""
            if not app_state.prompt_manager:
                app_state.init_prompt_system()

            templates = app_state.prompt_manager.list_templates(category)
            template_names = []
            for cat, names in templates.items():
                template_names.extend(names)

            return gr.Dropdown(choices=template_names)

        def on_template_change(category, template_name):
            """模板切换时加载内容"""
            if not app_state.prompt_manager:
                return ""

            template = app_state.prompt_manager.get_template(category, template_name)
            return template or ""

        def on_save_template(category, template_name, content):
            """保存模板"""
            if not app_state.prompt_manager:
                app_state.init_prompt_system()

            app_state.prompt_manager.set_template(category, template_name, content)
            return f"✓ 模板已保存：{category} - {template_name}"

        def on_reset(category, template_name):
            """重置为预设"""
            if not app_state.prompt_manager:
                app_state.init_prompt_system()

            success = app_state.prompt_manager.reset_to_preset(category, template_name)
            if success:
                template = app_state.prompt_manager.get_template(category, template_name, use_preset=True)
                return template, f"✓ 已重置为预设模板：{template_name}"
            return "", f"✗ 未找到预设模板：{category} - {template_name}"

        # 绑定事件
        category_dropdown.change(
            fn=on_category_change,
            inputs=[category_dropdown],
            outputs=[template_dropdown]
        )

        template_dropdown.change(
            fn=on_template_change,
            inputs=[category_dropdown, template_dropdown],
            outputs=[template_content]
        )

        save_template_btn.click(
            fn=on_save_template,
            inputs=[category_dropdown, template_dropdown, template_content],
            outputs=[status_output]
        )

        reset_btn.click(
            fn=on_reset,
            inputs=[category_dropdown, template_dropdown],
            outputs=[template_content, status_output]
        )

    return prompt_editor_tab


# ==================== 主界面 ====================

def create_main_ui():
    """创建主界面"""
    with gr.Blocks(title="AI Novel Generator 4.5") as app:
        # 项目介绍头部
        gr.Markdown("""
        <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 20px;">
            <h1 style="color: white; margin: 0; font-size: 2.5em;">🚀 AI小说生成器 4.5</h1>
            <h3 style="color: #f0f0f0; margin: 10px 0 0 0;">智能连贯性系统 | 22+ API提供商 | 灵活提示词管理</h3>
            <p style="color: #e0e0e0; margin: 10px 0 0 0; font-size: 1.1em;">
                一款功能强大的AI辅助小说创作工具，帮助作者高效创作高质量小说
            </p>
        </div>
        """)
        
        gr.Markdown("### 智能连贯性系统 + 22+提供商支持")

        with gr.Tabs():
            # Tab 1: 小说创作
            with gr.Tab("📖 小说创作"):
                with gr.Tabs():
                    # 子标签1: 单章创作
                    with gr.Tab("📝 单章创作"):
                        gr.Markdown("### 📌 选择项目")
                        gr.Markdown("为已有项目逐个生成章节。如需创建新项目，请使用「🚀 自动生成整本小说」标签。")

                        # 项目选择区域
                        with gr.Row():
                            # 获取项目列表
                            project_choices_for_dropdown = []
                            try:
                                from project_manager import ProjectManager
                                projects_list = ProjectManager.list_projects()
                                project_choices_for_dropdown = [p["title"] for p in projects_list]
                                logger.info(f"[单章创作] 加载了 {len(project_choices_for_dropdown)} 个项目")
                            except Exception as e:
                                logger.error(f"获取项目列表失败: {e}", exc_info=True)
                                project_choices_for_dropdown = []

                            project_selector = gr.Dropdown(
                                choices=project_choices_for_dropdown,
                                value=project_choices_for_dropdown[0] if project_choices_for_dropdown else None,
                                label="选择项目",
                                info="选择要操作的项目",
                                interactive=True
                            )

                        # 项目信息显示
                        project_info_display = gr.Markdown("""
                        **提示**：请先选择一个项目，或前往「🚀 自动生成整本小说」创建新项目
                        """)

                        gr.Markdown("---")

                        # 章节生成区域
                        gr.Markdown("### ✍️ 章节生成")

                        with gr.Row():
                            generation_style = gr.Dropdown(
                                choices=["默认", "玄幻仙侠", "都市言情", "悬疑推理", "武侠", "科幻", "历史", "游戏", "其他"],
                                value="默认",
                                label="写作风格",
                                info="选择预设的写作风格模板",
                                scale=1
                            )
                            use_coherence = gr.Checkbox(
                                label="启用连贯性系统",
                                value=True,
                                scale=1
                            )

                        with gr.Row():
                            chapter_num = gr.Number(
                                label="章节号",
                                value=1,
                                minimum=1,
                                info="自动填充，也可手动修改"
                            )
                            chapter_title = gr.Textbox(
                                label="章节标题",
                                placeholder="例如：第一章 初入江湖",
                                scale=2
                            )

                        chapter_desc = gr.Textbox(
                            label="章节大纲",
                            lines=5,
                            placeholder="本章要写的主要内容、情节要点..."
                        )

                        with gr.Row():
                            target_words = gr.Number(
                                label="目标字数",
                                value=3000,
                                minimum=100,
                                maximum=50000,
                                step=100
                            )
                            custom_prompt = gr.Textbox(
                                label="自定义提示词（可选）",
                                placeholder="额外的写作要求、风格调整等...",
                                scale=2
                            )

                        generate_btn = gr.Button("🚀 生成章节", variant="primary", size="lg")

                        # 生成结果
                        gr.Markdown("---")
                        gr.Markdown("### 📄 生成结果")

                        with gr.Row():
                            generate_status = gr.Textbox(
                                label="状态",
                                interactive=False,
                                scale=1
                            )
                            word_count_display = gr.Textbox(
                                label="字数统计",
                                value="待生成",
                                interactive=False,
                                scale=1
                            )

                        chapter_output = gr.Textbox(
                            label="生成内容",
                            lines=20,
                            interactive=True
                        )
                        validation_output = gr.Textbox(
                            label="连贯性验证",
                            lines=5,
                            interactive=False
                        )

                    # 子标签2: 自动生成整本小说
                    with gr.Tab("🚀 自动生成整本小说"):
                        gr.Markdown("### 📖 一键生成完整小说")
                        gr.Markdown("填写基本信息 → 指定章节数 → 自动生成整本小说，集成缓存、上下文、连贯性系统")

                        # 初始化自动生成器（如果还没有）
                        if not app_state.auto_generator:
                            app_state.init_auto_generator()

                        if app_state.auto_generator:
                            # 获取项目列表用于加载（使用project_id作为唯一标识）
                            project_choices = {}  # {project_id: title}
                            try:
                                from project_manager import ProjectManager
                                projects = ProjectManager.list_projects()
                                # 使用project_id作为key，避免同名项目冲突
                                project_choices = {p["id"]: p["title"] for p in projects}
                                logger.info(f"加载了 {len(project_choices)} 个项目")
                            except Exception as e:
                                logger.warning(f"获取项目列表失败: {e}")

                            auto_tab = create_auto_generation_ui(app_state, app_state.auto_generator, project_choices)
                        else:
                            gr.Markdown("❌ 自动生成器未初始化，请先配置API")

            # Tab 2: 小说重写
            with gr.Tab("📝 小说重写"):
                rewrite_tab = create_rewrite_ui(app_state)

            # Tab 3: 小说润色
            with gr.Tab("✨ 小说润色"):
                polish_tab = create_polish_ui(app_state)

            # Tab 4: 连贯性分析
            with gr.Tab("🔍 连贯性分析"):
                coherence_viz = CoherenceVizUI(app_state)
                coherence_tab = coherence_viz.create_ui()

            # Tab 5: 提示词编辑器
            with gr.Tab("📝 提示词编辑器"):
                prompt_editor_tab = create_prompt_editor_ui()

            # Tab 6: 项目管理
            with gr.Tab("📁 项目管理"):
                gr.Markdown("### 我的项目")
                gr.Markdown("💡 提示：要在单章创作中使用项目，请直接在「📝 单章创作」标签页选择项目")

                projects_table = gr.Dataframe(
                    headers=["ID", "标题", "类型", "创建时间", "章节数"],
                    interactive=False
                )
                with gr.Row():
                    refresh_btn = gr.Button("🔄 刷新列表")
                    delete_btn = gr.Button("🗑️ 删除项目", variant="stop")
                    delete_all_btn = gr.Button("🗑️ 一键删除所有项目", variant="stop")
                project_status = gr.Textbox(label="状态", interactive=False)

                gr.Markdown("---")

                # 导出功能（更显眼）
                gr.Markdown("### 📤 导出整本小说")
                gr.Markdown("**请先选择要导出的项目，然后选择导出格式，最后点击导出按钮**")

                # 获取项目列表用于导出选择框
                export_project_choices = []
                try:
                    from project_manager import ProjectManager
                    projects_list_for_export = ProjectManager.list_projects()
                    export_project_choices = [p["title"] for p in projects_list_for_export]
                except Exception as e:
                    logger.warning(f"获取导出项目列表失败: {e}")

                # 第一步：选择要导出的项目
                gr.Markdown("#### 第一步：选择要导出的项目")
                project_export_selector = gr.Dropdown(
                    choices=export_project_choices,
                    label="📁 选择要导出的项目",
                    info="请从下拉框中选择要导出的项目（点击刷新列表后可用）",
                    interactive=True,
                    scale=1
                )

                # 第二步：选择导出格式和导出按钮
                gr.Markdown("#### 第二步：选择导出格式并导出")
                with gr.Row():
                    project_export_format = gr.Radio(
                        choices=["Word (.docx)", "文本 (.txt)", "Markdown (.md)", "HTML (.html)"],
                        value="文本 (.txt)",
                        label="📄 导出格式",
                        interactive=True,
                        scale=1
                    )
                    export_project_btn = gr.Button("📦 导出整本小说", variant="primary", scale=1, size="lg")

                # 导出结果显示区域
                export_download = gr.File(label="💾 下载文件", interactive=False)
                export_info = gr.Markdown("**✨ 使用说明**: 1️⃣ 点击「刷新列表」→ 2️⃣ 在上方下拉框选择项目 → 3️⃣ 选择导出格式 → 4️⃣ 点击「导出整本小说」")

        # 事件绑定
        # 项目选择变化时显示项目信息并更新章节号
        def on_project_select(project_title):
            """项目选择变化时更新显示"""
            if not project_title or not project_title.strip():
                return "请选择一个项目", 1

            try:
                from project_manager import ProjectManager
                project = ProjectManager.get_project_by_title(project_title)
                if not project:
                    return "❌ 项目加载失败", 1

                # 加载项目到app_state
                project_id = project.get("id")
                if project_id:
                    load_project(project_id)

                chapters = project.get("chapters", [])
                total_chapters = project.get("total_chapters", len(chapters))
                completed_count = sum(1 for ch in chapters if ch.get("content", "").strip())

                # 下一章编号
                next_chapter = completed_count + 1

                # 项目信息
                info = f"""
### 📖 {project.get('title', '')}

**类型**: {project.get('genre', '')}
**总章节数**: {total_chapters} 章
**已完成**: {completed_count} 章
**待生成**: {total_chapters - completed_count} 章
**创建时间**: {project.get('created_at', '')[:10]}

---

💡 **建议**：
- 下一章建议编号：第{next_chapter}章
- 当前连贯性系统状态：{'✅ 已启用' if app_state.character_tracker else '❌ 未初始化'}
"""

                return info, next_chapter

            except Exception as e:
                logger.error(f"加载项目信息失败: {e}")
                return f"❌ 加载失败: {str(e)}", 1

        project_selector.change(
            fn=on_project_select,
            inputs=[project_selector],
            outputs=[project_info_display, chapter_num]
        )

        generate_btn.click(
            fn=generate_chapter,
            inputs=[
                chapter_num,
                chapter_title,
                chapter_desc,
                target_words,
                use_coherence,
                generation_style,
                custom_prompt
            ],
            outputs=[
                chapter_output,
                generate_status,
                validation_output
            ]
        ).then(
            # 生成完成后更新字数统计
            fn=lambda content, status: f"{len(content)} 字" if content and "✓" in status else "生成失败",
            inputs=[chapter_output, generate_status],
            outputs=[word_count_display]
        )

        # 刷新项目列表和导出选择器
        def on_refresh_all():
            """刷新项目列表和导出选择器"""
            table = list_projects()
            titles = list_project_titles()
            return table, gr.update(choices=titles, value=None)

        # 删除项目事件（改为使用下拉框）
        def on_delete_project(selected_project_title):
            """删除选中的项目"""
            if not selected_project_title or not selected_project_title.strip():
                return "❌ 请先选择要删除的项目（从下拉框选择）", gr.update(), gr.update()

            try:
                from project_manager import ProjectManager
                project = ProjectManager.get_project_by_title(selected_project_title)
                if not project:
                    return "❌ 未找到选中的项目", gr.update(), gr.update()

                project_id = project.get("id")
                if not project_id:
                    return "❌ 项目ID为空", gr.update(), gr.update()

                success, msg = delete_project(project_id)
                if success:
                    # 刷新列表和下拉框
                    new_table = list_projects()
                    new_titles = list_project_titles()
                    return f"✓ {msg}", gr.update(value=new_table), gr.update(choices=new_titles, value=None)
                else:
                    return f"✗ {msg}", gr.update(), gr.update()

            except Exception as e:
                logger.error(f"删除项目失败: {e}")
                return f"❌ 删除失败: {str(e)}", gr.update(), gr.update()

        # 导出项目事件
        def on_export_project_click(selected_project_title, format_type):
            """导出选中的项目"""
            if not selected_project_title or not selected_project_title.strip():
                return "❌ 请先在下拉框选择要导出的项目", None

            logger.info(f"[项目管理] 准备导出项目: {selected_project_title}, 格式: {format_type}")

            try:
                from project_manager import ProjectManager
                project = ProjectManager.get_project_by_title(selected_project_title)
                if not project:
                    return "❌ 未找到选中的项目", None

                project_id = project.get("id")
                if not project_id:
                    return "❌ 项目ID为空", None

                # 映射格式名称
                format_map = {
                    "Word (.docx)": "docx",
                    "文本 (.txt)": "txt",
                    "Markdown (.md)": "md",
                    "HTML (.html)": "html"
                }

                export_format = format_map.get(format_type, "docx")
                filepath, msg = export_project(project_id, export_format)

                if filepath:
                    logger.info(f"[项目管理] 导出成功: {filepath}")
                    return f"✓ {msg}", filepath
                else:
                    logger.error(f"[项目管理] 导出失败: {msg}")
                    return f"✗ {msg}", None

            except Exception as e:
                logger.error(f"[项目管理] 导出项目异常: {e}", exc_info=True)
                return f"❌ 导出失败: {str(e)}", None

        refresh_btn.click(
            fn=on_refresh_all,
            outputs=[projects_table, project_export_selector]
        )

        delete_btn.click(
            fn=on_delete_project,
            inputs=[project_export_selector],
            outputs=[project_status, projects_table, project_export_selector]
        )

        # 删除所有项目事件
        def on_delete_all_projects():
            """删除所有项目"""
            try:
                from project_manager import ProjectManager
                projects = ProjectManager.list_projects()

                if not projects:
                    return "❌ 没有项目可删除", gr.update(), gr.update()

                count = len(projects)
                deleted = 0
                failed = []

                for project in projects:
                    project_id = project.get("id")
                    if project_id:
                        try:
                            project_file = Path("projects") / f"{project_id}.json"
                            if project_file.exists():
                                project_file.unlink()
                                deleted += 1
                            else:
                                # 尝试旧格式
                                project_dir = Path("projects") / project_id
                                if project_dir.exists():
                                    import shutil
                                    shutil.rmtree(project_dir)
                                    deleted += 1
                        except Exception as e:
                            failed.append(f"{project.get('title', project_id)}: {str(e)}")

                # 刷新列表和导出选择器
                new_table = list_projects()
                new_titles = list_project_titles()

                msg = f"✓ 已删除 {deleted}/{count} 个项目"
                if failed:
                    msg += f"\n失败的: {', '.join(failed[:3])}"
                    if len(failed) > 3:
                        msg += f" 等{len(failed)}个"

                logger.info(f"[项目管理] {msg}")
                return msg, new_table, gr.update(choices=new_titles, value=None)

            except Exception as e:
                logger.error(f"[项目管理] 删除所有项目失败: {e}", exc_info=True)
                return f"❌ 删除失败: {str(e)}", gr.update(), gr.update()

        delete_all_btn.click(
            fn=on_delete_all_projects,
            outputs=[project_status, projects_table, project_export_selector]
        )

        export_project_btn.click(
            fn=on_export_project_click,
            inputs=[project_export_selector, project_export_format],
            outputs=[project_status, export_download]
        )

        # Tab 10: 系统设置
        with gr.Tab("⚙️ 系统设置"):
            gr.Markdown("### 🔧 全局配置")

            with gr.Tabs():
                # 子标签1: API配置
                with gr.Tab("🌐 接口管理"):
                    api_config_tab = create_api_config_ui()

                # 子标签2: 生成参数
                with gr.Tab("📝 生成参数"):
                    params_config_tab = create_params_config_ui(app_state)

                # 子标签3: 缓存管理
                with gr.Tab("💾 缓存管理"):
                    cache_tab = create_cache_manager_ui(app_state)

        # 底部版权信息
        gr.Markdown("""
        <div style="text-align: center; padding: 15px; margin-top: 30px; border-top: 1px solid #e0e0e0; color: #666;">
            <p style="margin: 5px 0;">AI小说生成器 v4.5.0</p>
            <p style="margin: 5px 0; font-size: 0.9em;">版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)</p>
            <p style="margin: 5px 0; font-size: 0.8em; color: #999;">Made with ❤️ by 幻城科技</p>
        </div>
        """)

        # 添加导出UI组件到项目管理标签
        # 这个需要在Tab定义中添加，但由于我们已经定义了，需要重新定位

    return app


# ==================== 启动应用 ====================

def main():
    """启动应用"""
    # 迁移配置文件：删除旧的outline_max_tokens字段
    config_file = Path("config/user_config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 检查并迁移旧的outline_max_tokens配置
            migrated = False
            for provider in config.get("providers", []):
                if "outline_max_tokens" in provider:
                    # 如果max_tokens较小，使用outline_max_tokens的值
                    if provider.get("max_tokens", 4000) < provider.get("outline_max_tokens", 8000):
                        provider["max_tokens"] = provider["outline_max_tokens"]
                    # 删除outline_max_tokens字段
                    del provider["outline_max_tokens"]
                    migrated = True
                    logger.info(f"迁移配置：删除outline_max_tokens字段，使用统一的max_tokens={provider['max_tokens']}")

            if migrated:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                logger.info("配置文件已更新")
        except Exception as e:
            logger.warning(f"迁移配置文件失败: {e}")

    # 初始化提示词系统
    app_state.init_prompt_system()

    # 自动加载API配置
    if not app_state.load_api_config():
        logger.info("未找到API配置，请在「系统设置 > 接口管理」中配置")

    # 创建UI
    app = create_main_ui()

    # 启动
    logger.info(f"启动Web服务器: {WEB_HOST}:{WEB_PORT}")
    app.launch(
        server_name=WEB_HOST,
        server_port=WEB_PORT,
        share=WEB_SHARE,
        show_error=True,
        show_api=False,  # 禁用API文档以避免gradio_client的bool类型错误
	inbrowser=True
    )


if __name__ == "__main__":
    main()
