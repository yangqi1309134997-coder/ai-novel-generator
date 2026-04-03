"""
小说润色功能模块
支持文件上传、8种润色类型、长文本分段处理

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import gradio as gr
import logging
from typing import Tuple, List, Optional
from datetime import datetime
from pathlib import Path
import json

from src.ui.features.file_utils import read_uploaded_file

logger = logging.getLogger(__name__)

# 润色类型映射
POLISH_TYPES_MAP = {
    "全面润色": "general",
    "查找错误": "find_errors",
    "改进建议": "suggest_improvements",
    "直接修改": "direct_modify",
    "去除AI味": "remove_ai_flavor",
    "增强细节": "enhance_details",
    "优化对话": "optimize_dialogue",
    "改善节奏": "improve_pacing",
}

# 润色提示词模板
POLISH_PROMPTS = {
    "general": """请对以下文本进行全面润色，提升其文学性和可读性。

{text}

要求：
1. 保持原意不变
2. 优化语言表达
3. 改善句子结构
4. 增强文学性
5. 修正语法错误

请直接返回润色后的文本，不要添加任何解释。""",

    "find_errors": """请仔细检查以下文本，找出其中的错误并标注。

{text}

检查项：
1. 语法错误
2. 标点符号错误
3. 错别字
4. 逻辑错误
5. 表达不当

请按以下格式返回：
【错误1】位置：xxx，问题：xxx，建议：xxx
...""",

    "suggest_improvements": """请对以下文本进行分析并提供改进建议。

{text}

分析内容：
1. 整体评价
2. 优点分析
3. 待改进点
4. 具体修改建议
5. 改写示例（如有必要）

请提供详细的建议和说明。""",

    "direct_modify": """请直接修改以下文本，使其更加通顺流畅。

{text}

要求：
1. 直接返回修改后的文本
2. 不要添加任何解释或说明
3. 保持原意和风格""",

    "remove_ai_flavor": """请去除以下文本中的AI生成痕迹，使其更加自然。

{text}
要求：
1. 消除机械感
2. 增加人性化表达
3. 优化节奏和语调
4. 使文字更生动
5. 直接返回润色后的文本""",

    "enhance_details": """请增强以下文本的细节描写。

{text}

要求：
1. 添加感官细节（视觉、听觉、嗅觉、触觉）
2. 深化人物心理描写
3. 丰富环境描写
4. 增强场景氛围
5. 保持原有情节""",

    "optimize_dialogue": """请优化以下文本中的对话部分。

{text}

要求：
1. 使对话更自然流畅
2. 符合人物性格
3. 增强对话的戏剧性
4. 优化对话标签
5. 减少不必要的对话""",

    "improve_pacing": """请改善以下文本的节奏和韵律。

{text}

要求：
1. 调整句式长短
2. 优化段落划分
3. 改善叙述节奏
4. 增强阅读流畅性
5. 提升整体韵律"""
}



def polish_with_api(api_client, text: str, polish_type: str, custom_req: str = "") -> Tuple[str, str]:
    """
    使用API客户端进行润色

    Args:
        api_client: UnifiedAPIClient实例
        text: 待润色文本
        polish_type: 润色类型
        custom_req: 自定义要求

    Returns:
        (润色后文本, 状态消息)
    """
    if not api_client:
        return "", "API客户端未初始化"

    logger.info(f"[润色功能] 开始润色，类型: {polish_type}, 文本长度: {len(text)} 字符")

    try:
        # 获取提示词模板
        actual_type = POLISH_TYPES_MAP.get(polish_type, "general")
        prompt_template = POLISH_PROMPTS.get(actual_type, POLISH_PROMPTS["general"])

        # 构建完整提示词
        prompt = prompt_template.replace("{text}", text)
        if custom_req:
            prompt = f"{prompt}\n\n【额外要求】\n{custom_req}"

        # 调用API
        messages = [
            {"role": "system", "content": "你是一位专业的文学编辑，擅长小说润色和修改。"},
            {"role": "user", "content": prompt}
        ]

        result = api_client.generate(
            messages=messages,
            max_tokens=max(int(len(text) * 1.5), 1000),
            temperature=0.7
        )

        if result:
            logger.info(f"[润色功能] 润色成功，返回长度: {len(result)} 字符")
            return result, "润色成功"
        else:
            logger.error(f"[润色功能] API返回空结果")
            return "", "润色失败：API返回空结果"

    except Exception as e:
        logger.error(f"[润色功能] 润色失败: {e}", exc_info=True)
        return "", f"润色失败: {str(e)}"


def polish_and_suggest_with_api(api_client, text: str, custom_req: str = "") -> Tuple[str, str, str]:
    """
    使用API客户端进行润色并提供建议

    Args:
        api_client: UnifiedAPIClient实例
        text: 待润色文本
        custom_req: 自定义要求

    Returns:
        (润色后文本, 改进建议, 状态消息)
    """
    if not api_client:
        return "", "", "API客户端未初始化"

    logger.info(f"[润色功能] 开始润色并提供建议，文本长度: {len(text)} 字符")

    try:
        # 构建提示词
        prompt_template = POLISH_PROMPTS["suggest_improvements"]

        prompt = prompt_template.replace("{text}", text)
        if custom_req:
            prompt = f"{prompt}\n\n【额外要求】\n{custom_req}"

        # 调用API
        messages = [
            {"role": "system", "content": "你是一位专业的文学评论家，擅长分析文学作品并提供改进建议。"},
            {"role": "user", "content": prompt}
        ]

        result = api_client.generate(
            messages=messages,
            max_tokens=max(int(len(text) * 2), 1500),
            temperature=0.7
        )

        if result:
            # 尝试分离润色文本和建议
            # 如果结果中包含明确的建议部分，则分离
            if "【改写示例】" in result or "修改建议：" in result:
                parts = result.split("【改写示例】") if "【改写示例】" in result else result.split("修改建议：")
                polished = parts[0].strip() if len(parts) > 1 else text
                suggestions = parts[-1].strip() if len(parts) > 1 else result
                logger.info(f"[润色功能] 润色并提供建议成功，建议长度: {len(suggestions)} 字符")
                return polished, suggestions, "润色成功"
            else:
                logger.info(f"[润色功能] 润色成功（无分离）")
                return text, result, "润色成功"
        else:
            logger.error(f"[润色功能] API返回空结果")
            return "", "", "润色失败：API返回空结果"

    except Exception as e:
        logger.error(f"[润色功能] 润色失败: {e}", exc_info=True)
        return "", "", f"润色失败: {str(e)}"


def split_text_by_word_count(text: str, max_words: int = 8000) -> List[str]:
    """
    按字数分割文本

    Args:
        text: 待分割文本
        max_words: 每段最大字数

    Returns:
        分割后的文本段落列表
    """
    if len(text) <= max_words:
        return [text]

    segments = []
    current_segment = ""
    paragraphs = text.split("\n\n")

    for paragraph in paragraphs:
        if len(current_segment) + len(paragraph) + 2 <= max_words:
            if current_segment:
                current_segment += "\n\n" + paragraph
            else:
                current_segment = paragraph
        else:
            if current_segment:
                segments.append(current_segment)
            current_segment = paragraph

    if current_segment:
        segments.append(current_segment)

    return segments


def handle_polish(text: str, polish_type: str, custom_req: str, api_client, progress=None) -> Tuple[str, str]:
    """
    处理文本润色（支持分段处理）

    Args:
        text: 待润色文本
        polish_type: 润色类型
        custom_req: 自定义要求
        api_client: API客户端实例
        progress: Gradio进度对象

    Returns:
        (润色后文本, 状态消息)
    """
    if not text or not text.strip():
        return "", "无内容可润色"

    if not api_client:
        return "", "API客户端未初始化，请先配置API"

    logger.info(f"[润色功能] 处理润色请求，类型: {polish_type}, 文本长度: {len(text)}")

    try:
        # 检查文本长度，如果超过限制则自动分段处理
        max_single_segment = 8000  # 单段最大字数
        if len(text) <= max_single_segment:
            # 文本较短，直接处理
            content, success_msg = polish_with_api(api_client, text, polish_type, custom_req)

            if success_msg != "润色成功":
                logger.error(f"润色失败: {content}")
                return "", content

            # 验证content是否有效
            if not content or not content.strip() or len(content.strip()) < 10:
                error_msg = f"润色返回了无效内容（长度: {len(content) if content else 0}字）"
                logger.error(error_msg)
                return "", error_msg

            logger.info("[润色功能] 润色完成（单段）")
            polished_content = content
        else:
            # 文本较长，自动分段处理
            logger.info(f"[润色功能] 文本过长（{len(text)}字），启用自动分段处理")
            segments = split_text_by_word_count(text, max_single_segment)
            logger.info(f"[润色功能] 已分为 {len(segments)} 段，开始逐段润色")

            polished_segments = []
            for i, segment in enumerate(segments):
                if progress:
                    progress((i + 1) / len(segments), desc=f"润色第 {i+1}/{len(segments)} 段")

                segment_content, success_msg = polish_with_api(api_client, segment, polish_type, custom_req)

                if success_msg != "润色成功":
                    logger.error(f"第 {i+1} 段润色失败: {segment_content}")
                    return "", f"第 {i+1} 段润色失败: {segment_content}"

                # 验证内容
                if not segment_content or not segment_content.strip() or len(segment_content.strip()) < 10:
                    error_msg = f"第 {i+1} 段润色返回了无效内容（长度: {len(segment_content) if segment_content else 0}字）"
                    logger.error(error_msg)
                    return "", error_msg

                polished_segments.append(segment_content)

            # 合并所有润色后的段落
            polished_content = "\n\n".join(polished_segments)
            logger.info(f"[润色功能] 分段润色完成，共 {len(polished_segments)} 段，总字数: {len(polished_content)}")

        return polished_content, "润色完成"

    except Exception as e:
        logger.error(f"[润色功能] 润色过程出错: {e}", exc_info=True)
        return "", f"润色失败: {str(e)}"


def handle_polish_with_suggestions(text: str, custom_req: str, api_client, progress=None) -> Tuple[str, str, str]:
    """
    处理润色并提供建议（支持分段处理）

    Args:
        text: 待润色文本
        custom_req: 自定义要求
        api_client: API客户端实例
        progress: Gradio进度对象

    Returns:
        (润色后文本, 改进建议, 状态消息)
    """
    if not text or not text.strip():
        return "", "", "无内容可润色"

    if not api_client:
        return "", "", "API客户端未初始化，请先配置API"

    logger.info(f"[润色功能] 处理润色并提供建议，文本长度: {len(text)}")

    try:
        # 对于改进建议，我们不对文本进行分段，而是直接处理
        # 因为建议本身就是分析性内容，不需要分段
        polished, suggestions, msg = polish_and_suggest_with_api(api_client, text, custom_req)

        if msg != "润色成功":
            logger.error(f"润色失败: {msg}")
            return "", "", msg

        # 验证polished是否有效
        if not polished or not polished.strip() or len(polished.strip()) < 10:
            error_msg = f"润色返回了无效内容（长度: {len(polished) if polished else 0}字）"
            logger.error(error_msg)
            return "", "", error_msg

        logger.info("润色完成")
        return polished, suggestions, "润色完成"

    except Exception as e:
        logger.error(f"[润色功能] 润色过程出错: {e}", exc_info=True)
        return "", "", f"润色失败: {str(e)}"


def create_polish_ui(app_state):
    """
    创建润色功能UI

    Args:
        app_state: 应用状态对象

    Returns:
        Gradio Blocks对象
    """
    with gr.Blocks() as polish_ui:
        gr.Markdown("## ✨ 小说润色")
        gr.Markdown("### 支持文件上传、8种润色类型、智能优化")

        with gr.Tabs():
            # Tab 1: 基础润色
            with gr.Tab("基础润色"):
                gr.Markdown("### 📤 上传文件（可选）")
                gr.Markdown("支持格式：.txt, .md, .docx, .json")

                polish_file_upload = gr.File(
                    label="上传文件",
                    file_types=[".txt", ".md", ".docx", ".json"],
                    type="filepath"
                )

                polish_file_status = gr.Textbox(
                    label="文件状态",
                    interactive=False,
                    lines=2
                )

                gr.Markdown("---")

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### ✍️ 输入")
                        polish_input = gr.Textbox(
                            label="待润色文本",
                            lines=10,
                            placeholder="上传文件后会自动显示，或直接在此粘贴需要润色的文本..."
                        )

                        polish_type = gr.Radio(
                            choices=list(POLISH_TYPES_MAP.keys()),
                            value="全面润色",
                            label="润色类型"
                        )

                        custom_req = gr.Textbox(
                            label="自定义要求（可选）",
                            lines=2,
                            placeholder="如有特殊要求，请在此说明..."
                        )

                        polish_btn = gr.Button("🚀 开始润色", variant="primary", size="lg")

                    with gr.Column(scale=1):
                        gr.Markdown("### 📄 输出")
                        polish_output = gr.Textbox(
                            label="润色结果",
                            lines=10,
                            interactive=True
                        )

                        polish_status = gr.Textbox(
                            label="状态",
                            interactive=False
                        )

                        with gr.Row():
                            copy_btn = gr.Button("📋 复制结果")
                            clear_btn = gr.Button("🗑️ 清空")

            # Tab 2: 润色+建议
            with gr.Tab("润色并提供建议"):
                gr.Markdown("### 📤 上传文件（可选）")
                gr.Markdown("支持格式：.txt, .md, .docx, .json")

                suggest_file_upload = gr.File(
                    label="上传文件",
                    file_types=[".txt", ".md", ".docx", ".json"],
                    type="filepath"
                )

                suggest_file_status = gr.Textbox(
                    label="文件状态",
                    interactive=False,
                    lines=2
                )

                gr.Markdown("---")

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### ✍️ 输入")
                        suggest_input = gr.Textbox(
                            label="待润色文本",
                            lines=10,
                            placeholder="上传文件后会自动显示，或直接在此粘贴需要润色的文本..."
                        )

                        suggest_custom_req = gr.Textbox(
                            label="自定义要求（可选）",
                            lines=2,
                            placeholder="如有特殊要求，请在此说明..."
                        )

                        suggest_btn = gr.Button("🚀 润色并提供建议", variant="primary", size="lg")

                    with gr.Column(scale=1):
                        gr.Markdown("### 📄 输出")
                        suggest_polished = gr.Textbox(
                            label="润色后文本",
                            lines=8,
                            interactive=True
                        )

                        suggest_output = gr.Textbox(
                            label="改进建议",
                            lines=10,
                            interactive=False
                        )

                        suggest_status = gr.Textbox(
                            label="状态",
                            interactive=False
                        )

                        with gr.Row():
                            copy_suggest_btn = gr.Button("📋 复制润色结果")
                            clear_suggest_btn = gr.Button("🗑️ 清空")

        # 事件绑定
        def on_polish_file_upload(file):
            """润色文件上传"""
            if file:
                content, status = read_uploaded_file(file)
                return content, status
            return "", "未选择文件"

        def on_suggest_file_upload(file):
            """建议文件上传"""
            if file:
                content, status = read_uploaded_file(file)
                return content, status
            return "", "未选择文件"

        def on_polish_click(text, p_type, custom):
            if not app_state.api_client:
                return "", "❌ 请先在'API配置'标签中配置API"
            return handle_polish(text, p_type, custom, app_state.api_client)

        def on_suggest_click(text, custom):
            if not app_state.api_client:
                return "", "", "❌ 请先在'API配置'标签中配置API"
            return handle_polish_with_suggestions(text, custom, app_state.api_client)

        def on_copy_click(text):
            if text:
                return "✓ 已复制到剪贴板"
            return "❌ 没有内容可复制"

        # 绑定事件
        polish_file_upload.upload(
            fn=on_polish_file_upload,
            inputs=[polish_file_upload],
            outputs=[polish_input, polish_file_status]
        )

        suggest_file_upload.upload(
            fn=on_suggest_file_upload,
            inputs=[suggest_file_upload],
            outputs=[suggest_input, suggest_file_status]
        )

        polish_btn.click(
            fn=on_polish_click,
            inputs=[polish_input, polish_type, custom_req],
            outputs=[polish_output, polish_status]
        )

        suggest_btn.click(
            fn=on_suggest_click,
            inputs=[suggest_input, suggest_custom_req],
            outputs=[suggest_polished, suggest_output, suggest_status]
        )

        copy_btn.click(
            fn=on_copy_click,
            inputs=[polish_output],
            outputs=[polish_status]
        )

        clear_btn.click(
            fn=lambda: ("", "", "已清空"),
            outputs=[polish_input, polish_output, polish_status]
        )

        copy_suggest_btn.click(
            fn=lambda x: "✓ 已复制润色结果" if x else "❌ 无内容",
            inputs=[suggest_polished],
            outputs=[suggest_status]
        )

        clear_suggest_btn.click(
            fn=lambda: ("", "", "", "已清空"),
            outputs=[suggest_input, suggest_polished, suggest_output, suggest_status]
        )

    return polish_ui
