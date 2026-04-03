"""
支付与计费路由

包含：
- POST /api/billing/redeem           — 用户兑换卡密
- POST /api/billing/alipay/create    — 创建支付宝订单（返回二维码URL）
- POST /api/billing/alipay/callback  — 支付宝异步回调（无需认证）
- GET  /api/billing/orders           — 用户订单列表
- GET  /api/billing/invoices         — 用户发票列表
- POST /api/billing/orders           — 创建订单
- GET  /api/billing/plans            — 获取套餐列表（公开）
- GET  /api/billing/orders/{order_id}/checkout-session — 获取结算会话
- POST /api/billing/orders/{order_id}/submit-payment   — 提交付款备注
- POST /api/billing/orders/{order_id}/sandbox-pay      — 沙盒支付
- POST /api/billing/orders/{order_id}/approve          — 审批订单
- POST /api/billing/orders/{order_id}/cancel           — 取消订单
- POST /api/billing/webhooks/payment                   — 支付回调

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import verify_payment_webhook_signature
from backend.models.orm_models import Order, User
from backend.routers.auth import get_current_user, require_permission, _sync_auth_user_to_db
from backend.schemas.billing import CardCodeRedeem, OrderCreate, OrderResponse
from backend.services.audit_service import audit_service
from backend.services.auth_service import SUBSCRIPTION_TIERS, auth_service
from backend.services.billing_service import TIER_ORDER, billing_service
from backend.services.payment_gateway import payment_gateway_service
from backend.services.payment_service import payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Pydantic 请求模型
# ---------------------------------------------------------------------------

class BillingOrderCreateRequest(BaseModel):
    target_tier: str = Field(pattern="^(basic|pro)$")
    payment_channel: str = Field(pattern="^(sandbox_card|manual_transfer)$")
    note: str = Field(default="", max_length=200)


class BillingOrderPaymentRequest(BaseModel):
    payment_reference: str = Field(default="", max_length=100)


class BillingOrderDecisionRequest(BaseModel):
    note: str = Field(default="", max_length=200)


class BillingWebhookEventRequest(BaseModel):
    event_id: str = Field(min_length=6, max_length=80)
    event_type: str = Field(pattern="^payment\\.paid$")
    order_id: str = Field(min_length=8, max_length=64)
    status: str = Field(pattern="^paid$")
    amount: int = Field(ge=1)
    currency: str = Field(pattern="^CNY$")
    payment_reference: str = Field(default="", max_length=100)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _can_view_all_billing(user: Dict[str, Any]) -> bool:
    return auth_service.has_permission_for_role(user.get("role", "customer"), "billing.view_all")


def _ensure_billing_order_access(order: Optional[Dict[str, Any]], user: Dict[str, Any]) -> Dict[str, Any]:
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if _can_view_all_billing(user):
        return order
    if order.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="你无权访问该订单")
    return order


def _filter_invoices_for_user(invoices: List[Dict[str, Any]], user: Dict[str, Any]) -> List[Dict[str, Any]]:
    if _can_view_all_billing(user):
        return invoices
    return [invoice for invoice in invoices if invoice.get("user_id") == user["user_id"]]


def _timestamp_is_recent(timestamp: str, max_age_seconds: int = 300) -> bool:
    try:
        issued_at = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return False

    delta = abs((datetime.now(timezone.utc) - issued_at).total_seconds())
    return delta <= max_age_seconds


# ---------------------------------------------------------------------------
# 公开端点（无需认证）
# ---------------------------------------------------------------------------

@router.get("/plans")
async def get_plans(db: Session = Depends(get_db)):
    """获取套餐列表（公开，无需认证）。"""
    plans = payment_service.list_plans(db)
    return {"success": True, "data": plans}


# ---------------------------------------------------------------------------
# 支付宝异步回调（无需认证，由支付宝服务器调用）
# ---------------------------------------------------------------------------

@router.post("/alipay/callback")
async def alipay_callback(request: Request, db: Session = Depends(get_db)):
    """支付宝当面付异步回调。

    支付宝服务器在支付成功后调用此端点。验签通过后更新订单状态。
    注意：此端点不需要 JWT 认证，由支付宝签名保证安全性。
    """
    # 解析 form-data 参数
    form_data = await request.form()
    params = dict(form_data)

    logger.info("收到支付宝回调: trade_no=%s, out_trade_no=%s",
                params.get("trade_no"), params.get("out_trade_no"))

    # 1. 验签
    if not payment_service.verify_alipay_callback(params):
        logger.warning("支付宝回调验签失败: %s", params.get("out_trade_no"))
        return "fail"

    # 2. 查找订单
    out_trade_no = params.get("out_trade_no", "")
    order = db.query(Order).filter(Order.order_no == out_trade_no).first()
    if not order:
        logger.warning("支付宝回调：订单不存在: %s", out_trade_no)
        return "fail"

    # 3. 检查交易状态
    trade_status = params.get("trade_status", "")
    if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        logger.info("支付宝回调：交易状态=%s, 忽略", trade_status)
        return "success"

    # 4. 处理支付成功
    trade_no = params.get("trade_no", "")
    result = await payment_service.process_payment_success(
        order_id=order.id,
        db=db,
        payment_reference=trade_no,
    )

    if result.get("success"):
        logger.info("支付宝回调处理成功: order_no=%s", out_trade_no)
        return "success"
    else:
        logger.error("支付宝回调处理失败: %s", result.get("message"))
        return "fail"


# ---------------------------------------------------------------------------
# 需要认证的端点
# ---------------------------------------------------------------------------

@router.post("/redeem")
async def redeem_card_code(
    payload: CardCodeRedeem,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户兑换卡密。

    验证卡密有效性后自动升级用户会员等级。
    """
    _sync_auth_user_to_db(user["user_id"], db)
    result = await payment_service.redeem_card_code(
        user_id=user["user_id"],
        code=payload.code,
        db=db,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "兑换失败"),
        )
    return result


@router.post("/alipay/create")
async def create_alipay_order(
    payload: OrderCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建支付宝当面付订单，返回支付二维码 URL。"""
    if payload.payment_channel != "alipay":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此端点仅支持支付宝渠道",
        )

    _sync_auth_user_to_db(user["user_id"], db)
    try:
        result = await payment_service.create_alipay_order(
            user_id=user["user_id"],
            tier=payload.target_tier,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return result


@router.post("/orders")
async def create_order(
    payload: OrderCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建订单（通用端点，支持所有支付渠道）。

    对于支付宝渠道：调用支付宝预下单并返回二维码 URL。
    对于卡密渠道：建议使用 /redeem 端点直接兑换。
    对于沙盒/人工转账：创建订单后返回支付指引。
    """
    user_id = user["user_id"]
    _sync_auth_user_to_db(user_id, db)

    # 卡密渠道应走 /redeem 端点
    if payload.payment_channel == "card_code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="卡密兑换请使用 POST /api/billing/redeem",
        )

    # 支付宝渠道
    if payload.payment_channel == "alipay":
        try:
            return await payment_service.create_alipay_order(
                user_id=user_id,
                tier=payload.target_tier,
                db=db,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

    # 沙盒 / 人工转账（走旧版 BillingService 兼容逻辑）
    orm_user = db.query(User).filter(User.id == user_id).first()
    if not orm_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    success, message, order_data = billing_service.create_order(
        user_id=user_id,
        user_email=orm_user.email,
        current_tier=orm_user.subscription_tier,
        target_tier=payload.target_tier,
        payment_channel=payload.payment_channel,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    # 为沙盒 / 人工转账生成 checkout session
    checkout = payment_gateway_service.build_checkout_session(order_data)

    return {
        "success": True,
        "message": message,
        "data": {
            **order_data,
            "checkout": checkout,
        },
    }


@router.get("/orders")
async def list_orders(
    status_filter: str = Query(default="", alias="status", description="订单状态过滤"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的订单列表。"""
    orders = payment_service.get_user_orders(
        user_id=user["user_id"],
        db=db,
        status_filter=status_filter,
    )

    # 同时合并旧版 BillingService 的订单数据（兼容）
    legacy_orders = billing_service.list_orders(user_id=user["user_id"])
    legacy_order_nos = {o.get("order_no") for o in orders}

    merged = list(orders)
    for legacy in legacy_orders:
        if legacy.get("order_no") not in legacy_order_nos:
            merged.append(legacy)

    # 按创建时间降序排列
    merged.sort(key=lambda o: o.get("created_at", ""), reverse=True)

    return {"success": True, "data": merged}


@router.get("/invoices")
async def list_invoices(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的发票/收据列表。"""
    invoices = payment_service.get_user_invoices(
        user_id=user["user_id"],
        db=db,
    )

    # 合并旧版 BillingService 的发票数据（兼容）
    legacy_invoices = billing_service.list_invoices(user_id=user["user_id"])
    legacy_invoice_nos = {inv.get("invoice_no") for inv in invoices}

    merged = list(invoices)
    for legacy in legacy_invoices:
        if legacy.get("invoice_no") not in legacy_invoice_nos:
            merged.append(legacy)

    merged.sort(key=lambda o: o.get("created_at", ""), reverse=True)

    return {"success": True, "data": merged}


# ---------------------------------------------------------------------------
# 订单详情与操作
# ---------------------------------------------------------------------------

@router.get("/orders/{order_id}/checkout-session")
async def get_billing_checkout_session(order_id: str, user: dict = Depends(get_current_user)):
    order = _ensure_billing_order_access(billing_service.get_order(order_id), user)
    return {
        "success": True,
        "data": payment_gateway_service.build_checkout_session(order),
    }


@router.post("/orders/{order_id}/submit-payment")
async def submit_manual_payment(order_id: str, payload: BillingOrderPaymentRequest, user: dict = Depends(get_current_user)):
    order = _ensure_billing_order_access(billing_service.get_order(order_id), user)
    if not payload.payment_reference.strip():
        raise HTTPException(status_code=400, detail="请填写付款备注或转账流水号")
    if order.get("status") != "pending_payment":
        raise HTTPException(status_code=400, detail="当前订单状态不允许提交付款备注")

    success, message, updated = billing_service.submit_manual_payment(
        order_id,
        payment_reference=payload.payment_reference,
    )
    if not success or not updated:
        raise HTTPException(status_code=400, detail=message)

    audit_service.record(
        "billing.order.submit_payment",
        actor=user,
        status="success",
        target_type="billing_order",
        target_id=updated["id"],
        target_label=updated["order_no"],
        message=message,
        metadata={
            "payment_channel": updated["payment_channel"],
        },
    )
    return {"success": True, "message": message, "data": updated}


@router.post("/orders/{order_id}/sandbox-pay")
async def sandbox_pay_order(order_id: str, payload: BillingOrderPaymentRequest, user: dict = Depends(get_current_user)):
    order = _ensure_billing_order_access(billing_service.get_order(order_id), user)
    if order.get("payment_channel") != "sandbox_card":
        raise HTTPException(status_code=400, detail="当前订单不是沙盒支付订单")

    success, membership_message, upgraded = auth_service.update_user_membership(
        user_id=order["user_id"],
        subscription_tier=order["target_tier"],
        is_active=True,
    )
    if not success or not upgraded:
        raise HTTPException(status_code=400, detail=membership_message)

    payment_reference = payload.payment_reference.strip() or f"SANDBOX-{order['id'][:8].upper()}"
    success, message, paid_order, invoice = billing_service.mark_order_paid(
        order_id,
        payment_reference=payment_reference,
    )
    if not success or not paid_order or not invoice:
        raise HTTPException(status_code=400, detail=message)

    audit_service.record(
        "billing.order.sandbox_pay",
        actor=user,
        status="success",
        target_type="billing_order",
        target_id=paid_order["id"],
        target_label=paid_order["order_no"],
        message=message,
        metadata={
            "invoice_no": invoice["invoice_no"],
            "target_tier": paid_order["target_tier"],
            "amount": paid_order["amount"],
        },
    )
    return {
        "success": True,
        "message": message,
        "data": {
            "order": paid_order,
            "invoice": invoice,
            "membership": upgraded,
        },
    }


@router.post("/orders/{order_id}/approve")
async def approve_billing_order(
    order_id: str,
    payload: BillingOrderPaymentRequest,
    user: dict = Depends(require_permission("billing.manage")),
):
    order = _ensure_billing_order_access(billing_service.get_order(order_id), user)
    if order.get("payment_channel") != "manual_transfer":
        raise HTTPException(status_code=400, detail="只有人工转账订单需要后台确认")

    success, membership_message, upgraded = auth_service.update_user_membership(
        user_id=order["user_id"],
        subscription_tier=order["target_tier"],
        is_active=True,
    )
    if not success or not upgraded:
        raise HTTPException(status_code=400, detail=membership_message)

    payment_reference = payload.payment_reference.strip() or order.get("payment_reference", "")
    success, message, paid_order, invoice = billing_service.mark_order_paid(
        order_id,
        payment_reference=payment_reference,
    )
    if not success or not paid_order or not invoice:
        raise HTTPException(status_code=400, detail=message)

    audit_service.record(
        "billing.order.approve",
        actor=user,
        status="success",
        target_type="billing_order",
        target_id=paid_order["id"],
        target_label=paid_order["order_no"],
        message=message,
        metadata={
            "invoice_no": invoice["invoice_no"],
            "target_tier": paid_order["target_tier"],
            "amount": paid_order["amount"],
        },
    )
    return {
        "success": True,
        "message": message,
        "data": {
            "order": paid_order,
            "invoice": invoice,
            "membership": upgraded,
        },
    }


@router.post("/orders/{order_id}/cancel")
async def cancel_billing_order(order_id: str, payload: BillingOrderDecisionRequest, user: dict = Depends(get_current_user)):
    order = _ensure_billing_order_access(billing_service.get_order(order_id), user)
    if not _can_view_all_billing(user) and order.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="你无权取消该订单")

    success, message, cancelled = billing_service.cancel_order(order_id, reason=payload.note)
    if not success or not cancelled:
        raise HTTPException(status_code=400, detail=message)

    audit_service.record(
        "billing.order.cancel",
        actor=user,
        status="success",
        target_type="billing_order",
        target_id=cancelled["id"],
        target_label=cancelled["order_no"],
        message=message,
        metadata={
            "target_tier": cancelled["target_tier"],
            "status": cancelled["status"],
        },
    )
    return {"success": True, "message": message, "data": cancelled}


# ---------------------------------------------------------------------------
# 支付回调 Webhook
# ---------------------------------------------------------------------------

@router.post("/webhooks/payment")
async def payment_webhook(
    request: Request,
    x_payment_timestamp: str = Header(default=""),
    x_payment_signature: str = Header(default=""),
):
    raw_body = await request.body()
    if not _timestamp_is_recent(x_payment_timestamp):
        raise HTTPException(status_code=401, detail="支付回调时间戳无效或已过期")
    if not verify_payment_webhook_signature(raw_body, x_payment_timestamp, x_payment_signature):
        raise HTTPException(status_code=401, detail="支付回调签名无效")

    try:
        payload = BillingWebhookEventRequest.model_validate_json(raw_body)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"支付回调内容无效: {exc}") from exc

    order = billing_service.get_order(payload.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.get("amount") != payload.amount or order.get("currency") != payload.currency:
        raise HTTPException(status_code=400, detail="支付回调金额或币种与订单不一致")

    existing_event = billing_service.get_webhook_event(payload.event_id)
    if existing_event:
        existing_order = billing_service.get_order(payload.order_id)
        existing_invoice = billing_service.find_invoice_by_order_id(payload.order_id)
        return {
            "success": True,
            "message": "支付回调已处理，返回当前订单状态",
            "data": {
                "order": existing_order,
                "invoice": existing_invoice,
                "event": existing_event,
                "idempotent": True,
            },
        }

    success, membership_message, upgraded = auth_service.update_user_membership(
        user_id=order["user_id"],
        subscription_tier=order["target_tier"],
        is_active=True,
    )
    if not success or not upgraded:
        raise HTTPException(status_code=400, detail=membership_message)

    success, message, paid_order, invoice = billing_service.mark_order_paid(
        payload.order_id,
        payment_reference=payload.payment_reference,
    )
    if not success or not paid_order or not invoice:
        raise HTTPException(status_code=400, detail=message)

    billing_service.record_webhook_event(
        event_id=payload.event_id,
        order_id=payload.order_id,
        event_type=payload.event_type,
        status=payload.status,
        payload=payload.model_dump(),
    )

    audit_service.record(
        "billing.webhook.payment_paid",
        actor={"email": "payment-webhook", "role": "system"},
        status="success",
        target_type="billing_order",
        target_id=paid_order["id"],
        target_label=paid_order["order_no"],
        message="支付回调已确认到账",
        metadata={
            "event_id": payload.event_id,
            "invoice_no": invoice["invoice_no"],
            "payment_reference": paid_order.get("payment_reference", ""),
            "target_tier": paid_order["target_tier"],
            "amount": paid_order["amount"],
        },
    )
    return {
        "success": True,
        "message": "支付回调已处理",
        "data": {
            "order": paid_order,
            "invoice": invoice,
            "membership": upgraded,
            "event": payload.model_dump(),
            "idempotent": False,
        },
    }
