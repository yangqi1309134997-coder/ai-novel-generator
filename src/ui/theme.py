"""
AI Novel Generator 4.5 - 共享主题定义

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import gradio as gr
from gradio.themes.utils import sizes

CUSTOM_THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.teal,
    secondary_hue=gr.themes.colors.slate,
    neutral_hue=gr.themes.colors.slate,
    font=gr.themes.GoogleFont("Noto Sans SC"),
    radius_size=sizes.radius_lg,
).set(
    body_background_fill="#f0f4f8",
    body_text_color="#1e293b",
    body_text_color_subdued="#475569",
    background_fill_primary="#ffffff",
    background_fill_secondary="#f1f5f9",
    border_color_primary="#cbd5e1",
    color_accent="#0d9488",
    color_accent_soft="#ccfbf1",
    button_primary_background_fill="#0d9488",
    button_primary_background_fill_hover="#0f766e",
    button_primary_text_color="#ffffff",
    button_secondary_background_fill="#e2e8f0",
    button_secondary_background_fill_hover="#cbd5e1",
    button_secondary_text_color="#1e293b",
    input_background_fill="#ffffff",
    input_border_color="#94a3b8",
    input_border_color_focus="#0d9488",
    input_placeholder_color="#94a3b8",
    block_title_text_color="#0f172a",
    block_label_text_color="#334155",
    block_background_fill="#ffffff",
    block_border_color="#e2e8f0",
    checkbox_background_color="#ffffff",
    checkbox_background_color_selected="#0d9488",
    checkbox_border_color="#94a3b8",
    checkbox_border_color_selected="#0d9488",
    checkbox_label_text_color="#1e293b",
    link_text_color="#0d9488",
    link_text_color_hover="#0f766e",
    shadow_drop="0 4px 12px rgba(0, 0, 0, 0.08)",
    shadow_drop_lg="0 8px 24px rgba(0, 0, 0, 0.12)",
)
