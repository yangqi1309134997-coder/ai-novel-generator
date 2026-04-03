"""
统一支付服务 — 支付宝当面付 + 卡密兑换

整合支付宝当面付（扫码付）和卡密兑换两种支付渠道，提供统一的订单创建、
支付成功处理、用户升级接口。数据库操作基于 SQLAlchemy Session。

支付宝当面付的 API 调用使用 TODO 占位，需要商户号和密钥才能对接真实网关。

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.models.orm_models import AdminConfig, CardCode, Order, User
from backend.services.auth_service import SUBSCRIPTION_TIERS, auth_service
from backend.services.billing_service import billing_service
from backend.services.payment_gateway import payment_gateway_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

_TIER_RANK = {"free": 0, "basic": 1, "pro": 2}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _generate_order_no() -> str:
    """生成唯一订单号: ORD-XXXXXXXXXX"""
    return f"ORD-{uuid.uuid4().hex[:10].upper()}"


def _get_tier_price(db: Session, tier: str) -> float:
    """从 AdminConfig 读取套餐价格，回退到 SUBSCRIPTION_TIERS 默认值。"""
    config_key = f"price_{tier}"
    config = db.query(AdminConfig).filter(AdminConfig.config_key == config_key).first()
    if config and config.config_value:
        try:
            return float(config.config_value)
        except (ValueError, TypeError):
            pass
    return float(SUBSCRIPTION_TIERS.get(tier, {}).get("price", 0))


# ---------------------------------------------------------------------------
# PaymentService
# ---------------------------------------------------------------------------

class PaymentService:
    """统一支付服务 — 支付宝当面付 + 卡密兑换"""

    # ---- 支付宝当面付 ----

    async def create_alipay_order(
        self,
        user_id: str,
        tier: str,
        db: Session,
    ) -> dict[str, Any]:
        """创建支付宝当面付订单。

        Args:
            user_id: 用户 ID。
            tier: 目标会员等级（basic / pro）。
            db: SQLAlchemy Session。

        Returns:
            包含订单信息和支付二维码 URL 的字典。
        """
        if tier not in ("basic", "pro"):
            raise ValueError(f"无效的会员等级: {tier!r}")

        # 1. 查询用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        current_rank = _TIER_RANK.get(user.subscription_tier, 0)
        target_rank = _TIER_RANK.get(tier, 0)
        if target_rank <= current_rank:
            raise ValueError("目标会员等级必须高于当前等级")

        # 2. 查询套餐价格
        amount = _get_tier_price(db, tier)

        # 3. 创建 Order 记录
        order_id = str(uuid.uuid4())
        order_no = _generate_order_no()
        order = Order(
            id=order_id,
            order_no=order_no,
            user_id=user_id,
            target_tier=tier,
            amount=amount,
            currency="CNY",
            status="pending_payment",
            payment_channel="alipay",
            payment_reference=None,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        # 4. 调用支付宝 API 创建预下单（TODO: 需要商户号和密钥）
        qr_code_url = await self._create_alipay_prepay(order_no, amount, tier)

        # 5. 同步到旧版 BillingService（兼容）
        billing_service.create_order(
            user_id=user_id,
            user_email=user.email,
            current_tier=user.subscription_tier,
            target_tier=tier,
            payment_channel="alipay",
        )

        logger.info(
            "支付宝订单已创建: order_no=%s, user=%s, tier=%s, amount=%.2f",
            order_no, user.email, tier, amount,
        )

        return {
            "success": True,
            "message": "支付宝订单已创建",
            "data": {
                "order_id": order.id,
                "order_no": order.order_no,
                "amount": order.amount,
                "currency": order.currency,
                "tier": tier,
                "qr_code_url": qr_code_url,
            },
        }

    async def _create_alipay_prepay(
        self,
        order_no: str,
        amount: float,
        tier: str,
    ) -> str:
        """调用支付宝当面付预下单接口。

        TODO: 需要配置以下参数后才能对接真实网关：
        - ALIPAY_APP_ID          应用ID
        - ALIPAY_PRIVATE_KEY     应用私钥（RSA2）
        - ALIPAY_PUBLIC_KEY      支付宝公钥
        - ALIPAY_NOTIFY_URL      异步回调地址

        当前返回模拟 URL 用于开发和测试。
        """
        # TODO: 对接真实支付宝当面付 API
        # from alipay import AliPay
        # alipay = AliPay(
        #     appid=settings.ALIPAY_APP_ID,
        #     app_private_key_string=settings.ALIPAY_PRIVATE_KEY,
        #     alipay_public_key_string=settings.ALIPAY_PUBLIC_KEY,
        #     sign_type="RSA2",
        # )
        # result = alipay.api_alipay_trade_precreate(
        #     out_trade_no=order_no,
        #     total_amount=str(amount),
        #     subject=f"AI Novel Generator - {SUBSCRIPTION_TIERS[tier]['name']}",
        # )
        # return result.get("qr_code", "")

        logger.warning("支付宝当面付 API 尚未对接，返回模拟二维码 URL")
        return f"mock://alipay/qr?order={order_no}&amount={amount}&tier={tier}"

    def verify_alipay_callback(self, params: dict[str, Any]) -> bool:
        """验证支付宝异步回调签名。

        Args:
            params: 支付宝回调的所有参数（包含 sign 和 sign_type）。

        Returns:
            签名是否有效。
        """
        # TODO: 对接真实支付宝 RSA2 签名验证
        # from alipay import AliPay
        # alipay = AliPay(...)
        # return alipay.verify(params, params.get("sign"))

        # 开发模式下仅做基本参数检查
        trade_status = params.get("trade_status")
        if trade_status == "TRADE_SUCCESS":
            logger.warning("支付宝回调验签（开发模式）：跳过签名验证")
            return True
        return False

    # ---- 卡密兑换 ----

    async def redeem_card_code(
        self,
        user_id: str,
        code: str,
        db: Session,
    ) -> dict[str, Any]:
        """卡密兑换。

        流程：
        1. 查找 CardCode 记录
        2. 检查状态（available?）、是否过期
        3. 更新 CardCode 状态为 redeemed
        4. 创建 Order 记录（payment_channel=card_code）
        5. 自动升级用户会员
        6. 返回兑换结果

        Args:
            user_id: 用户 ID。
            code: 卡密字符串。
            db: SQLAlchemy Session。

        Returns:
            兑换结果字典。
        """
        # 1. 查找卡密
        card = db.query(CardCode).filter(CardCode.code == code.strip()).first()
        if not card:
            return {"success": False, "message": "卡密不存在"}

        # 2. 检查状态
        if card.status != "available":
            status_labels = {
                "redeemed": "已被兑换",
                "expired": "已过期",
                "disabled": "已禁用",
            }
            return {
                "success": False,
                "message": f"卡密{status_labels.get(card.status, '不可用')}",
            }

        # 检查卡密是否过期
        if card.expires_at:
            expires_at = card.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if _utcnow() > expires_at:
                card.status = "expired"
                db.commit()
                return {"success": False, "message": "卡密已过期"}

        # 3. 查询用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "message": "用户不存在"}

        # 检查会员等级（卡密对应等级需 >= 当前等级才有意义，但允许叠加时间）
        current_rank = _TIER_RANK.get(user.subscription_tier, 0)
        card_rank = _TIER_RANK.get(card.tier, 0)
        if card_rank < current_rank:
            return {
                "success": False,
                "message": f"当前会员等级({user.subscription_tier})高于卡密等级({card.tier})，无法使用",
            }

        # 4. 更新 CardCode 状态
        now = _utcnow()
        card.status = "redeemed"
        card.redeemed_by_user_id = user_id
        card.redeemed_at = now

        # 5. 创建 Order 记录
        order_id = str(uuid.uuid4())
        order_no = _generate_order_no()
        order = Order(
            id=order_id,
            order_no=order_no,
            user_id=user_id,
            target_tier=card.tier,
            amount=card.value_yuan,
            currency="CNY",
            status="paid",  # 卡密兑换直接标记为已支付
            payment_channel="card_code",
            payment_reference=card.code,
            created_at=now,
            updated_at=now,
        )
        db.add(order)

        # 6. 升级用户会员
        new_expires = self._calculate_new_expiry(
            current_tier=user.subscription_tier,
            current_expires=user.subscription_expires_at,
            new_tier=card.tier,
            days=card.days,
        )
        user.subscription_tier = card.tier
        user.subscription_expires_at = new_expires
        user.updated_at = now

        db.commit()
        db.refresh(user)
        db.refresh(order)

        # 7. 同步到旧版 auth_service 内存用户库（兼容）
        auth_service.update_user_membership(
            user_id=user_id,
            subscription_tier=card.tier,
        )

        logger.info(
            "卡密兑换成功: user=%s, code=%s, tier=%s, days=%d",
            user.email, card.code, card.tier, card.days,
        )

        return {
            "success": True,
            "message": f"兑换成功，已升级为{SUBSCRIPTION_TIERS[card.tier]['name']} {card.days}天",
            "data": {
                "order_id": order.id,
                "order_no": order.order_no,
                "tier": card.tier,
                "tier_name": SUBSCRIPTION_TIERS[card.tier]["name"],
                "days": card.days,
                "expires_at": new_expires.isoformat() if new_expires else None,
            },
        }

    # ---- 支付成功统一处理 ----

    async def process_payment_success(
        self,
        order_id: str,
        db: Session,
        *,
        payment_reference: str = "",
    ) -> dict[str, Any]:
        """统一支付成功处理。

        流程：
        1. 更新 Order 状态为 paid
        2. 升级用户会员等级
        3. 发送通知邮件（TODO）
        4. 返回处理结果

        Args:
            order_id: 订单 ID。
            db: SQLAlchemy Session。
            payment_reference: 支付流水号（可选）。

        Returns:
            处理结果字典。
        """
        # 1. 查找订单
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"success": False, "message": "订单不存在"}

        if order.status == "paid":
            return {"success": True, "message": "订单已完成支付（幂等）"}

        if order.status not in ("pending_payment", "payment_submitted"):
            return {"success": False, "message": f"当前订单状态({order.status})不允许确认支付"}

        # 2. 更新订单状态
        now = _utcnow()
        order.status = "paid"
        if payment_reference:
            order.payment_reference = payment_reference
        order.updated_at = now

        # 3. 查找用户
        user = db.query(User).filter(User.id == order.user_id).first()
        if not user:
            db.commit()
            return {"success": False, "message": "用户不存在"}

        # 4. 升级会员等级（默认30天）
        current_rank = _TIER_RANK.get(user.subscription_tier, 0)
        target_rank = _TIER_RANK.get(order.target_tier, 0)

        if target_rank >= current_rank:
            new_expires = self._calculate_new_expiry(
                current_tier=user.subscription_tier,
                current_expires=user.subscription_expires_at,
                new_tier=order.target_tier,
                days=30,
            )
            user.subscription_tier = order.target_tier
            user.subscription_expires_at = new_expires
            user.updated_at = now

        db.commit()
        db.refresh(user)
        db.refresh(order)

        # 5. 同步到旧版服务（兼容）
        auth_service.update_user_membership(
            user_id=user.id,
            subscription_tier=user.subscription_tier,
        )

        # 同步到旧版 BillingService
        billing_service.mark_order_paid(
            order.id,
            payment_reference=payment_reference,
        )

        # 6. 发送通知邮件（TODO: 需要邮件模板）
        # await email_service.send_payment_success_notification(
        #     user.email,
        #     order_no=order.order_no,
        #     tier=order.target_tier,
        #     amount=order.amount,
        # )
        logger.info("支付成功通知邮件（TODO）: %s", user.email)

        logger.info(
            "支付成功处理完成: order_no=%s, user=%s, tier=%s",
            order.order_no, user.email, user.subscription_tier,
        )

        return {
            "success": True,
            "message": "支付成功，会员已升级",
            "data": {
                "order_id": order.id,
                "order_no": order.order_no,
                "status": order.status,
                "tier": user.subscription_tier,
                "tier_name": SUBSCRIPTION_TIERS.get(user.subscription_tier, {}).get("name", ""),
                "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            },
        }

    # ---- 查询接口 ----

    def get_user_orders(
        self,
        user_id: str,
        db: Session,
        *,
        status_filter: str = "",
    ) -> list[dict[str, Any]]:
        """获取用户订单列表。

        Args:
            user_id: 用户 ID。
            db: SQLAlchemy Session。
            status_filter: 可选状态过滤。

        Returns:
            订单字典列表。
        """
        query = db.query(Order).filter(Order.user_id == user_id)
        if status_filter:
            query = query.filter(Order.status == status_filter)
        orders = query.order_by(Order.created_at.desc()).all()
        return [order.to_dict() for order in orders]

    def get_user_invoices(
        self,
        user_id: str,
        db: Session,
    ) -> list[dict[str, Any]]:
        """获取用户发票/收据列表。

        基于已支付订单生成简易发票数据。

        Args:
            user_id: 用户 ID。
            db: SQLAlchemy Session。

        Returns:
            发票字典列表。
        """
        paid_orders = (
            db.query(Order)
            .filter(Order.user_id == user_id, Order.status == "paid")
            .order_by(Order.created_at.desc())
            .all()
        )

        invoices = []
        for order in paid_orders:
            invoices.append({
                "invoice_no": f"INV-{order.order_no[-10:]}",
                "order_no": order.order_no,
                "tier": order.target_tier,
                "amount": order.amount,
                "currency": order.currency,
                "status": order.status,
                "payment_channel": order.payment_channel,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "paid_at": order.updated_at.isoformat() if order.updated_at else None,
            })

        return invoices

    def list_plans(self, db: Session) -> list[dict[str, Any]]:
        """获取套餐列表（公开）。

        优先从 AdminConfig 读取价格，回退到 SUBSCRIPTION_TIERS 默认值。

        Args:
            db: SQLAlchemy Session。

        Returns:
            套餐字典列表。
        """
        plans = []
        for tier in ("basic", "pro"):
            config = SUBSCRIPTION_TIERS[tier]
            price = _get_tier_price(db, tier)
            plans.append({
                "tier": tier,
                "name": config["name"],
                "price": price,
                "currency": "CNY",
                "daily_quota": config["daily_quota"],
                "is_unlimited": config["daily_quota"] == -1,
                "description": f"{config['name']} - ¥{price}/月",
            })
        return plans

    # ---- 辅助方法 ----

    @staticmethod
    def _calculate_new_expiry(
        current_tier: str,
        current_expires: datetime | None,
        new_tier: str,
        days: int,
    ) -> datetime:
        """计算新的会员到期时间。

        规则：
        - 如果升级到相同等级且未过期，在当前到期时间基础上延长。
        - 否则从当前时间开始计算。
        """
        now = _utcnow()
        base = now

        # 如果当前等级与目标相同且未过期，则顺延
        if current_tier == new_tier and current_expires:
            expires = current_expires
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires > now:
                base = expires

        return base + timedelta(days=days)


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

payment_service = PaymentService()
