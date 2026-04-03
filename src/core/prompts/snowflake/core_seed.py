"""
核心种子提示词
雪花写作法第一步 - 用单句概括故事本质

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from typing import Dict, Any


def generate_core_seed_prompt(params: Dict[str, Any]) -> str:
    """
    生成核心种子提示词

    Args:
        params: 包含以下键的字典
            - topic: 主题
            - genre: 小说类型
            - number_of_chapters: 章节数
            - word_number: 每章字数
            - user_guidance: 用户指导（可选）

    Returns:
        完整的提示词字符串
    """
    topic = params.get('topic', '')
    genre = params.get('genre', '通用')
    number_of_chapters = params.get('number_of_chapters', 50)
    word_number = params.get('word_number', 3000)
    user_guidance = params.get('user_guidance', '')

    prompt = f"""作为专业作家，请用"雪花写作法"第一步构建故事核心：

主题：{topic}
类型：{genre}
篇幅：约{number_of_chapters}章（每章{word_number}字）

请根据【{genre}】类型的特点，用单句公式概括故事本质。

不同类型的示例：
- 悬疑/惊悚类："当[主角]遭遇[核心事件]，必须[关键行动]，否则[灾难后果]；与此同时，[隐藏的更大危机]正在发酵。"
- 言情/温馨类："当[主角]在[背景环境]中遇见[另一角色]，两人因[契机]产生羁绊，在[成长/治愈过程]中收获[情感结局]。"
- 玄幻/仙侠类："当[主角]获得[机缘]，踏上[修炼之路]，面对[挑战]，逐步成长为[最终成就]。"
- 都市/现实类："当[主角]面临[现实困境]，通过[努力方式]，实现[人生目标]，同时收获[情感/成长]。"
- 科幻/未来类："当[科技突破/灾难发生]，[主角]在[未来世界]中，为[目标]而[行动]，最终[结局]。"
- 武侠/江湖类："当[主角]身怀[秘密/宝物]，踏入[江湖纷争]，在[成长历程]中，最终[成就/结局]。"

要求：
1. **严格遵循【{genre}】类型的核心特征和情感基调**
2. 体现人物核心驱动力
3. 暗示世界观或故事背景的关键特点
4. 使用25-100字精准表达
5. 包含冲突、转折和情感内核
6. 让读者一眼就能看出故事的核心吸引力

{f'''
用户额外指导：
{user_guidance}
''' if user_guidance else ''}

仅返回故事核心文本，不要解释任何内容。"""

    return prompt


# 便捷函数
def create_core_seed_prompt(
    topic: str,
    genre: str,
    number_of_chapters: int = 50,
    word_number: int = 3000,
    user_guidance: str = ''
) -> str:
    """创建核心种子提示词的便捷函数"""
    return generate_core_seed_prompt({
        'topic': topic,
        'genre': genre,
        'number_of_chapters': number_of_chapters,
        'word_number': word_number,
        'user_guidance': user_guidance
    })
