"""
生成任务相关 Pydantic Schema

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FullGenerationRequest(BaseModel):
    """完整小说生成请求"""
    title: str = Field(..., min_length=1, max_length=255, description="小说标题")
    genre: str | None = Field(default=None, max_length=100, description="题材/风格")
    character_setting: str | None = Field(default=None, description="角色设定")
    world_setting: str | None = Field(default=None, description="世界观设定")
    plot_idea: str | None = Field(default=None, description="剧情构思")
    chapter_count: int = Field(default=10, ge=1, le=1000, description="章节数量")
    export_format: str | None = Field(
        default="txt",
        pattern=r"^(txt|markdown|docx|pdf)$",
        description="导出格式",
    )
    # 允许携带额外的生成参数
    extra_params: dict[str, Any] | None = Field(default=None, description="额外参数")


class GenerationJobResponse(BaseModel):
    """生成任务响应"""
    id: str
    status: str
    title: str | None = None
    project_id: str | None = None
    progress: int = 0
    current_step: str | None = None
    message: str | None = None
    error: str | None = None
    export_format: str | None = None
    owner_user_id: str
    request_payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
