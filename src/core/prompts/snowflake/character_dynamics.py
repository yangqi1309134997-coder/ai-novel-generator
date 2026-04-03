"""
角色动力学提示词
设计具有动态变化潜力的核心角色

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from typing import Dict, Any


def generate_character_dynamics_prompt(params: Dict[str, Any]) -> str:
    """
    生成角色动力学提示词

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
- 核心种子：{core_seed}

请设计3-6个具有动态变化潜力的核心角色，每个角色需包含：

【角色特征】
- 背景、外貌、性别、年龄、职业等
- 角色独特之处或成长空间

【核心驱动力三角】
- 表面追求（物质目标）：表面上想要得到的东西
- 深层渴望（情感需求）：内心真正渴望的东西
- 灵魂需求（哲学层面）：人生价值观层面的追求

【角色弧线设计】
初始状态 → 触发事件 → 内心转变 → 成长节点 → 最终状态

【角色关系网】（根据【{genre}】类型调整）：
- 与其他角色的关系和互动模式
- 角色间的羁绊或张力来源
- 情感连接点（友情/爱情/亲情/信任等）
- 可能的误解或需要跨越的障碍

**重要**：
- 角色设计需符合【{genre}】类型的情感基调
- 每个角色都要有成长的潜力
- 角色之间要有冲突和张力
- 避免脸谱化，要有复杂性和深度

{f'''
用户额外指导：
{user_guidance}
''' if user_guidance else ''}

要求：
- 每个角色描述200-400字
- 仅给出最终文本，不要解释任何内容
- 角色之间要有明确的互动关系
- 包含主角和重要配角"""

    return prompt


# 便捷函数
def create_character_dynamics_prompt(
    genre: str,
    core_seed: str,
    user_guidance: str = ''
) -> str:
    """创建角色动力学提示词的便捷函数"""
    return generate_character_dynamics_prompt({
        'genre': genre,
        'core_seed': core_seed,
        'user_guidance': user_guidance
    })
