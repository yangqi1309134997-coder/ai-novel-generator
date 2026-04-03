"""
Text tool routes (polish, continuation).

包含：
- POST /api/tools/polish                — 文本润色
- POST /api/tools/polish-suggestions    — 润色+建议
- POST /api/tools/continuation/analyze  — 续写分析
- POST /api/tools/continuation/generate — 续写生成

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.routers.auth import get_current_user
from backend.services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


# ---------------------------------------------------------------------------
# Pydantic 请求模型
# ---------------------------------------------------------------------------

class PolishRequest(BaseModel):
    text: str = Field(max_length=50000)
    polish_type: str = "全面润色"
    custom_req: str = ""


class ContinuationAnalysisRequest(BaseModel):
    content: str = Field(max_length=50000)
    current_chapters: int = Field(default=30, ge=1, le=10000)


class ContinuationGenerateRequest(BaseModel):
    content: str = Field(max_length=50000)
    planning: str = Field(max_length=10000)
    current_chapters: int = Field(default=30, ge=1, le=10000)
    target_words: int = Field(default=3000, ge=500, le=10000)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _require_generation_access(user: Dict[str, any]) -> None:
    allowed, reason = auth_service.can_generate(user["user_id"])
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)


def _get_runtime_api_client():
    from src.api import create_api_client

    from backend.routers.settings import _load_user_config
    config = _load_user_config()
    providers = config.get("providers", [])
    if not providers:
        raise HTTPException(status_code=400, detail="请先在设置中配置 API")
    return create_api_client(providers)


# ---------------------------------------------------------------------------
# 路由端点
# ---------------------------------------------------------------------------

@router.post("/polish")
async def polish_text(payload: PolishRequest, user: dict = Depends(get_current_user)):
    try:
        _require_generation_access(user)
        api_client = _get_runtime_api_client()
        prompt = f"""请润色下面这段中文文本。

要求：
1. 保持原意不变。
2. 改善流畅度和节奏。
3. 让表达更自然，减少 AI 腔。
4. 直接返回润色后的正文，不要解释。

润色类型：{payload.polish_type}
额外要求：{payload.custom_req or "无"}

原文：
{payload.text}
"""
        result = api_client.generate(
            [
                {"role": "system", "content": "你是一位专业中文小说编辑。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max(1200, int(len(payload.text) * 1.8)),
            temperature=0.7,
            use_cache=False,
        )
        message = "润色成功"
        if not result:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message, "data": {"content": result}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本润色失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/polish-suggestions")
async def polish_with_suggestions(payload: PolishRequest, user: dict = Depends(get_current_user)):
    try:
        _require_generation_access(user)
        api_client = _get_runtime_api_client()
        prompt = f"""请先润色下面的中文文本，再给出简明修改建议。

要求：
1. 第一部分输出"【润色后】"和润色后的正文。
2. 第二部分输出"【修改建议】"和 3 到 5 条建议。
3. 建议要具体，重点指出表达、节奏、人物或细节问题。

润色类型：{payload.polish_type}
额外要求：{payload.custom_req or "无"}

原文：
{payload.text}
"""
        raw = api_client.generate(
            [
                {"role": "system", "content": "你是一位专业中文小说编辑。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max(1800, int(len(payload.text) * 2.2)),
            temperature=0.7,
            use_cache=False,
        )
        message = "润色成功"
        if "【修改建议】" in raw:
            polished, suggestions = raw.split("【修改建议】", 1)
            polished = polished.replace("【润色后】", "").strip()
            suggestions = suggestions.strip()
        else:
            polished, suggestions = raw, ""
        if not polished and not suggestions:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message, "data": {"content": polished, "suggestions": suggestions}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"润色建议失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/continuation/analyze")
async def analyze_continuation(payload: ContinuationAnalysisRequest, user: dict = Depends(get_current_user)):
    try:
        _require_generation_access(user)
        from src.ui.features.rewrite import analyze_novel_for_continuation

        api_client = _get_runtime_api_client()
        analysis, planning, message = analyze_novel_for_continuation(api_client, payload.content, payload.current_chapters)
        if not analysis and not planning:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message, "data": {"analysis": analysis, "planning": planning}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"续写分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/continuation/generate")
async def generate_continuation(payload: ContinuationGenerateRequest, user: dict = Depends(get_current_user)):
    try:
        _require_generation_access(user)
        from src.ui.features.rewrite import generate_continuation_chapter

        api_client = _get_runtime_api_client()
        content, message = generate_continuation_chapter(
            api_client,
            payload.content,
            payload.planning,
            payload.current_chapters + 1,
            payload.target_words,
        )
        if not content:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message, "data": {"content": content}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"续写生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
