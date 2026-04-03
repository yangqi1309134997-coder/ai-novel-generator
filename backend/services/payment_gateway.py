"""
Commercial payment gateway adapter layer.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.core.settings import (
    COMMERCIAL_BACKEND_URL,
    COMMERCIAL_MANUAL_TRANSFER_ACCOUNT_NAME,
    COMMERCIAL_MANUAL_TRANSFER_ACCOUNT_NO,
    COMMERCIAL_MANUAL_TRANSFER_BANK_NAME,
)


class PaymentGatewayService:
    def build_checkout_session(self, order: Dict[str, Any]) -> Dict[str, Any]:
        channel = order.get("payment_channel", "")
        if channel == "sandbox_card":
            return self._sandbox_session(order)
        if channel == "manual_transfer":
            return self._manual_transfer_session(order)
        raise ValueError("Unsupported payment channel")

    def _sandbox_session(self, order: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "provider": "sandbox_gateway",
            "mode": "instant",
            "checkout_label": "本地沙盒支付",
            "checkout_url": "",
            "provider_order_ref": f"SBX-{order['id'][:12].upper()}",
            "instructions": [
                "该订单使用本地沙盒支付通道。",
                "客户点击“立即完成沙盒支付”后会直接模拟支付成功。",
                "适合开发、演示和自动化回归，不连接外部网关。",
            ],
            "webhook_endpoint": f"{COMMERCIAL_BACKEND_URL}/api/billing/webhooks/payment",
        }

    def _manual_transfer_session(self, order: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "provider": "manual_transfer",
            "mode": "offline",
            "checkout_label": "人工转账",
            "checkout_url": "",
            "provider_order_ref": f"MANUAL-{order['id'][:12].upper()}",
            "instructions": [
                f"开户名：{COMMERCIAL_MANUAL_TRANSFER_ACCOUNT_NAME}",
                f"开户行：{COMMERCIAL_MANUAL_TRANSFER_BANK_NAME}",
                f"账号：{COMMERCIAL_MANUAL_TRANSFER_ACCOUNT_NO}",
                f"转账备注请填写订单号：{order['order_no']}",
                "转账完成后回到账号中心提交付款备注，等待后台确认。",
            ],
            "webhook_endpoint": f"{COMMERCIAL_BACKEND_URL}/api/billing/webhooks/payment",
        }


payment_gateway_service = PaymentGatewayService()
