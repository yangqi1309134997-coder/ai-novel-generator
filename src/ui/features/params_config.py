"""
参数配置功能模块
管理生成参数、写作风格等全局配置

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import gradio as gr
import logging
import json
from typing import Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = Path("config/generation_config.json")


# 默认配置 - 针对小说生成优化的最佳值
DEFAULT_CONFIG = {
    "temperature": 0.78,  # 降低过度发散，兼顾创意与稳定性
    "top_p": 0.90,  # 保持词汇多样性，同时减少漂移
    "top_k": 50,  # 稍宽的候选词范围
    "max_tokens": 20000,  # 默认20K，支持长章节生成
    "target_words": 3000,  # 每章目标字数
    "writing_style": "详细生动",
    "writing_tone": "第三人称",
    "character_dev": "平衡发展",
    "plot_complexity": "中等复杂",
    # 上下文管理配置
    "context_enable": True,  # 启用上下文机制
    "context_mode": "summary",  # 上下文模式: summary(摘要), full(全文), disabled(关闭)
    "context_max_chapters": 60,  # 最大使用前面多少章作为上下文
    "context_auto_allocate": True  # 自动分配token（不超过max_tokens）
}


def load_config() -> Dict[str, Any]:
    """
    加载配置

    Returns:
        配置字典
    """
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置（确保所有键都存在）
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    保存配置

    Args:
        config: 配置字典

    Returns:
        (成功标志, 状态信息)
    """
    try:
        CONFIG_FILE.parent.mkdir(exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True, "配置已保存"
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return False, f"保存失败: {str(e)}"


def reset_config() -> Tuple[bool, str]:
    """
    重置配置为默认值

    Returns:
        (成功标志, 状态信息)
    """
    try:
        return save_config(DEFAULT_CONFIG.copy())
    except Exception as e:
        logger.error(f"重置配置失败: {e}")
        return False, f"重置失败: {str(e)}"


def create_params_config_ui(app_state):
    """
    创建参数配置UI

    Args:
        app_state: 应用状态对象

    Returns:
        Gradio Blocks对象
    """
    with gr.Blocks() as params_ui:
        gr.Markdown("## 📝 生成参数配置")
        gr.Markdown("### 调整小说生成的各项参数")

        # 加载当前配置
        current_config = load_config()

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 基础参数")

                temperature = gr.Slider(
                    minimum=0,
                    maximum=2,
                    value=current_config.get("temperature", 0.85),
                    step=0.05,
                    label="Temperature（温度）",
                    info="控制生成的随机性和创意。写小说建议：0.8-0.9（创意与连贯性平衡），0.9-1.0（更创意多变），0.6-0.8（更连贯稳定）"
                )

                top_p = gr.Slider(
                    minimum=0,
                    maximum=1,
                    value=current_config.get("top_p", 0.92),
                    step=0.01,
                    label="Top-P（核采样）",
                    info="控制词汇选择 diversity。写小说建议：0.90-0.95（平衡），0.95-1.0（更多样），0.85-0.90（更稳定）"
                )

                top_k = gr.Slider(
                    minimum=1,
                    maximum=100,
                    value=current_config.get("top_k", 40),
                    step=1,
                    label="Top-K",
                    info="每步考虑的前K个词汇"
                )

                max_tokens = gr.Slider(
                    minimum=100,
                    maximum=2000000,  # 最大支持 2M token
                    value=current_config.get("max_tokens", 20000),
                    step=1000,
                    label="Max Tokens（全局）",
                    info="所有API调用的最大token数（大纲生成、章节生成等共用）。建议：普通章节20K，长章节50K-100K，超长章节最高可达2M"
                )

            with gr.Column(scale=1):
                gr.Markdown("### 生成目标")

                target_words = gr.Number(
                    label="目标字数",
                    value=current_config.get("target_words", 3000),
                    minimum=100,
                    maximum=50000,
                    step=100,
                    info="每次生成的目标字数"
                )

                gr.Markdown("---")
                gr.Markdown("### 写作风格")

                writing_style = gr.Radio(
                    choices=["简洁明了", "详细生动", "华丽辞藻", "通俗易懂", "专业术语"],
                    value=current_config.get("writing_style", "详细生动"),
                    label="语言风格"
                )

                writing_tone = gr.Radio(
                    choices=["第一人称", "第三人称", "混合"],
                    value=current_config.get("writing_tone", "第三人称"),
                    label="叙述视角"
                )

                character_dev = gr.Radio(
                    choices=["快速成长", "平衡发展", "缓慢深入", "复杂多变"],
                    value=current_config.get("character_dev", "平衡发展"),
                    label="角色发展"
                )

                plot_complexity = gr.Radio(
                    choices=["简单直白", "中等复杂", "复杂交错", "宏大史诗"],
                    value=current_config.get("plot_complexity", "中等复杂"),
                    label="剧情复杂度"
                )

        # 上下文管理配置
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 上下文管理")

                context_enable = gr.Checkbox(
                    value=current_config.get("context_enable", True),
                    label="启用上下文机制",
                    info="使用前面章节的内容帮助生成连贯性"
                )

                with gr.Row():
                    context_mode = gr.Radio(
                        choices=["summary", "full", "disabled"],
                        value=current_config.get("context_mode", "summary"),
                        label="上下文模式",
                        info="summary：使用摘要；full：使用全文；disabled：关闭上下文"
                    )

                    context_auto_allocate = gr.Checkbox(
                        value=current_config.get("context_auto_allocate", True),
                        label="自动分配token",
                        info="根据max_tokens自动分配上下文token"
                    )

                context_max_chapters = gr.Slider(
                    minimum=1,
                    maximum=5000,
                    value=current_config.get("context_max_chapters", 50),
                    step=10,
                    label="使用前面多少章",
                    info="最多使用前面多少章作为上下文（例如：第55章使用前50章，前4章不使用）。长篇建议500-2000章。"
                )

                gr.Markdown("""
**上下文模式说明：**
- **summary（摘要模式）**：使用章节摘要，节省token，适合长篇小说
- **full（全文模式）**：使用完整章节内容，连贯性更好，消耗token更多
- **disabled（关闭）**：不使用上下文，生成速度更快但连贯性降低

**Token自动分配**：
启用后，系统会自动将可用token按比例分配给角色、剧情、世界观等上下文元素。
                """, visible=True)

        with gr.Row():
            save_btn = gr.Button("💾 保存配置", variant="primary")
            reset_btn = gr.Button("🔄 重置为默认", variant="secondary")
            test_btn = gr.Button("🧪 测试参数", variant="secondary")

        status_output = gr.Textbox(
            label="状态",
            interactive=False,
            lines=2
        )

        # 事件处理
        def on_save(temp, top_p_val, top_k_val, max_tok, target, style, tone, char_dev, plot,
                    context_en, context_m, context_max_ch, context_auto):
            config = {
                "temperature": temp,
                "top_p": top_p_val,
                "top_k": top_k_val,
                "max_tokens": max_tok,
                "target_words": int(target),
                "writing_style": style,
                "writing_tone": tone,
                "character_dev": char_dev,
                "plot_complexity": plot,
                # 上下文管理配置
                "context_enable": context_en,
                "context_mode": context_m,
                "context_max_chapters": context_max_ch,
                "context_auto_allocate": context_auto
            }
            success, msg = save_config(config)
            if success:
                # 更新全局配置（需要重启应用以生效）
                return f"✓ {msg}\n注意：部分参数需要重启应用后生效"
            else:
                return f"✗ {msg}"

        def on_reset():
            success, msg = reset_config()
            if success:
                return f"✓ {msg}\n请刷新页面"
            else:
                return f"✗ {msg}"

        def on_test():
            config = load_config()
            temp = config['temperature']
            top_p_val = config['top_p']

            # 根据参数值给出建议
            temp_advice = ""
            if temp < 0.7:
                temp_advice = "（较低，生成更稳定但创意较少）"
            elif temp < 0.85:
                temp_advice = "（适中，适合大多数小说类型）"
            elif temp < 0.95:
                temp_advice = "（较高，创意性更强）"
            else:
                temp_advice = "（很高，非常创意但可能不够连贯）"

            tokens_advice = ""
            if config['max_tokens'] < 10000:
                tokens_advice = "（适合短章节）"
            elif config['max_tokens'] < 50000:
                tokens_advice = "（适合普通章节，推荐）"
            elif config['max_tokens'] < 100000:
                tokens_advice = "（适合长章节）"
            else:
                tokens_advice = "（超大配置，适合超长章节）"

            # 上下文配置信息
            context_info = ""
            if config.get('context_enable', True):
                mode = config.get('context_mode', 'summary')
                mode_text = {
                    'summary': '摘要模式（节省token）',
                    'full': '全文模式（连贯性更好）',
                    'disabled': '已关闭'
                }.get(mode, mode)

                max_ch = config.get('context_max_chapters', 50)
                auto_alloc = config.get('context_auto_allocate', True)

                context_info = f"""📚 上下文管理：
• 状态: {'✅ 已启用' if mode != 'disabled' else '❌ 已关闭'}
• 模式: {mode_text}
• 最大章节数: {max_ch}
• 自动分配: {'✅' if auto_alloc else '❌'}"""
            else:
                context_info = "📚 上下文管理: ❌ 已关闭"

            return f"""📊 当前生成参数配置：

🎛️ 基础模型参数：
• Temperature: {temp} {temp_advice}
• Top-P: {top_p_val}
• Top-K: {config['top_k']}
• Max Tokens: {config['max_tokens']:,} {tokens_advice}

📝 生成目标：
• 每章目标字数: {config['target_words']}

✍️ 写作风格：
• 语言风格: {config['writing_style']}
• 叙述视角: {config['writing_tone']}
• 角色发展: {config['character_dev']}
• 剧情复杂度: {config['plot_complexity']}

{context_info}

✅ 这些参数将在下次生成时自动生效"""

        # 绑定事件
        save_btn.click(
            fn=on_save,
            inputs=[
                temperature, top_p, top_k, max_tokens, target_words,
                writing_style, writing_tone, character_dev, plot_complexity,
                context_enable, context_mode, context_max_chapters, context_auto_allocate
            ],
            outputs=[status_output]
        )

        reset_btn.click(
            fn=on_reset,
            outputs=[status_output]
        )

        test_btn.click(
            fn=on_test,
            outputs=[status_output]
        )

    return params_ui
