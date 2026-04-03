"""
文件读取工具函数 — Gradio 功能模块的共享工具。

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import json
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


def read_uploaded_file(file_path) -> Tuple[str, str]:
    """
    读取上传的文件。

    Args:
        file_path: 文件路径

    Returns:
        (文件内容, 状态消息)
    """
    if not file_path:
        return "", "未选择文件"

    try:
        file = Path(file_path)
        suffix = file.suffix.lower()

        if suffix == '.txt':
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, f"✓ 成功读取文本文件 ({len(content)} 字)"

        elif suffix == '.md':
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, f"✓ 成功读取Markdown文件 ({len(content)} 字)"

        elif suffix == '.docx':
            try:
                from docx import Document
                doc = Document(file)
                paragraphs = [para.text for para in doc.paragraphs]
                content = '\n\n'.join(paragraphs)
                return content, f"✓ 成功读取Word文档 ({len(content)} 字)"
            except ImportError:
                return "", "❌ 需要安装 python-docx 库：pip install python-docx"
            except Exception as e:
                return "", f"❌ 读取Word文件失败: {str(e)}"

        elif suffix == '.json':
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 尝试提取章节内容
                if isinstance(data, dict):
                    chapters = data.get('chapters', [])
                    if chapters:
                        content = '\n\n'.join([
                            f"第{ch.get('num', '')}章 {ch.get('title', '')}\n\n{ch.get('content', '')}"
                            for ch in chapters if ch.get('content')
                        ])
                    else:
                        content = json.dumps(data, ensure_ascii=False, indent=2)
                else:
                    content = json.dumps(data, ensure_ascii=False, indent=2)
            return content, f"✓ 成功读取JSON文件 ({len(content)} 字)"

        else:
            return "", f"❌ 不支持的文件格式: {suffix}"

    except Exception as e:
        logger.error(f"读取文件失败: {e}", exc_info=True)
        return "", f"❌ 读取文件失败: {str(e)}"
