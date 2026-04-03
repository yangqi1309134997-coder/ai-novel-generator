"""
Public routes (no authentication required).

包含：
- GET / — 根路径信息
- GET /health — 健康检查

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["public"])


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str


@router.get("/", response_model=dict)
async def root():
    """根路径"""
    return {
        "message": "AI Novel Generator API",
        "version": "6.0.0",
        "docs": "/docs",
        "status": "running",
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version="6.0.0",
    )
