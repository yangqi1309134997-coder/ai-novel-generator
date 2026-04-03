"""
计费 / 订单相关 Pydantic Schema

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    """创建订单请求"""
    target_tier: str = Field(..., pattern=r"^(basic|pro)$", description="目标订阅层级")
    payment_channel: str = Field(
        default="alipay",
        pattern=r"^(alipay|card_code|manual_transfer)$",
        description="支付渠道",
    )


class OrderResponse(BaseModel):
    """订单响应"""
    id: str
    order_no: str
    user_id: str
    target_tier: str
    amount: float
    currency: str = "CNY"
    status: str
    payment_channel: str
    payment_reference: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    """发票 / 收据响应"""
    order_no: str
    target_tier: str
    amount: float
    currency: str
    status: str
    payment_channel: str
    created_at: datetime
    paid_at: datetime | None = None


class CardCodeRedeem(BaseModel):
    """卡密兑换请求"""
    code: str = Field(..., min_length=1, max_length=64, description="充值卡密")
