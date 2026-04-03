"""
情节架构提示词
三幕式悬念结构

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from typing import Dict, Any


def generate_plot_architecture_prompt(params: Dict[str, Any]) -> str:
    """
    生成情节架构提示词

    Args:
        params: 包含以下键的字典
            - genre: 小说类型
            - core_seed: 核心种子
            - character_dynamics: 角色动力学
            - world_building: 世界观
            - user_guidance: 用户指导（可选）

    Returns:
        完整的提示词字符串
    """
    genre = params.get('genre', '通用')
    core_seed = params.get('core_seed', '')
    character_dynamics = params.get('character_dynamics', '')
    world_building = params.get('world_building', '')
    user_guidance = params.get('user_guidance', '')

    prompt = f"""基于以下元素：
- 小说类型：{genre}
- 内容指导：{user_guidance if user_guidance else '无'}
- 核心种子：{core_seed}
- 角色体系：{character_dynamics}
- 世界观：{world_building}

请根据【{genre}】类型设计三幕式情节架构：

【第一幕（开端）】
- 日常状态展示（3处场景铺垫，体现【{genre}】的氛围）
- 引出故事：展示主线、感情线、副线的开端
- 契机事件：推动故事发展的触发点（改变角色关系或状态）
- 初步反应：主角面对变化的第一反应

【第二幕（发展）】
- 剧情深入：主线+感情线的交织发展
- 挑战与成长：角色面临的困难和内心变化
- 情感升温/矛盾激化：关系发展的关键节点
- 重要转折：改变故事走向的关键时刻

【第三幕（高潮与结局）】
- 核心冲突爆发：故事的高潮部分
- 角色抉择：主角做出重要决定
- 情感/事件收尾：符合【{genre}】类型的结局处理

**重要**：
- 情节设计需符合【{genre}】类型读者的期待
- 确保情感基调一致
- 每个阶段需包含3个关键节点及其伏笔设计
- 节奏要张弛有度
- 高潮要有冲击力

{f'''
用户额外指导：
{user_guidance}
''' if user_guidance else ''}

要求：
- 每个幕300-500字
- 仅给出最终文本，不要解释任何内容
- 确保情节逻辑连贯
- 伏笔要自然埋设"""

    return prompt


# 便捷函数
def create_plot_architecture_prompt(
    genre: str,
    core_seed: str,
    character_dynamics: str,
    world_building: str,
    user_guidance: str = ''
) -> str:
    """创建情节架构提示词的便捷函数"""
    return generate_plot_architecture_prompt({
        'genre': genre,
        'core_seed': core_seed,
        'character_dynamics': character_dynamics,
        'world_building': world_building,
        'user_guidance': user_guidance
    })
