"""
管理员 API 路由

所有端点均需 admin 权限。提供系统配置、用户管理、卡密管理、
订单管理、数据统计、审计日志等功能。

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.orm_models import AdminConfig, CardCode, GenerationJob, Order, User
from backend.routers.auth import require_permission
from backend.schemas.admin import AdminConfigResponse, AdminConfigUpdate, CardCodeGenerateRequest
from backend.services.audit_service import audit_service
from backend.services.email_service import email_service
from backend.utils.card_code_generator import generate_batch

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


# ---------------------------------------------------------------------------
# Pydantic 请求/响应模型
# ---------------------------------------------------------------------------

class BatchConfigUpdateItem(BaseModel):
    config_key: str = Field(..., min_length=1, max_length=100)
    config_value: Any = Field(..., description="配置值")
    value_type: str = Field(
        default="string",
        pattern=r"^(string|json|number|boolean)$",
    )
    description: str | None = Field(default=None, max_length=500)


class BatchConfigUpdateRequest(BaseModel):
    items: List[BatchConfigUpdateItem] = Field(..., min_length=1, max_length=100)


class SmtpConfigRequest(BaseModel):
    smtp_host: str = Field(..., min_length=1, max_length=255)
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_username: str = Field(..., min_length=1, max_length=255)
    smtp_password: str = Field(..., min_length=1, max_length=255)
    smtp_sender: str = Field(..., min_length=1, max_length=255)
    smtp_use_tls: bool = Field(default=True)


class SmtpTestRequest(BaseModel):
    to_email: str = Field(..., min_length=1, max_length=255)


class PaymentConfigRequest(BaseModel):
    alipay_app_id: str | None = Field(default=None, max_length=255)
    alipay_private_key: str | None = Field(default=None, max_length=2000)
    alipay_public_key: str | None = Field(default=None, max_length=2000)
    alipay_notify_url: str | None = Field(default=None, max_length=500)
    alipay_return_url: str | None = Field(default=None, max_length=500)
    payment_enabled: bool | None = Field(default=None)
    manual_transfer_enabled: bool | None = Field(default=None)
    card_code_enabled: bool | None = Field(default=None)


class MembershipPlanItem(BaseModel):
    tier: str = Field(..., pattern=r"^(basic|pro)$")
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., ge=0)
    daily_quota: int = Field(default=-1, ge=-1)
    features: List[str] = Field(default_factory=list)


class MembershipConfigRequest(BaseModel):
    plans: List[MembershipPlanItem] = Field(..., min_length=1, max_length=10)


class UserBanRequest(BaseModel):
    is_active: bool = Field(..., description="True=启用, False=禁用")
    reason: str | None = Field(default=None, max_length=500)


class BalanceAdjustRequest(BaseModel):
    amount: float = Field(..., description="调整金额（正数增加，负数扣除）")
    reason: str = Field(..., min_length=1, max_length=500)


class StyleConfigRequest(BaseModel):
    styles: List[Dict[str, Any]] = Field(..., min_length=1)


class GenerationConfigRequest(BaseModel):
    config: Dict[str, Any] = Field(...)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _mask_sensitive(value: Optional[str], visible_chars: int = 4) -> str:
    """对敏感字段做脱敏处理，仅保留最后几个可见字符。"""
    if not value:
        return ""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def _get_config_value(db: Session, key: str) -> Optional[AdminConfig]:
    """根据 key 获取 AdminConfig 行。"""
    return (
        db.query(AdminConfig)
        .filter(AdminConfig.config_key == key)
        .first()
    )


def _upsert_config(
    db: Session,
    key: str,
    value: Any,
    value_type: str = "string",
    description: str | None = None,
) -> AdminConfig:
    """创建或更新 AdminConfig 行。"""
    raw_value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    row = _get_config_value(db, key)
    if row:
        row.config_value = raw_value
        row.value_type = value_type
        if description is not None:
            row.description = description
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = AdminConfig(
            id=str(uuid.uuid4()),
            config_key=key,
            config_value=raw_value,
            value_type=value_type,
            description=description,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(row)
    db.flush()
    return row


# ===========================================================================
# 系统配置
# ===========================================================================

@router.get("/api/admin/config")
async def list_configs(
    user: dict = Depends(require_permission("admin.config.view")),
    db: Session = Depends(get_db),
):
    """获取所有配置项（key-value 列表）。"""
    rows = db.query(AdminConfig).order_by(AdminConfig.config_key).all()
    return {"success": True, "data": [row.to_dict() for row in rows]}


@router.put("/api/admin/config")
async def batch_update_configs(
    payload: BatchConfigUpdateRequest,
    user: dict = Depends(require_permission("admin.config.edit")),
    db: Session = Depends(get_db),
):
    """批量更新配置项。"""
    updated = []
    for item in payload.items:
        row = _upsert_config(
            db,
            key=item.config_key,
            value=item.config_value,
            value_type=item.value_type,
            description=item.description,
        )
        updated.append(row.to_dict())

    db.commit()

    audit_service.record(
        "admin.config.batch_update",
        actor=user,
        status="success",
        target_type="admin_config",
        message=f"批量更新 {len(updated)} 项配置",
        metadata={"keys": [item.config_key for item in payload.items]},
    )

    return {"success": True, "data": updated}


@router.get("/api/admin/config/{key}")
async def get_config(
    key: str,
    user: dict = Depends(require_permission("admin.config.view")),
    db: Session = Depends(get_db),
):
    """获取单个配置项。"""
    row = _get_config_value(db, key)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"配置项 {key!r} 不存在")
    return {"success": True, "data": row.to_dict()}


@router.put("/api/admin/config/{key}")
async def update_config(
    key: str,
    payload: AdminConfigUpdate,
    user: dict = Depends(require_permission("admin.config.edit")),
    db: Session = Depends(get_db),
):
    """更新单个配置项。"""
    row = _upsert_config(
        db,
        key=payload.config_key,
        value=payload.config_value,
        value_type=payload.value_type,
        description=payload.description,
    )
    db.commit()

    audit_service.record(
        "admin.config.update",
        actor=user,
        status="success",
        target_type="admin_config",
        target_id=key,
        message=f"更新配置项 {key}",
        metadata={"value_type": payload.value_type},
    )

    return {"success": True, "data": row.to_dict()}


# ===========================================================================
# SMTP 邮件配置
# ===========================================================================

_SMTP_KEYS = [
    "smtp_host",
    "smtp_port",
    "smtp_username",
    "smtp_password",
    "smtp_sender",
    "smtp_use_tls",
]


@router.get("/api/admin/config/smtp")
async def get_smtp_config(
    user: dict = Depends(require_permission("admin.config.view")),
    db: Session = Depends(get_db),
):
    """获取 SMTP 配置（密码脱敏）。"""
    rows = (
        db.query(AdminConfig)
        .filter(AdminConfig.config_key.in_(_SMTP_KEYS))
        .all()
    )
    config_map = {row.config_key: row.to_dict() for row in rows}

    # 密码脱敏
    pw_entry = config_map.get("smtp_password")
    masked = _mask_sensitive(
        pw_entry.get("config_value") if pw_entry else None
    )

    return {
        "success": True,
        "data": {
            "smtp_host": config_map["smtp_host"]["config_value"] if "smtp_host" in config_map else "",
            "smtp_port": config_map["smtp_port"]["config_value"] if "smtp_port" in config_map else 465,
            "smtp_username": config_map["smtp_username"]["config_value"] if "smtp_username" in config_map else "",
            "smtp_password": masked,
            "smtp_sender": config_map["smtp_sender"]["config_value"] if "smtp_sender" in config_map else "",
            "smtp_use_tls": config_map["smtp_use_tls"]["config_value"] if "smtp_use_tls" in config_map else True,
        },
    }


@router.put("/api/admin/config/smtp")
async def update_smtp_config(
    payload: SmtpConfigRequest,
    user: dict = Depends(require_permission("admin.config.edit")),
    db: Session = Depends(get_db),
):
    """更新 SMTP 配置。"""
    pairs = {
        "smtp_host": (payload.smtp_host, "string", "SMTP 服务器地址"),
        "smtp_port": (str(payload.smtp_port), "string", "SMTP 端口"),
        "smtp_username": (payload.smtp_username, "string", "SMTP 用户名"),
        "smtp_password": (payload.smtp_password, "string", "SMTP 密码"),
        "smtp_sender": (payload.smtp_sender, "string", "发件人地址"),
        "smtp_use_tls": (str(payload.smtp_use_tls).lower(), "boolean", "是否使用 TLS"),
    }
    for key, (val, vtype, desc) in pairs.items():
        _upsert_config(db, key=key, value=val, value_type=vtype, description=desc)

    db.commit()

    # 通知 email_service 重载配置
    email_service.reload_config()

    audit_service.record(
        "admin.config.smtp_update",
        actor=user,
        status="success",
        target_type="admin_config",
        target_label="smtp",
        message="SMTP 配置已更新",
        metadata={"smtp_host": payload.smtp_host, "smtp_port": payload.smtp_port},
    )

    return {"success": True, "message": "SMTP 配置已更新"}


@router.post("/api/admin/config/smtp/test")
async def test_smtp_connection(
    payload: SmtpTestRequest,
    user: dict = Depends(require_permission("admin.config.edit")),
    db: Session = Depends(get_db),
):
    """测试 SMTP 连接，发送测试邮件。"""
    html_body = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif; padding:24px; color:#333;">
  <h2 style="color:#667eea;">SMTP 测试邮件</h2>
  <p>这是一封由管理员发送的 SMTP 连接测试邮件。</p>
  <p>如果您收到此邮件，说明 SMTP 配置正确。</p>
  <hr style="border:none;border-top:1px solid #eee;margin:16px 0;">
  <p style="color:#999;font-size:12px;">
    发送时间: {datetime.now(timezone.utc).isoformat()}<br>
    操作者: {user.get('email', 'unknown')}
  </p>
</body>
</html>
"""
    success = await email_service._send(
        payload.to_email,
        "【AI Novel Generator】SMTP 测试邮件",
        html_body,
    )

    audit_service.record(
        "admin.config.smtp_test",
        actor=user,
        status="success" if success else "failed",
        target_type="admin_config",
        target_label="smtp",
        message="SMTP 测试邮件" + ("发送成功" if success else "发送失败"),
        metadata={"to_email": payload.to_email},
    )

    if not success:
        raise HTTPException(status_code=500, detail="SMTP 测试邮件发送失败，请检查配置")

    return {"success": True, "message": f"测试邮件已发送至 {payload.to_email}"}


# ===========================================================================
# 支付配置
# ===========================================================================

_PAYMENT_KEYS_SENSITIVE = {
    "alipay_private_key",
    "alipay_public_key",
}


@router.get("/api/admin/config/payment")
async def get_payment_config(
    user: dict = Depends(require_permission("admin.config.view")),
    db: Session = Depends(get_db),
):
    """获取支付配置（密钥脱敏）。"""
    payment_prefix_keys = [
        "alipay_app_id",
        "alipay_private_key",
        "alipay_public_key",
        "alipay_notify_url",
        "alipay_return_url",
        "payment_enabled",
        "manual_transfer_enabled",
        "card_code_enabled",
    ]
    rows = (
        db.query(AdminConfig)
        .filter(AdminConfig.config_key.in_(payment_prefix_keys))
        .all()
    )
    config_map = {row.config_key: row.to_dict() for row in rows}

    result = {}
    for key in payment_prefix_keys:
        entry = config_map.get(key)
        if entry:
            val = entry["config_value"]
            if key in _PAYMENT_KEYS_SENSITIVE:
                val = _mask_sensitive(str(val))
            result[key] = val
        else:
            result[key] = None

    return {"success": True, "data": result}


@router.put("/api/admin/config/payment")
async def update_payment_config(
    payload: PaymentConfigRequest,
    user: dict = Depends(require_permission("admin.config.edit")),
    db: Session = Depends(get_db),
):
    """更新支付配置。"""
    updates = {
        "alipay_app_id": (payload.alipay_app_id, "string", "支付宝 App ID"),
        "alipay_private_key": (payload.alipay_private_key, "string", "支付宝应用私钥"),
        "alipay_public_key": (payload.alipay_public_key, "string", "支付宝公钥"),
        "alipay_notify_url": (payload.alipay_notify_url, "string", "支付宝异步通知地址"),
        "alipay_return_url": (payload.alipay_return_url, "string", "支付宝同步跳转地址"),
        "payment_enabled": (
            str(payload.payment_enabled).lower() if payload.payment_enabled is not None else None,
            "boolean",
            "是否启用在线支付",
        ),
        "manual_transfer_enabled": (
            str(payload.manual_transfer_enabled).lower() if payload.manual_transfer_enabled is not None else None,
            "boolean",
            "是否启用手动转账",
        ),
        "card_code_enabled": (
            str(payload.card_code_enabled).lower() if payload.card_code_enabled is not None else None,
            "boolean",
            "是否启用卡密兑换",
        ),
    }

    for key, (val, vtype, desc) in updates.items():
        if val is not None:
            _upsert_config(db, key=key, value=val, value_type=vtype, description=desc)

    db.commit()

    audit_service.record(
        "admin.config.payment_update",
        actor=user,
        status="success",
        target_type="admin_config",
        target_label="payment",
        message="支付配置已更新",
    )

    return {"success": True, "message": "支付配置已更新"}


# ===========================================================================
# 会员配置
# ===========================================================================

@router.get("/api/admin/config/membership")
async def get_membership_config(
    user: dict = Depends(require_permission("admin.config.view")),
    db: Session = Depends(get_db),
):
    """获取会员套餐配置。"""
    row = _get_config_value(db, "membership_plans")
    if row:
        return {"success": True, "data": row.to_dict()}
    # 默认配置
    default_plans = [
        {"tier": "basic", "name": "基础会员", "price": 29, "daily_quota": 50, "features": ["每天50次生成"]},
        {"tier": "pro", "name": "专业会员", "price": 99, "daily_quota": -1, "features": ["无限次生成", "优先处理"]},
    ]
    return {"success": True, "data": {"config_key": "membership_plans", "config_value": default_plans}}


@router.put("/api/admin/config/membership")
async def update_membership_config(
    payload: MembershipConfigRequest,
    user: dict = Depends(require_permission("admin.config.edit")),
    db: Session = Depends(get_db),
):
    """更新会员套餐配置。"""
    plans_data = [plan.model_dump() for plan in payload.plans]
    _upsert_config(
        db,
        key="membership_plans",
        value=plans_data,
        value_type="json",
        description="会员套餐配置",
    )
    db.commit()

    audit_service.record(
        "admin.config.membership_update",
        actor=user,
        status="success",
        target_type="admin_config",
        target_label="membership_plans",
        message="会员套餐配置已更新",
        metadata={"tiers": [p.tier for p in payload.plans]},
    )

    return {"success": True, "message": "会员套餐配置已更新"}


# ===========================================================================
# 用户管理
# ===========================================================================

@router.get("/api/admin/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=""),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern=r"^(asc|desc)$"),
    user: dict = Depends(require_permission("admin.users.view")),
    db: Session = Depends(get_db),
):
    """用户列表（分页、搜索、排序）。"""
    query = db.query(User)

    # 搜索
    if search.strip():
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (User.email.ilike(search_term))
            | (User.display_name.ilike(search_term))
        )

    # 排序
    sort_col = getattr(User, sort_by, None)
    if sort_col is None:
        sort_col = User.created_at
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": {
            "items": [u.to_dict() for u in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        },
    }


@router.get("/api/admin/users/{user_id}")
async def get_user_detail(
    user_id: str,
    user: dict = Depends(require_permission("admin.users.view")),
    db: Session = Depends(get_db),
):
    """用户详情。"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return {"success": True, "data": target.to_dict()}


@router.put("/api/admin/users/{user_id}/ban")
async def toggle_user_ban(
    user_id: str,
    payload: UserBanRequest,
    user: dict = Depends(require_permission("admin.users.ban")),
    db: Session = Depends(get_db),
):
    """禁用/启用用户。"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if target.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能禁用管理员账号")

    target.is_active = payload.is_active
    target.updated_at = datetime.now(timezone.utc)
    db.commit()

    action_text = "启用" if payload.is_active else "禁用"
    audit_service.record(
        "admin.user.ban",
        actor=user,
        status="success",
        target_type="user",
        target_id=user_id,
        target_label=target.email,
        message=f"{action_text}用户",
        metadata={"is_active": payload.is_active, "reason": payload.reason},
    )

    return {"success": True, "message": f"用户已{action_text}", "data": target.to_dict()}


@router.put("/api/admin/users/{user_id}/adjust-balance")
async def adjust_user_balance(
    user_id: str,
    payload: BalanceAdjustRequest,
    user: dict = Depends(require_permission("admin.users.balance")),
    db: Session = Depends(get_db),
):
    """调整用户余额。"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    old_balance = target.balance
    new_balance = round(old_balance + payload.amount, 2)
    if new_balance < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="余额不足，无法扣减")

    target.balance = new_balance
    target.updated_at = datetime.now(timezone.utc)
    db.commit()

    audit_service.record(
        "admin.user.adjust_balance",
        actor=user,
        status="success",
        target_type="user",
        target_id=user_id,
        target_label=target.email,
        message=f"调整用户余额：{old_balance} -> {new_balance}",
        metadata={
            "old_balance": old_balance,
            "adjustment": payload.amount,
            "new_balance": new_balance,
            "reason": payload.reason,
        },
    )

    return {
        "success": True,
        "message": "余额已调整",
        "data": {
            "user_id": user_id,
            "old_balance": old_balance,
            "new_balance": new_balance,
            "adjustment": payload.amount,
        },
    }


# ===========================================================================
# 卡密管理
# ===========================================================================

@router.post("/api/admin/card-codes/generate")
async def generate_card_codes(
    payload: CardCodeGenerateRequest,
    user: dict = Depends(require_permission("admin.card_codes.generate")),
    db: Session = Depends(get_db),
):
    """批量生成卡密。"""
    try:
        raw_cards = generate_batch(
            payload.quantity,
            tier=payload.tier,
            days=payload.days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    created = []
    for card_data in raw_cards:
        card = CardCode(
            id=str(uuid.uuid4()),
            code=card_data["code"],
            tier=card_data["tier"],
            days=card_data["days"],
            value_yuan=payload.value_yuan,
            status="available",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.fromisoformat(card_data["expires_at"]),
        )
        db.add(card)
        created.append(card)

    db.commit()

    # refresh to get all fields
    for card in created:
        db.refresh(card)

    audit_service.record(
        "admin.card_codes.generate",
        actor=user,
        status="success",
        target_type="card_code",
        message=f"批量生成 {len(created)} 张卡密",
        metadata={
            "tier": payload.tier,
            "days": payload.days,
            "quantity": payload.quantity,
            "value_yuan": payload.value_yuan,
        },
    )

    return {
        "success": True,
        "data": {
            "generated": len(created),
            "codes": [c.to_dict() for c in created],
        },
    }


@router.get("/api/admin/card-codes")
async def list_card_codes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str = Query(default="", alias="status"),
    tier: str = Query(default=""),
    user: dict = Depends(require_permission("admin.card_codes.view")),
    db: Session = Depends(get_db),
):
    """卡密列表（分页、筛选）。"""
    query = db.query(CardCode)

    if status_filter.strip():
        query = query.filter(CardCode.status == status_filter.strip())
    if tier.strip():
        query = query.filter(CardCode.tier == tier.strip())

    query = query.order_by(CardCode.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": {
            "items": [c.to_dict() for c in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        },
    }


@router.put("/api/admin/card-codes/{code_id}/disable")
async def disable_card_code(
    code_id: str,
    user: dict = Depends(require_permission("admin.card_codes.disable")),
    db: Session = Depends(get_db),
):
    """作废卡密。"""
    card = db.query(CardCode).filter(CardCode.id == code_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="卡密不存在")

    if card.status == "redeemed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已兑换的卡密不能作废")

    card.status = "disabled"
    db.commit()

    audit_service.record(
        "admin.card_codes.disable",
        actor=user,
        status="success",
        target_type="card_code",
        target_id=code_id,
        target_label=card.code,
        message=f"作废卡密 {card.code}",
    )

    return {"success": True, "message": "卡密已作废", "data": card.to_dict()}


# ===========================================================================
# 订单管理
# ===========================================================================

@router.get("/api/admin/orders")
async def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str = Query(default="", alias="status"),
    payment_channel: str = Query(default=""),
    user: dict = Depends(require_permission("admin.orders.view")),
    db: Session = Depends(get_db),
):
    """订单列表（分页、筛选）。"""
    query = db.query(Order)

    if status_filter.strip():
        query = query.filter(Order.status == status_filter.strip())
    if payment_channel.strip():
        query = query.filter(Order.payment_channel == payment_channel.strip())

    query = query.order_by(Order.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": {
            "items": [o.to_dict() for o in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        },
    }


# ===========================================================================
# 数据统计（仪表盘）
# ===========================================================================

@router.get("/api/admin/stats")
async def get_dashboard_stats(
    user: dict = Depends(require_permission("admin.stats.view")),
    db: Session = Depends(get_db),
):
    """仪表盘数据统计。"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 总用户数
    total_users = db.query(func.count(User.id)).scalar() or 0

    # 活跃用户（最近7天有更新）
    seven_days_ago = now - timedelta(days=7)
    active_users = (
        db.query(func.count(User.id))
        .filter(User.updated_at >= seven_days_ago)
        .scalar()
        or 0
    )

    # 今日新注册
    new_users_today = (
        db.query(func.count(User.id))
        .filter(User.created_at >= today_start)
        .scalar()
        or 0
    )

    # 今日收入（已支付订单金额总和）
    today_revenue = (
        db.query(func.coalesce(func.sum(Order.amount), 0))
        .filter(Order.status == "paid", Order.created_at >= today_start)
        .scalar()
        or 0
    )

    # 总收入
    total_revenue = (
        db.query(func.coalesce(func.sum(Order.amount), 0))
        .filter(Order.status == "paid")
        .scalar()
        or 0
    )

    # 进行中任务
    active_jobs = (
        db.query(func.count(GenerationJob.id))
        .filter(GenerationJob.status.in_(["queued", "running"]))
        .scalar()
        or 0
    )

    # 今日已完成任务
    completed_jobs_today = (
        db.query(func.count(GenerationJob.id))
        .filter(
            GenerationJob.status == "completed",
            GenerationJob.updated_at >= today_start,
        )
        .scalar()
        or 0
    )

    # 卡密统计
    available_cards = (
        db.query(func.count(CardCode.id))
        .filter(CardCode.status == "available")
        .scalar()
        or 0
    )
    redeemed_cards = (
        db.query(func.count(CardCode.id))
        .filter(CardCode.status == "redeemed")
        .scalar()
        or 0
    )

    # 订单统计
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    pending_orders = (
        db.query(func.count(Order.id))
        .filter(Order.status == "pending_payment")
        .scalar()
        or 0
    )

    return {
        "success": True,
        "data": {
            "users": {
                "total": total_users,
                "active_7d": active_users,
                "new_today": new_users_today,
            },
            "revenue": {
                "today": round(float(today_revenue), 2),
                "total": round(float(total_revenue), 2),
            },
            "jobs": {
                "active": active_jobs,
                "completed_today": completed_jobs_today,
            },
            "card_codes": {
                "available": available_cards,
                "redeemed": redeemed_cards,
            },
            "orders": {
                "total": total_orders,
                "pending": pending_orders,
            },
        },
    }


# ===========================================================================
# 系统日志（审计日志）
# ===========================================================================

@router.get("/api/admin/audit-logs")
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action_prefix: str = Query(default=""),
    actor_role: str = Query(default=""),
    user: dict = Depends(require_permission("admin.audit.view")),
):
    """审计日志（分页）。"""
    # audit_service.list_logs 返回倒序结果，我们用它获取全部再分页
    safe_limit = 5000  # 取足够多的日志用于分页
    all_logs = audit_service.list_logs(
        limit=safe_limit,
        actor_role=actor_role.strip(),
        action_prefix=action_prefix.strip(),
    )

    total = len(all_logs)
    start = (page - 1) * page_size
    end = start + page_size
    items = all_logs[start:end]

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        },
    }


# ===========================================================================
# 内容配置 — 风格模板
# ===========================================================================

@router.get("/api/admin/config/styles")
async def get_style_config(
    user: dict = Depends(require_permission("admin.config.view")),
    db: Session = Depends(get_db),
):
    """获取风格模板配置。"""
    row = _get_config_value(db, "style_templates")
    if row:
        return {"success": True, "data": row.to_dict()}
    return {"success": True, "data": {"config_key": "style_templates", "config_value": []}}


@router.put("/api/admin/config/styles")
async def update_style_config(
    payload: StyleConfigRequest,
    user: dict = Depends(require_permission("admin.config.edit")),
    db: Session = Depends(get_db),
):
    """更新风格模板配置。"""
    _upsert_config(
        db,
        key="style_templates",
        value=payload.styles,
        value_type="json",
        description="风格模板配置",
    )
    db.commit()

    audit_service.record(
        "admin.config.styles_update",
        actor=user,
        status="success",
        target_type="admin_config",
        target_label="style_templates",
        message=f"更新风格模板配置（{len(payload.styles)} 项）",
        metadata={"count": len(payload.styles)},
    )

    return {"success": True, "message": "风格模板配置已更新"}


# ===========================================================================
# 生成默认参数配置
# ===========================================================================

@router.get("/api/admin/config/generation")
async def get_generation_config(
    user: dict = Depends(require_permission("admin.config.view")),
    db: Session = Depends(get_db),
):
    """获取生成参数配置。"""
    row = _get_config_value(db, "generation_defaults")
    if row:
        return {"success": True, "data": row.to_dict()}
    return {"success": True, "data": {"config_key": "generation_defaults", "config_value": {}}}


@router.put("/api/admin/config/generation")
async def update_generation_config(
    payload: GenerationConfigRequest,
    user: dict = Depends(require_permission("admin.config.edit")),
    db: Session = Depends(get_db),
):
    """更新生成参数配置。"""
    _upsert_config(
        db,
        key="generation_defaults",
        value=payload.config,
        value_type="json",
        description="生成默认参数配置",
    )
    db.commit()

    audit_service.record(
        "admin.config.generation_update",
        actor=user,
        status="success",
        target_type="admin_config",
        target_label="generation_defaults",
        message="更新生成默认参数配置",
    )

    return {"success": True, "message": "生成参数配置已更新"}
