"""
角色状态提示词
生成初始角色状态文档

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from typing import Dict, Any


def generate_character_state_prompt(params: Dict[str, Any]) -> str:
    """
    生成角色状态提示词

    Args:
        params: 包含以下键的字典
            - character_dynamics: 角色动力学

    Returns:
        完整的提示词字符串
    """
    character_dynamics = params.get('character_dynamics', '')

    prompt = f"""依据当前角色动力学设定：
{character_dynamics}

请生成一个角色状态文档，用于追踪角色在故事中的动态变化。

格式示例：
```
张三：
├── 物品:
│   ├── 青衫：一件破损的青色长袍，带有暗红色的污渍
│   └── 寒铁长剑：一柄断裂的铁剑，剑身上刻有古老的符文
├── 能力
│   ├── 技能1：强大的精神感知能力 - 能够察觉到周围人的心中活动
│   └── 技能2：无形攻击 - 能够释放一种无法被视觉捕捉的精神攻击
├── 状态
│   ├── 身体状态: 身材挺拔，穿着华丽的铠甲，面色冷峻
│   └── 心理状态: 目前的心态比较平静，但内心隐藏着对柳溪镇未来掌控的野心和不安
├── 主要角色间关系网
│   ├── 李四：张三从小就与她有关联，对她的成长一直保持关注
│   └── 王二：两人之间有着复杂的过去，最近因一场冲突而让对方感到威胁
└── 触发或加深的事件
    ├── 村庄内突然出现不明符号：这个不明符号似乎在暗示柳溪镇即将发生重大事件
    └── 李四被刺穿皮肤：这次事件让两人意识到对方的强大实力，促使他们迅速离开队伍
```

要求：
- 为每个主要角色创建详细的状态档案
- 物品要具体，有故事性
- 能力要符合世界观设定
- 状态要体现角色当前的情况
- 关系网要清晰明确
- 事件要记录对角色产生影响的重大事件

仅返回编写好的角色状态文本，不要解释任何内容。"""

    return prompt


# 便捷函数
def create_character_state_prompt(
    character_dynamics: str
) -> str:
    """创建角色状态提示词的便捷函数"""
    return generate_character_state_prompt({
        'character_dynamics': character_dynamics
    })
