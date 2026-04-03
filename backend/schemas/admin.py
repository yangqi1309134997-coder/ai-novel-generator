"""
管理员相关 Pydantic Schema

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AdminConfigUpdate(BaseModel):
    """更新管理员配置请求"""
    config_key: str = Field(..., min_length=1, max_length=100)
    config_value: Any = Field(..., description="配置值（类型由 value_type 决定）")
    value_type: str = Field(
        default="string",
        pattern=r"^(string|json|number|boolean)$",
        description="值类型",
    )
    description: str | None = Field(default=None, max_length=500)


class AdminConfigResponse(BaseModel):
    """管理员配置响应"""
    id: str
    config_key: str
    config_value: Any
    value_type: str
    description: str | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class CardCodeGenerateRequest(BaseModel):
    """批量生成卡密请求"""
    tier: str = Field(..., pattern=r"^(basic|pro)$", description="卡密层级")
    days: int = Field(default=30, ge=1, description="有效天数")
    value_yuan: float = Field(..., gt=0, description="面值（元）")
    quantity: int = Field(default=1, ge=1, le=1000, description="生成数量")


class UserManagementRequest(BaseModel):
    """用户管理请求（修改角色 / 订阅 / 状态等）"""
    user_id: str = Field(..., description="目标用户 ID")
    action: str = Field(
        ...,
        pattern=r"^(set_role|set_tier|set_active|adjust_balance)$",
        description="操作类型",
    )
    value: str | None = Field(default=None, description="操作值")
    reason: str | None = Field(default=None, max_length=500, description="操作备注")
