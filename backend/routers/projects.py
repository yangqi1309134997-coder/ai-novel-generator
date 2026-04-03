"""
Project management routes.

包含：
- GET    /api/projects                        — 列出项目
- POST   /api/projects                        — 创建项目
- GET    /api/projects/{project_id}            — 获取项目详情
- POST   /api/projects/{project_id}/chapters   — 追加章节
- PUT    /api/projects/{project_id}/content    — 替换内容
- DELETE /api/projects/{project_id}            — 删除项目
- GET    /api/projects/{project_id}/export     — 导出项目

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.routers.auth import get_current_user
from project_manager import ProjectManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])

# ---------------------------------------------------------------------------
# Pydantic 请求模型
# ---------------------------------------------------------------------------

class ProjectCreateRequest(BaseModel):
    """创建项目请求"""
    title: str
    genre: str
    character_setting: str = ""
    world_setting: str = ""
    plot_idea: str = ""
    chapter_count: int = 50


class ProjectAppendChapterRequest(BaseModel):
    title: str
    content: str
    desc: str = ""


class ProjectReplaceContentRequest(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _is_admin_user(user: Dict[str, Any]) -> bool:
    return bool(user.get("is_admin"))


def _filter_projects_for_user(projects: List[Dict[str, Any]], user: Dict[str, Any]) -> List[Dict[str, Any]]:
    if _is_admin_user(user):
        return projects
    return [project for project in projects if project.get("owner_user_id") == user["user_id"]]


def _ensure_project_access(project: Optional[Dict[str, Any]], user: Dict[str, Any]) -> Dict[str, Any]:
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if _is_admin_user(user):
        return project
    if project.get("owner_user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="你无权访问该项目")
    return project


def _split_project_text_into_chapters_safe(text: str, existing_chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse chaptered text with a clean regex that is not affected by legacy encoding issues."""
    import re

    normalized = (text or "").replace("\r\n", "\n").strip()
    if not normalized:
        return []

    chapter_keyword = "\u7b2c"
    chapter_suffix = "\u7ae0"
    pattern = re.compile(
        rf"(?m)^(?:#+\s*)?(?:{chapter_keyword}\s*(\d+)\s*{chapter_suffix}|Chapter\s*(\d+))(?:[\s:?\-?]+([^\n]+))?\s*$",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(normalized))

    if not matches:
        if len(existing_chapters) <= 1:
            original = existing_chapters[0] if existing_chapters else {}
            return [{
                "num": original.get("num", 1),
                "title": original.get("title", f"{chapter_keyword}1{chapter_suffix}"),
                "desc": original.get("desc", ""),
                "content": normalized,
                "word_count": len(normalized),
                "generated_at": datetime.now().isoformat(),
            }]
        return []

    by_num = {chapter.get("num"): chapter for chapter in existing_chapters}
    chapters: List[Dict[str, Any]] = []
    for index, match in enumerate(matches):
        chapter_num = int(match.group(1) or match.group(2))
        chapter_title = (match.group(3) or "").strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        content = normalized[start:end].strip()
        original = by_num.get(chapter_num, {})
        chapters.append({
            "num": chapter_num,
            "title": chapter_title or original.get("title", f"{chapter_keyword}{chapter_num}{chapter_suffix}"),
            "desc": original.get("desc", ""),
            "content": content,
            "word_count": len(content),
            "generated_at": original.get("generated_at", datetime.now().isoformat()),
        })

    return chapters


# ---------------------------------------------------------------------------
# 路由端点
# ---------------------------------------------------------------------------

@router.get("")
async def list_projects(user: dict = Depends(get_current_user)):
    """获取项目列表"""
    try:
        projects = ProjectManager.list_projects()
        return {"success": True, "data": _filter_projects_for_user(projects, user)}
    except Exception as e:
        logger.error(f"读取项目列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_project(project: ProjectCreateRequest, user: dict = Depends(get_current_user)):
    """创建项目"""
    try:
        project_id, message = ProjectManager.create_project(
            title=project.title,
            genre=project.genre,
            character_setting=project.character_setting,
            world_setting=project.world_setting,
            plot_idea=project.plot_idea,
            chapter_count=project.chapter_count,
            owner_user_id=user["user_id"],
            owner_email=user["email"],
        )

        if not project_id:
            raise HTTPException(status_code=400, detail=message)

        project_data = ProjectManager.get_project(project_id)
        return {"success": True, "message": message, "data": project_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建项目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    """读取单个项目"""
    project = _ensure_project_access(ProjectManager.get_project(project_id), user)
    return {"success": True, "data": project}


@router.post("/{project_id}/chapters")
async def append_project_chapter(project_id: str, payload: ProjectAppendChapterRequest, user: dict = Depends(get_current_user)):
    project = _ensure_project_access(ProjectManager.get_project(project_id), user)

    chapters = project.get("chapters", [])
    next_num = max([chapter.get("num", 0) for chapter in chapters], default=0) + 1
    chapter_data = {
        "num": next_num,
        "title": payload.title,
        "desc": payload.desc,
        "content": payload.content,
        "word_count": len(payload.content or ""),
        "generated_at": datetime.now().isoformat(),
    }
    chapters.append(chapter_data)
    project["chapters"] = chapters

    success, message = ProjectManager.save_project(project_id, project)
    if not success:
        raise HTTPException(status_code=500, detail=message)

    return {"success": True, "message": f"章节已保存到项目，第{next_num}章", "data": chapter_data}


@router.put("/{project_id}/content")
async def replace_project_content(project_id: str, payload: ProjectReplaceContentRequest, user: dict = Depends(get_current_user)):
    project = _ensure_project_access(ProjectManager.get_project(project_id), user)

    chapters = _split_project_text_into_chapters_safe(payload.text, project.get("chapters", []))
    if not chapters:
        raise HTTPException(status_code=400, detail="无法解析章节结构，请保留\"第N章 标题\"的章节标题格式")

    project["chapters"] = chapters
    success, message = ProjectManager.save_project(project_id, project)
    if not success:
        raise HTTPException(status_code=500, detail=message)

    return {"success": True, "message": f"项目正文已更新，共 {len(chapters)} 章", "data": {"chapter_count": len(chapters)}}


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    """删除项目"""
    _ensure_project_access(ProjectManager.get_project(project_id), user)
    success, message = ProjectManager.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"success": True, "message": message}


@router.get("/{project_id}/export")
async def export_project_file(project_id: str, format: str = "txt", user: dict = Depends(get_current_user)):
    _ensure_project_access(ProjectManager.get_project(project_id), user)
    filepath, message = ProjectManager.export_project(project_id, format)
    if not filepath:
        raise HTTPException(status_code=400, detail=message)

    path = Path(filepath)
    if not path.exists():
        raise HTTPException(status_code=404, detail="导出文件不存在")

    media_type_map = {
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "html": "text/html; charset=utf-8",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "json": "application/json",
    }
    return FileResponse(path, filename=path.name, media_type=media_type_map.get(format, "application/octet-stream"))
