"""
章节生成提示词
多场景设计（对话/动作/心理/环境）

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json


# 通用默认系统提示词（零AI痕迹版）
DEFAULT_SYSTEM_PROMPT = """你是一位经验丰富的中文长篇小说职业作家，擅长用细腻的笔触和扎实的叙事功力创作引人入胜的故事。

【绝对禁止】
- 绝不使用：突然、竟然、霎时间、不由得、禁不住、心中涌起、却然、陡然
- 绝不使用：在...的时候、随着...的发展、在...的背景下
- 绝不使用：括号注释人物（如：他（李明））
- 绝不使用：空洞形容词（美丽的、壮观的、惊人的）
- 绝不使用：不禁...了起来、一股...涌上心头、眼中闪过一丝...
- 绝不使用：嘴角微微上扬、轻轻地点了点头、深深地吸了一口气
- 绝不使用：仿佛...一般、宛如...似的、犹如...一样
- 绝不使用：不由自主地、情不自禁地、下意识地
- 绝不使用：浑身一震、瞳孔骤缩、倒吸一口凉气
- 绝不使用：此刻、这一刻、这一瞬间、刹那间
- 绝不使用：缓缓开口、沉声说道、语气坚定地说
- 绝不使用：与此同时、然而、只见、赫然、顿时
- 绝不在结尾总结人生感悟

【高级写作技法】
1. 展示而非告知：不要说"他很伤心"，而是描写"他手指微微颤抖，咖啡杯里的涟漪映着窗外的灰天"
2. 用动作代替形容：不要说"美丽的花园"，而是写"月季爬满石墙，蜜蜂在花瓣间穿梭"
3. 对话推动情节：每段对话至少包含一个信息增量或情感转折
4. 感官交错：视觉、听觉、触觉、嗅觉交替使用，营造沉浸感
5. 节奏变化：紧张段落用短句，舒缓段落用长句，避免句式单调
6. 信息差管理：读者知道但角色不知道，或角色知道但读者不知道——制造悬念
"""

# 保留旧常量名作为别名，兼容已有引用
OPTIMIZED_NO_AI_TASTE_SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT

# 题材到风格配置文件的映射
_GENRE_STYLE_MAP = {
    "玄幻": "xuanhuan", "仙侠": "xuanhuan",
    "都市": "dushi_romance", "言情": "dushi_romance",
    "悬疑": "xuanyi", "推理": "xuanyi",
    "历史": "lishi", "穿越": "lishi",
    "科幻": "kehuan",
    "武侠": "wuxia",
    "现实": "xianshi",
    "轻小说": "qingxiaoshuo",
}

# 扩展的禁止AI套话列表（50+个表达）
EXTENDED_FORBIDDEN_AI_PHRASES = """
【绝对禁止使用的AI套话】
突然、竟然、霎时间、不由得、禁不住、心中涌起、却然、陡然、
在...的时候、随着...的发展、在...的背景下、
不禁...了起来、一股...涌上心头、眼中闪过一丝...、
嘴角微微上扬、轻轻地点了点头、深深地吸了一口气、
心中暗想、暗自下定决心、感受到了前所未有的...、
仿佛...一般、宛如...似的、犹如...一样、
不由自主地、情不自禁地、下意识地、
一种...的感觉、说不出的...、难以言喻的...、
浑身一震、瞳孔骤缩、倒吸一口凉气、
气氛突然变得...、空气中弥漫着...、
此刻、这一刻、这一瞬间、刹那间、
缓缓开口、沉声说道、语气坚定地说、
目光如炬、眼中带着...的神色、
迈着坚定的步伐、头也不回地、义无反顾地、
与此同时、然而、只见、赫然、顿时
"""

# 高级写作技法
ADVANCED_WRITING_TECHNIQUES = """
【高级写作技法】
1. 展示而非告知：不要说"他很伤心"，而是描写"他手指微微颤抖，咖啡杯里的涟漪映着窗外的灰天"
2. 用动作代替形容：不要说"美丽的花园"，而是写"月季爬满石墙，蜜蜂在花瓣间穿梭"
3. 对话推动情节：每段对话至少包含一个信息增量或情感转折
4. 感官交错：视觉、听觉、触觉、嗅觉交替使用，营造沉浸感
5. 节奏变化：紧张段落用短句，舒缓段落用长句，避免句式单调
6. 信息差管理：读者知道但角色不知道，或角色知道但读者不知道——制造悬念
"""


def _load_style_config(genre: str) -> Optional[Dict]:
    """加载风格配置文件

    Args:
        genre: 小说题材类型（中文），如"玄幻""武侠"等

    Returns:
        风格配置字典，无匹配时返回None
    """
    style_id = _GENRE_STYLE_MAP.get(genre)
    if not style_id:
        return None
    style_path = Path("config/style_prompts") / f"{style_id}.json"
    if not style_path.exists():
        return None
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_system_prompt_for_genre(genre: str) -> str:
    """根据类型获取系统提示词

    优先从风格配置文件读取system_prompt，无匹配时回退到DEFAULT_SYSTEM_PROMPT。

    Args:
        genre: 小说题材类型（中文），如"玄幻""武侠"等

    Returns:
        系统提示词字符串
    """
    style_config = _load_style_config(genre)
    if style_config and style_config.get("system_prompt"):
        return style_config["system_prompt"]
    return DEFAULT_SYSTEM_PROMPT


def _get_style_rules_snippet(genre: str) -> str:
    """获取风格特定的写作规则片段，用于嵌入提示词中"""
    style_config = _load_style_config(genre)
    if not style_config:
        return ""
    rules = style_config.get("writing_rules", [])
    if not rules:
        return ""
    rules_text = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(rules))
    return f"\n【风格写作规则】\n{rules_text}\n"


def generate_first_chapter_prompt(params: Dict[str, Any]) -> str:
    """
    生成第一章提示词

    Args:
        params: 包含以下键的字典
            - chapter_number: 章节号
            - chapter_title: 章节标题
            - chapter_role: 章节定位
            - chapter_purpose: 核心作用
            - suspense_level: 悬念密度
            - foreshadowing: 伏笔操作
            - plot_twist_level: 认知颠覆
            - chapter_summary: 本章简述
            - characters_involved: 核心人物（可选）
            - key_items: 关键道具（可选）
            - scene_location: 空间坐标（可选）
            - time_constraint: 时间压力（可选）
            - novel_setting: 小说设定
            - word_number: 字数要求
            - user_guidance: 用户指导（可选）
            - genre: 小说类型（可选，用于风格适配）

    Returns:
        完整的提示词字符串
    """
    chapter_number = params.get('chapter_number', 1)
    chapter_title = params.get('chapter_title', '')
    chapter_role = params.get('chapter_role', '')
    chapter_purpose = params.get('chapter_purpose', '')
    suspense_level = params.get('suspense_level', '中等')
    foreshadowing = params.get('foreshadowing', '')
    plot_twist_level = params.get('plot_twist_level', '')
    chapter_summary = params.get('chapter_summary', '')
    characters_involved = params.get('characters_involved', '(未指定)')
    key_items = params.get('key_items', '(未指定)')
    scene_location = params.get('scene_location', '(未指定)')
    time_constraint = params.get('time_constraint', '(未指定)')
    novel_setting = params.get('novel_setting', '')
    word_number = params.get('word_number', 3000)
    user_guidance = params.get('user_guidance', '')
    genre = params.get('genre', '')

    # 获取风格特定的写作规则
    style_rules = _get_style_rules_snippet(genre)

    user_guidance_block = ""
    if user_guidance:
        user_guidance_block = f"\n用户额外指导：\n{user_guidance}\n"

    prompt = f"""即将创作：第 {chapter_number} 章《{chapter_title}》

【章节信息】
本章定位：{chapter_role}
核心作用：{chapter_purpose}
悬念密度：{suspense_level}
伏笔操作：{foreshadowing}
认知颠覆：{plot_twist_level}
本章简述：{chapter_summary}

【可用元素】
- 核心人物：{characters_involved}
- 关键道具：{key_items}
- 空间坐标：{scene_location}
- 时间压力：{time_constraint}

【参考文档】
小说设定：
{novel_setting}

【创作要求】
完成第 {chapter_number} 章的正文，字数要求约{word_number}字
{style_rules}
根据小说类型设计2个或以上的场景：

1. 对话场景：
   - 体现人物性格和关系
   - 推动剧情或情感发展
   - 对话要简短有力，像真人说话
   - 避免长篇大论的独白

2. 动作/互动场景：
   - 环境交互细节（感官描写）
   - 节奏控制（根据情节需要调整）
   - 通过行动展现人物特质
   - 描写要具体，用细节代替空洞形容词

3. 心理/情感场景：
   - 人物内心活动描写
   - 情感变化的细腻刻画
   - 符合小说类型的情感基调
   - 不要用"心中涌起""不由得"等AI化表达

4. 环境场景：
   - 场景氛围营造
   - 环境与人物心情的呼应
   - 符合小说类型的整体风格
   - 环境描写要有画面感

【写作示例】
❌ 不要："突然，他感受到了前所未有的恐惧"
✅ 正确："他的手不受控制地抖了一下，杯子里的水洒出来几滴。"

❌ 不要："他不由得想起了过去的种种"
✅ 正确："往事如烟，却呛得人咳出泪来。"

❌ 不要："在那个风雪交加的夜晚，空气中弥漫着紧张的气氛"
✅ 正确："风雪夜。门被撞开了三次。"

{EXTENDED_FORBIDDEN_AI_PHRASES}

{ADVANCED_WRITING_TECHNIQUES}
{user_guidance_block}
【格式要求】
- 仅返回章节正文文本
- 不使用分章节小标题
- 不要使用markdown格式
- 直接开始正文

请开始创作："""

    return prompt


def generate_next_chapter_prompt(params: Dict[str, Any]) -> str:
    """
    生成后续章节提示词

    Args:
        params: 包含以下键的字典
            - chapter_number: 章节号
            - chapter_title: 章节标题
            - chapter_role: 章节定位
            - chapter_purpose: 核心作用
            - suspense_level: 悬念密度
            - foreshadowing: 伏笔设计
            - plot_twist_level: 转折程度
            - chapter_summary: 章节简述
            - word_number: 字数要求
            - characters_involved: 核心人物（可选）
            - key_items: 关键道具（可选）
            - scene_location: 场景地点（可选）
            - time_constraint: 时间压力（可选）
            - global_summary: 前文摘要
            - previous_chapter_excerpt: 前章结尾段
            - character_state: 角色状态
            - short_summary: 当前章节摘要（可选）
            - next_chapter_number: 下一章节号
            - next_chapter_title: 下一章标题
            - next_chapter_role: 下一章定位
            - next_chapter_purpose: 下一章核心作用
            - next_suspense_level: 下一章悬念密度
            - next_foreshadowing: 下一章伏笔设计
            - next_plot_twist_level: 下一章转折程度
            - next_chapter_summary: 下一章简述
            - user_guidance: 用户指导（可选）
            - genre: 小说类型（可选，用于风格适配）

    Returns:
        完整的提示词字符串
    """
    chapter_number = params.get('chapter_number', 2)
    chapter_title = params.get('chapter_title', '')
    chapter_role = params.get('chapter_role', '')
    chapter_purpose = params.get('chapter_purpose', '')
    suspense_level = params.get('suspense_level', '中等')
    foreshadowing = params.get('foreshadowing', '')
    plot_twist_level = params.get('plot_twist_level', '')
    chapter_summary = params.get('chapter_summary', '')
    word_number = params.get('word_number', 3000)
    characters_involved = params.get('characters_involved', '(未指定)')
    key_items = params.get('key_items', '(未指定)')
    scene_location = params.get('scene_location', '(未指定)')
    time_constraint = params.get('time_constraint', '(未指定)')
    global_summary = params.get('global_summary', '')
    previous_chapter_excerpt = params.get('previous_chapter_excerpt', '')
    character_state = params.get('character_state', '')
    short_summary = params.get('short_summary', '(无)')
    next_chapter_number = params.get('next_chapter_number', chapter_number + 1)
    next_chapter_title = params.get('next_chapter_title', '')
    next_chapter_role = params.get('next_chapter_role', '')
    next_chapter_purpose = params.get('next_chapter_purpose', '')
    next_suspense_level = params.get('next_suspense_level', '中等')
    next_foreshadowing = params.get('next_foreshadowing', '')
    next_plot_twist_level = params.get('next_plot_twist_level', '')
    next_chapter_summary = params.get('next_chapter_summary', '')
    user_guidance = params.get('user_guidance', '')
    genre = params.get('genre', '')

    # 获取风格特定的写作规则
    style_rules = _get_style_rules_snippet(genre)

    prompt = f"""【参考文档】
└── 前文摘要：
    {global_summary}

└── 前章结尾段：
    {previous_chapter_excerpt}

└── 角色状态：
    {character_state}

└── 用户指导：
    {user_guidance if user_guidance else '(无)'}

└── 当前章节摘要：
    {short_summary}

【当前章节信息】
第{chapter_number}章《{chapter_title}》：
├── 章节定位：{chapter_role}
├── 核心作用：{chapter_purpose}
├── 悬念密度：{suspense_level}
├── 伏笔设计：{foreshadowing}
├── 转折程度：{plot_twist_level}
├── 章节简述：{chapter_summary}
├── 字数要求：约{word_number}字
├── 核心人物：{characters_involved}
├── 关键道具：{key_items}
├── 场景地点：{scene_location}
└── 时间压力：{time_constraint}

【下一章节目录】
第{next_chapter_number}章《{next_chapter_title}》：
├── 章节定位：{next_chapter_role}
├── 核心作用：{next_chapter_purpose}
├── 悬念密度：{next_suspense_level}
├── 伏笔设计：{next_foreshadowing}
├── 转折程度：{next_plot_twist_level}
└── 章节简述：{next_chapter_summary}

【创作要求】
依据前面所有设定，开始完成第 {chapter_number} 章的正文，字数要求约{word_number}字

内容生成严格遵循：
- 用户指导
- 当前章节摘要
- 当前章节信息
- 确保与前文摘要、前章结尾段衔接流畅
- 与下一章目录保证上下文完整性
- 无逻辑漏洞

根据小说类型设计2个或以上的场景（同第一章）
{style_rules}
{EXTENDED_FORBIDDEN_AI_PHRASES}

{ADVANCED_WRITING_TECHNIQUES}

【格式要求】
- 仅返回章节正文文本
- 不使用分章节小标题
- 不要使用markdown格式
- 直接开始正文
- 对话要口语化，别让人物说话像念书

请开始创作："""

    return prompt


def generate_enrich_chapter_prompt(params: Dict[str, Any]) -> str:
    """
    生成章节扩写提示词

    Args:
        params: 包含以下键的字典
            - chapter_text: 原章节内容
            - word_number: 目标字数
            - genre: 小说类型（可选，用于风格适配）

    Returns:
        完整的提示词字符串
    """
    chapter_text = params.get('chapter_text', '')
    word_number = params.get('word_number', 3000)
    genre = params.get('genre', '')

    # 获取风格特定的写作规则
    style_rules = _get_style_rules_snippet(genre)

    prompt = f"""以下章节文本较短，请在保持剧情连贯的前提下进行扩写，使其更充实，接近 {word_number} 字左右。

【原文】
{chapter_text}

【扩写要求】
- 保持剧情连贯性
- 增加环境描写和心理描写
- 丰富对话和场景细节
- 扩展动作描写，增加画面感
- 深化人物内心活动
- 不要改变原有情节走向
- 遵循写作禁忌（不使用AI化表达）
{style_rules}
{EXTENDED_FORBIDDEN_AI_PHRASES}

{ADVANCED_WRITING_TECHNIQUES}

仅给出最终文本，不要解释任何内容。"""

    return prompt


# 便捷函数
def create_first_chapter_prompt(
    chapter_number: int,
    chapter_title: str,
    chapter_role: str,
    chapter_purpose: str,
    suspense_level: str,
    foreshadowing: str,
    plot_twist_level: str,
    chapter_summary: str,
    novel_setting: str,
    word_number: int = 3000,
    characters_involved: str = '',
    key_items: str = '',
    scene_location: str = '',
    time_constraint: str = '',
    user_guidance: str = '',
    genre: str = ''
) -> str:
    """创建第一章提示词的便捷函数"""
    return generate_first_chapter_prompt({
        'chapter_number': chapter_number,
        'chapter_title': chapter_title,
        'chapter_role': chapter_role,
        'chapter_purpose': chapter_purpose,
        'suspense_level': suspense_level,
        'foreshadowing': foreshadowing,
        'plot_twist_level': plot_twist_level,
        'chapter_summary': chapter_summary,
        'novel_setting': novel_setting,
        'word_number': word_number,
        'characters_involved': characters_involved,
        'key_items': key_items,
        'scene_location': scene_location,
        'time_constraint': time_constraint,
        'user_guidance': user_guidance,
        'genre': genre
    })


def create_next_chapter_prompt(
    chapter_number: int,
    chapter_title: str,
    chapter_role: str,
    chapter_purpose: str,
    suspense_level: str,
    foreshadowing: str,
    plot_twist_level: str,
    chapter_summary: str,
    word_number: int,
    global_summary: str,
    previous_chapter_excerpt: str,
    character_state: str,
    next_chapter_number: int,
    next_chapter_title: str,
    next_chapter_role: str,
    next_chapter_purpose: str,
    next_suspense_level: str,
    next_foreshadowing: str,
    next_plot_twist_level: str,
    next_chapter_summary: str,
    characters_involved: str = '',
    key_items: str = '',
    scene_location: str = '',
    time_constraint: str = '',
    short_summary: str = '',
    user_guidance: str = '',
    genre: str = ''
) -> str:
    """创建下一章提示词的便捷函数"""
    return generate_next_chapter_prompt({
        'chapter_number': chapter_number,
        'chapter_title': chapter_title,
        'chapter_role': chapter_role,
        'chapter_purpose': chapter_purpose,
        'suspense_level': suspense_level,
        'foreshadowing': foreshadowing,
        'plot_twist_level': plot_twist_level,
        'chapter_summary': chapter_summary,
        'word_number': word_number,
        'characters_involved': characters_involved,
        'key_items': key_items,
        'scene_location': scene_location,
        'time_constraint': time_constraint,
        'global_summary': global_summary,
        'previous_chapter_excerpt': previous_chapter_excerpt,
        'character_state': character_state,
        'short_summary': short_summary,
        'next_chapter_number': next_chapter_number,
        'next_chapter_title': next_chapter_title,
        'next_chapter_role': next_chapter_role,
        'next_chapter_purpose': next_chapter_purpose,
        'next_suspense_level': next_suspense_level,
        'next_foreshadowing': next_foreshadowing,
        'next_plot_twist_level': next_plot_twist_level,
        'next_chapter_summary': next_chapter_summary,
        'user_guidance': user_guidance,
        'genre': genre
    })


def create_enrich_chapter_prompt(
    chapter_text: str,
    word_number: int,
    genre: str = ''
) -> str:
    """创建章节扩写提示词的便捷函数"""
    return generate_enrich_chapter_prompt({
        'chapter_text': chapter_text,
        'word_number': word_number,
        'genre': genre
    })
