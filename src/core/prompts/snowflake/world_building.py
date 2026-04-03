"""
世界观构建提示词
三维交织法构建世界观

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from typing import Dict, Any


def generate_world_building_prompt(params: Dict[str, Any]) -> str:
    """
    生成世界观构建提示词

    Args:
        params: 包含以下键的字典
            - genre: 小说类型
            - core_seed: 核心种子
            - user_guidance: 用户指导（可选）

    Returns:
        完整的提示词字符串
    """
    genre = params.get('genre', '通用')
    core_seed = params.get('core_seed', '')
    user_guidance = params.get('user_guidance', '')

    prompt = f"""基于以下元素：
- 小说类型：{genre}
- 内容指导：{user_guidance if user_guidance else '无'}
- 核心故事："{core_seed}"

为服务上述内容，请构建适合【{genre}】类型的世界观：

【1. 物理维度】
- 空间结构（地理环境、主要场景）
- 时间背景（故事发生的时代/时间跨度）
- 规则体系（该世界的基本运行法则）

【2. 社会维度】
- 社会结构（人物所处的社会环境）
- 文化氛围（风俗、习惯、价值观）
- 生活方式（日常生活的细节设定）

【3. 情感维度】
- 贯穿全书的核心意象（如反复出现的场景、物品、象征）
- 环境氛围与故事情感的呼应关系
- 场景设计如何强化【{genre}】类型的情感体验

**重要**：
- 世界观设计需服务于【{genre}】类型的核心体验
- 营造符合类型特点的氛围
- 每个维度至少包含3个可与角色决策产生互动的动态元素
- 避免设定堆砌，每个设定都要有实际作用

{f'''
用户额外指导：
{user_guidance}
''' if user_guidance else ''}

要求：
- 每个维度150-300字
- 仅给出最终文本，不要解释任何内容
- 设定要具体可操作，不要虚的"""

    return prompt


# 便捷函数
def create_world_building_prompt(
    genre: str,
    core_seed: str,
    user_guidance: str = ''
) -> str:
    """创建世界观构建提示词的便捷函数"""
    return generate_world_building_prompt({
        'genre': genre,
        'core_seed': core_seed,
        'user_guidance': user_guidance
    })
