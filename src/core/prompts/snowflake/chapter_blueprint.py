"""
章节蓝图提示词
节奏曲线设计（悬念密度、伏笔操作、情节张力）

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from typing import Dict, Any


def generate_chapter_blueprint_prompt(params: Dict[str, Any]) -> str:
    """
    生成章节蓝图提示词（一次性生成）

    Args:
        params: 包含以下键的字典
            - novel_architecture: 小说架构文本
            - number_of_chapters: 章节数
            - user_guidance: 用户指导（可选）

    Returns:
        完整的提示词字符串
    """
    novel_architecture = params.get('novel_architecture', '')
    number_of_chapters = params.get('number_of_chapters', 50)
    user_guidance = params.get('user_guidance', '')

    prompt = f"""基于以下元素：
- 内容指导：{user_guidance if user_guidance else '无'}
- 小说架构：
{novel_architecture}

设计{number_of_chapters}章的节奏分布（根据小说类型调整风格）：

【1. 章节集群划分】
- 每3-5章构成一个情节单元，包含完整的小高潮
- 单元之间合理安排情感节奏（张弛有度）
- 关键转折章需预留铺垫

【2. 每章需明确】
- 章节定位（角色/事件/主题等）
- 核心作用（推进/转折/发展/升温/...）
- 情感基调（符合小说类型的情感色彩）
- 伏笔操作（埋设/强化/回收）
- 情节张力（★☆☆☆☆ 到 ★★★★★）

【输出格式示例】
```
第n章 - [标题]
本章定位：[角色/事件/主题/...]
核心作用：[推进/转折/发展/升温/...]
情感强度：[平缓/渐进/高潮/...]
伏笔操作：埋设(A线索)→强化(B关系)...
情节张力：★☆☆☆☆
本章简述：[一句话概括]
```

要求：
- 使用精炼语言描述，每章字数控制在100字以内
- 合理安排节奏，确保整体情感曲线的连贯性
- 在生成{number_of_chapters}章前不要出现结局章节
- **情节设计需符合小说类型的风格和情感基调**
- 节奏要有起伏，不要平淡
- 伏笔要自然埋设

{f'''
用户额外指导：
{user_guidance}
''' if user_guidance else ''}

仅给出最终文本，不要解释任何内容。"""

    return prompt


def generate_chunked_chapter_blueprint_prompt(params: Dict[str, Any]) -> str:
    """
    生成分块章节蓝图提示词

    Args:
        params: 包含以下键的字典
            - novel_architecture: 小说架构文本
            - chapter_list: 已有章节列表
            - number_of_chapters: 总章节数
            - start_chapter: 开始章节号
            - end_chapter: 结束章节号
            - user_guidance: 用户指导（可选）

    Returns:
        完整的提示词字符串
    """
    novel_architecture = params.get('novel_architecture', '')
    chapter_list = params.get('chapter_list', '')
    number_of_chapters = params.get('number_of_chapters', 50)
    start_chapter = params.get('start_chapter', 1)
    end_chapter = params.get('end_chapter', 10)
    user_guidance = params.get('user_guidance', '')

    prompt = f"""基于以下元素：
- 内容指导：{user_guidance if user_guidance else '无'}
- 小说架构：
{novel_architecture}

需要生成总共{number_of_chapters}章的节奏分布

当前已有章节目录（若为空则说明是初始生成）：
{chapter_list if chapter_list else '(无)'}

现在请设计第{start_chapter}章到第{end_chapter}章的节奏分布：

【1. 章节集群划分】
- 每3-5章构成一个情节单元，包含完整的小高潮
- 单元之间合理安排情感节奏（张弛有度）
- 关键转折章需预留铺垫

【2. 每章需明确】
- 章节定位（角色/事件/主题等）
- 核心作用（推进/转折/发展/升温/...）
- 情感基调（符合小说类型的情感色彩）
- 伏笔操作（埋设/强化/回收）
- 情节张力（★☆☆☆☆ 到 ★★★★★）

【输出格式示例】
```
第n章 - [标题]
本章定位：[角色/事件/主题/...]
核心作用：[推进/转折/发展/升温/...]
情感强度：[平缓/渐进/高潮/...]
伏笔操作：埋设(A线索)→强化(B关系)...
情节张力：★☆☆☆☆
本章简述：[一句话概括]
```

要求：
- 使用精炼语言描述，每章字数控制在100字以内
- 合理安排节奏，确保整体情感曲线的连贯性
- 在生成{number_of_chapters}章前不要出现结局章节
- **情节设计需符合小说类型的风格和情感基调**
- 与已有章节保持连贯性

{f'''
用户额外指导：
{user_guidance}
''' if user_guidance else ''}

仅给出最终文本，不要解释任何内容。"""

    return prompt


# 便捷函数
def create_chapter_blueprint_prompt(
    novel_architecture: str,
    number_of_chapters: int,
    user_guidance: str = ''
) -> str:
    """创建章节蓝图提示词的便捷函数"""
    return generate_chapter_blueprint_prompt({
        'novel_architecture': novel_architecture,
        'number_of_chapters': number_of_chapters,
        'user_guidance': user_guidance
    })


def create_chunked_chapter_blueprint_prompt(
    novel_architecture: str,
    chapter_list: str,
    number_of_chapters: int,
    start_chapter: int,
    end_chapter: int,
    user_guidance: str = ''
) -> str:
    """创建分块章节蓝图提示词的便捷函数"""
    return generate_chunked_chapter_blueprint_prompt({
        'novel_architecture': novel_architecture,
        'chapter_list': chapter_list,
        'number_of_chapters': number_of_chapters,
        'start_chapter': start_chapter,
        'end_chapter': end_chapter,
        'user_guidance': user_guidance
    })
