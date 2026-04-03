"""
雪花写作法提示词系统
基于 huobao-novel 项目优化

核心概念：
1. 核心种子 - 单句概括故事本质
2. 角色动力学 - 驱动力三角 + 角色弧线
3. 世界观构建 - 物理社会情感三维
4. 情节架构 - 三幕式悬念结构
5. 章节蓝图 - 节奏曲线设计
6. 角色状态 - 动态状态追踪

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from .core_seed import generate_core_seed_prompt
from .character_dynamics import generate_character_dynamics_prompt
from .world_building import generate_world_building_prompt
from .plot_architecture import generate_plot_architecture_prompt
from .character_state import generate_character_state_prompt
from .chapter_blueprint import (
    generate_chapter_blueprint_prompt,
    generate_chunked_chapter_blueprint_prompt
)
from .chapter_generation import (
    generate_first_chapter_prompt,
    generate_next_chapter_prompt,
    generate_enrich_chapter_prompt,
    create_first_chapter_prompt,
    create_next_chapter_prompt,
    create_enrich_chapter_prompt
)
from .manager import (
    SnowflakeManager,
    SnowflakeArchitecture,
    SnowflakeConfig,
    create_snowflake_manager
)
from .parser import (
    ChapterBlueprintParser,
    ChapterInfo,
    parse_chapter_blueprint,
    get_chapter_info
)

__all__ = [
    # 提示词生成函数
    'generate_core_seed_prompt',
    'generate_character_dynamics_prompt',
    'generate_world_building_prompt',
    'generate_plot_architecture_prompt',
    'generate_character_state_prompt',
    'generate_chapter_blueprint_prompt',
    'generate_chunked_chapter_blueprint_prompt',
    'generate_first_chapter_prompt',
    'generate_next_chapter_prompt',
    'generate_enrich_chapter_prompt',
    'create_first_chapter_prompt',
    'create_next_chapter_prompt',
    'create_enrich_chapter_prompt',

    # 管理器
    'SnowflakeManager',
    'SnowflakeArchitecture',
    'SnowflakeConfig',
    'create_snowflake_manager',

    # 解析器
    'ChapterBlueprintParser',
    'ChapterInfo',
    'parse_chapter_blueprint',
    'get_chapter_info',
]
