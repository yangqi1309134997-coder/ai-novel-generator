"""
认证相关 Pydantic Schema

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    """验证码校验请求"""
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=10, description="邮箱验证码")


class UserPublic(BaseModel):
    """公开用户信息（不含敏感字段）"""
    id: str
    email: str
    email_verified: bool = False
    display_name: str | None = None
    avatar_url: str | None = None
    role: str = "customer"
    subscription_tier: str = "free"
    subscription_expires_at: datetime | None = None
    balance: float = 0.0
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """认证成功响应（令牌 + 用户信息）"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str
