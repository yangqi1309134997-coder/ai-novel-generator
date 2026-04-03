"""
Prompt template management routes.

包含：
- GET  /api/prompts/templates — 列出模板
- GET  /api/prompts/template  — 获取模板
- POST /api/prompts/template  — 保存模板
- POST /api/prompts/reset     — 重置模板

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.routers.auth import require_permission
from backend.services.audit_service import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

project_root = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Pydantic 请求模型
# ---------------------------------------------------------------------------

class PromptTemplateRequest(BaseModel):
    category: str
    name: str
    content: str


class PromptTemplateLookupRequest(BaseModel):
    category: str
    name: str


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _get_prompt_manager():
    from src.core.prompts import PromptManager

    return PromptManager(project_root / "config")


# ---------------------------------------------------------------------------
# 路由端点
# ---------------------------------------------------------------------------

@router.get("/templates")
async def list_prompt_templates(category: Optional[str] = None, _user: dict = Depends(require_permission("prompts.view"))):
    try:
        prompt_manager = _get_prompt_manager()
        return {"success": True, "data": prompt_manager.list_templates(category, include_preset=True)}
    except Exception as e:
        logger.error(f"读取提示词列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/template")
async def get_prompt_template(category: str, name: str, _user: dict = Depends(require_permission("prompts.view"))):
    try:
        prompt_manager = _get_prompt_manager()
        content = prompt_manager.get_template(category, name, use_preset=True)
        if content is None:
            raise HTTPException(status_code=404, detail="提示词不存在")
        return {"success": True, "data": {"category": category, "name": name, "content": content}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取提示词失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/template")
async def save_prompt_template(payload: PromptTemplateRequest, user: dict = Depends(require_permission("prompts.edit"))):
    try:
        prompt_manager = _get_prompt_manager()
        prompt_manager.set_template(payload.category, payload.name, payload.content)
        audit_service.record(
            "admin.prompt.save",
            actor=user,
            status="success",
            target_type="prompt_template",
            target_label=f"{payload.category}/{payload.name}",
            message="提示词已保存",
        )
        return {"success": True, "message": "提示词已保存"}
    except Exception as e:
        logger.error(f"保存提示词失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_prompt_template(payload: PromptTemplateLookupRequest, user: dict = Depends(require_permission("prompts.edit"))):
    try:
        prompt_manager = _get_prompt_manager()
        success = prompt_manager.reset_to_preset(payload.category, payload.name)
        if not success:
            raise HTTPException(status_code=404, detail="未找到可重置的预设提示词")
        content = prompt_manager.get_template(payload.category, payload.name, use_preset=True)
        audit_service.record(
            "admin.prompt.reset",
            actor=user,
            status="success",
            target_type="prompt_template",
            target_label=f"{payload.category}/{payload.name}",
            message="提示词已重置为预设",
        )
        return {"success": True, "message": "提示词已重置为预设", "data": {"content": content or ""}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置提示词失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
