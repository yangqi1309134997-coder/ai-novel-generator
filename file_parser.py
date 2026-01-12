"""
文件解析模块 - 支持 txt/pdf/epub，带进度跟踪和错误处理

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import os
import re
import logging
import tempfile
from typing import Tuple, List, Optional, IO
from enum import Enum

logger = logging.getLogger(__name__)

# 常量
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MIN_PARAGRAPH_LENGTH = 20  # 最小段落长度


class FileType(Enum):
    """文件类型"""
    TXT = "txt"
    PDF = "pdf"
    EPUB = "epub"
    UNKNOWN = "unknown"


def get_file_type(file_path: str) -> FileType:
    """获取文件类型"""
    if not file_path:
        return FileType.UNKNOWN
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".txt":
        return FileType.TXT
    elif ext == ".pdf":
        return FileType.PDF
    elif ext == ".epub":
        return FileType.EPUB
    else:
        return FileType.UNKNOWN


def parse_txt_file(file_path: str) -> Tuple[List[str], str]:
    """
    解析TXT文件
    
    Returns:
        (段落列表, 状态信息)
    """
    try:
        # 支持传入文件对象或路径
        if hasattr(file_path, 'read'):
            fobj: IO = file_path
            # 尝试获取 size 属性
            try:
                fobj.seek(0, os.SEEK_END)
                file_size = fobj.tell()
                fobj.seek(0)
            except Exception:
                file_size = 0
        else:
            file_size = os.path.getsize(file_path)

        if file_size and file_size > MAX_FILE_SIZE:
            return [], f"错误：文件过大 ({file_size / 1024 / 1024:.1f}MB > 50MB)"

        paragraphs: List[str] = []
        buf_lines: List[str] = []
        total_chars = 0

        # 逐行读取以降低内存压力
        if hasattr(file_path, 'read'):
            stream = file_path
        else:
            stream = open(file_path, 'r', encoding='utf-8', errors='ignore')

        try:
            for line in stream:
                stripped = line.rstrip('\n')
                total_chars += len(stripped)

                if stripped.strip() == '':
                    # 空行 -> 段落结束
                    if buf_lines:
                        para = '\n'.join(buf_lines).strip()
                        if len(para) >= MIN_PARAGRAPH_LENGTH:
                            paragraphs.append(para)
                        buf_lines = []
                    continue

                # 常规行
                buf_lines.append(stripped)

            # 最后一段
            if buf_lines:
                para = '\n'.join(buf_lines).strip()
                if len(para) >= MIN_PARAGRAPH_LENGTH:
                    paragraphs.append(para)

        finally:
            if not hasattr(file_path, 'read'):
                stream.close()

        logger.info(f"TXT文件解析完成，共 {len(paragraphs)} 段")
        return paragraphs, f"解析完成，共 {len(paragraphs)} 段，约 {total_chars} 字"
    
    except Exception as e:
        logger.error(f"TXT文件解析失败: {e}")
        return [], f"读取失败：{str(e)}"


def parse_pdf_file(file_path: str) -> Tuple[List[str], str]:
    """
    解析PDF文件
    
    Returns:
        (段落列表, 状态信息)
    """
    try:
        import fitz
    except ImportError:
        return [], "错误：缺少PyMuPDF依赖，请运行: pip install PyMuPDF"
    
    try:
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            return [], f"错误：文件过大 ({file_size / 1024 / 1024:.1f}MB > 50MB)"
        
        text = ""
        doc = fitz.open(file_path)
        
        for page_num, page in enumerate(doc):
            try:
                page_text = page.get_text("text")
                text += page_text + "\n"
            except Exception as e:
                logger.warning(f"PDF页面 {page_num} 解析失败: {e}")
        
        doc.close()
        
        paragraphs = _split_paragraphs(text)
        logger.info(f"PDF文件解析完成，共 {len(paragraphs)} 段")
        return paragraphs, f"解析完成，共 {len(paragraphs)} 段，约 {len(text)} 字"
    
    except Exception as e:
        logger.error(f"PDF文件解析失败: {e}")
        return [], f"读取失败：{str(e)}"


def parse_epub_file(file_path: str) -> Tuple[List[str], str]:
    """
    解析EPUB文件
    
    Returns:
        (段落列表, 状态信息)
    """
    try:
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except ImportError:
        return [], "错误：缺少ebooklib或beautifulsoup4依赖，请运行: pip install ebooklib beautifulsoup4"
    
    try:
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            return [], f"错误：文件过大 ({file_size / 1024 / 1024:.1f}MB > 50MB)"
        
        text = ""
        book = epub.read_epub(file_path)
        
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                try:
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    text += soup.get_text(separator="\n") + "\n"
                except Exception as e:
                    logger.warning(f"EPUB章节解析失败: {e}")
        
        paragraphs = _split_paragraphs(text)
        logger.info(f"EPUB文件解析完成，共 {len(paragraphs)} 段")
        return paragraphs, f"解析完成，共 {len(paragraphs)} 段，约 {len(text)} 字"
    
    except Exception as e:
        logger.error(f"EPUB文件解析失败: {e}")
        return [], f"读取失败：{str(e)}"


def parse_novel_file(file_path: str) -> Tuple[List[str], str]:
    """
    解析小说文件（自动识别格式）
    
    Args:
        file_path: 文件路径
    
    Returns:
        (段落列表, 状态信息)
    """
    if not file_path:
        return [], "无文件"
    
    # 处理Gradio上传的文件对象或文件流
    temp_path = None
    if hasattr(file_path, 'name') and isinstance(file_path.name, str) and os.path.exists(file_path.name):
        file_path = file_path.name
    elif hasattr(file_path, 'read'):
        # 将上传的流写入临时文件以便下游库处理（PDF/EPUB 需要文件路径）
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
            chunk = file_path.read(8192)
            while chunk:
                if isinstance(chunk, str):
                    tmp.write(chunk.encode('utf-8'))
                else:
                    tmp.write(chunk)
                chunk = file_path.read(8192)
            tmp.close()
            temp_path = tmp.name
            file_path = temp_path
        except Exception as e:
            logger.error(f"处理上传文件失败: {e}")
            return [], f"读取上传文件失败: {e}"
    
    if not os.path.exists(file_path):
        return [], f"文件不存在: {file_path}"
    
    file_type = get_file_type(file_path)
    
    if file_type == FileType.TXT:
        try:
            return parse_txt_file(file_path)
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    elif file_type == FileType.PDF:
        try:
            return parse_pdf_file(file_path)
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    elif file_type == FileType.EPUB:
        try:
            return parse_epub_file(file_path)
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    else:
        return [], "不支持的文件格式（支持 txt/pdf/epub）"


def _split_paragraphs(text: str, min_length: int = MIN_PARAGRAPH_LENGTH) -> List[str]:
    """
    将文本分割为段落
    
    Args:
        text: 原始文本
        min_length: 最小段落长度
    
    Returns:
        段落列表
    """
    # 按多个换行符分割
    raw_paragraphs = re.split(r'\n\s*\n+', text)
    
    # 清理和过滤
    paragraphs = []
    for para in raw_paragraphs:
        para = para.strip()
        # 移除章节标题等特殊标记
        para = re.sub(r'^(第\d+章|Chapter \d+|第 \d+ 章)[：:：]?\s*', '', para)
        para = re.sub(r'^\s*\*+\s*|\s*\*+\s*$', '', para)
        
        if len(para) >= min_length:
            paragraphs.append(para)
    
    return paragraphs


def estimate_word_count(text: str) -> int:
    """估计中文字数（粗略估计）"""
    chinese_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_count = len(re.findall(r'\b[a-zA-Z]+\b', text))
    # 中文按1字计算，英文按0.5字计算
    return chinese_count + int(english_count * 0.5)
