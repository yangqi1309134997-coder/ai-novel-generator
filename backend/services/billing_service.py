"""
Commercial subscription billing service.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from backend.services.auth_service import SUBSCRIPTION_TIERS
from backend.services.state_store import state_store


AUTH_DATA_DIR = Path.home() / ".ai_novel_generator"
BILLING_DB_PATH = AUTH_DATA_DIR / "billing.json"
BILLING_DB_LOCK = Lock()
BILLING_STATE_KEY = "billing_state"

PAID_TIERS = ("basic", "pro")
TIER_ORDER = {
    "free": 0,
    "basic": 1,
    "pro": 2,
}
PAYMENT_CHANNELS: Dict[str, Dict[str, str]] = {
    "sandbox_card": {
        "name": "沙盒支付",
        "description": "用于本地回归和演示环境的模拟支付通道",
    },
    "manual_transfer": {
        "name": "人工转账",
        "description": "客户提交转账备注后，等待后台确认到账",
    },
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BillingService:
    def __init__(self) -> None:
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._invoices: Dict[str, Dict[str, Any]] = {}
        self._webhook_events: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        AUTH_DATA_DIR.mkdir(parents=True, exist_ok=True)
        if state_store.enabled:
            data = state_store.get_json(BILLING_STATE_KEY, {})
            if data:
                self._orders = data.get("orders", {})
                self._invoices = data.get("invoices", {})
                self._webhook_events = data.get("webhook_events", {})
                return
            if BILLING_DB_PATH.exists():
                try:
                    data = json.loads(BILLING_DB_PATH.read_text(encoding="utf-8"))
                    self._orders = data.get("orders", {})
                    self._invoices = data.get("invoices", {})
                    self._webhook_events = data.get("webhook_events", {})
                    self._save()
                    return
                except Exception:
                    pass
            self._save()
            return

        if not BILLING_DB_PATH.exists():
            self._save()
            return

        try:
            data = json.loads(BILLING_DB_PATH.read_text(encoding="utf-8"))
            self._orders = data.get("orders", {})
            self._invoices = data.get("invoices", {})
            self._webhook_events = data.get("webhook_events", {})
        except Exception:
            self._orders = {}
            self._invoices = {}
            self._webhook_events = {}
            self._save()

    def _save(self) -> None:
        payload = {
            "orders": self._orders,
            "invoices": self._invoices,
            "webhook_events": self._webhook_events,
            "updated_at": _utcnow().isoformat(),
        }
        if state_store.enabled:
            state_store.set_json(BILLING_STATE_KEY, payload, updated_at=payload["updated_at"])
            return
        BILLING_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        BILLING_DB_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_plans(self) -> List[Dict[str, Any]]:
        plans: List[Dict[str, Any]] = []
        for tier in PAID_TIERS:
            config = SUBSCRIPTION_TIERS[tier]
            plans.append({
                "tier": tier,
                "name": config["name"],
                "price": config["price"],
                "currency": "CNY",
                "daily_quota": config["daily_quota"],
                "is_unlimited": config["daily_quota"] == -1,
                "description": f"{config['name']} · ¥{config['price']}/月",
            })
        return plans

    def list_payment_channels(self) -> List[Dict[str, str]]:
        return [
            {
                "value": value,
                "label": data["name"],
                "description": data["description"],
            }
            for value, data in PAYMENT_CHANNELS.items()
        ]

    def create_order(
        self,
        *,
        user_id: str,
        user_email: str,
        current_tier: str,
        target_tier: str,
        payment_channel: str,
        note: str = "",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        if target_tier not in PAID_TIERS:
            return False, "当前只支持基础会员或专业会员的升级订单", None

        if payment_channel not in PAYMENT_CHANNELS:
            return False, "无效的支付通道", None

        current_rank = TIER_ORDER.get(current_tier, 0)
        target_rank = TIER_ORDER.get(target_tier, 0)
        if target_rank <= current_rank:
            return False, "目标会员等级必须高于当前等级", None

        with BILLING_DB_LOCK:
            active_pending = [
                order for order in self._orders.values()
                if order.get("user_id") == user_id
                and order.get("status") in {"pending_payment", "payment_submitted"}
            ]
            if active_pending:
                return False, "你还有未完成的升级订单，请先完成或取消当前订单", None

            config = SUBSCRIPTION_TIERS[target_tier]
            now = _utcnow().isoformat()
            order_id = uuid.uuid4().hex
            order = {
                "id": order_id,
                "order_no": f"ORD-{order_id[:10].upper()}",
                "user_id": user_id,
                "user_email": user_email,
                "current_tier": current_tier,
                "target_tier": target_tier,
                "target_name": config["name"],
                "amount": config["price"],
                "currency": "CNY",
                "payment_channel": payment_channel,
                "payment_channel_name": PAYMENT_CHANNELS[payment_channel]["name"],
                "status": "pending_payment",
                "note": note.strip(),
                "payment_reference": "",
                "invoice_id": "",
                "created_at": now,
                "updated_at": now,
                "paid_at": "",
            }
            self._orders[order_id] = order
            self._save()
            return True, "升级订单已创建", dict(order)

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        order = self._orders.get(order_id)
        return dict(order) if order else None

    def find_invoice_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        for invoice in self._invoices.values():
            if invoice.get("order_id") == order_id:
                return dict(invoice)
        return None

    def get_webhook_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        event = self._webhook_events.get(event_id)
        return dict(event) if event else None

    def list_orders(
        self,
        *,
        user_id: str = "",
        include_all: bool = False,
        status: str = "",
    ) -> List[Dict[str, Any]]:
        orders = list(self._orders.values())
        if not include_all:
            orders = [order for order in orders if order.get("user_id") == user_id]
        if status:
            orders = [order for order in orders if order.get("status") == status]
        orders.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return [dict(order) for order in orders]

    def list_invoices(
        self,
        *,
        user_id: str = "",
        include_all: bool = False,
    ) -> List[Dict[str, Any]]:
        invoices = list(self._invoices.values())
        if not include_all:
            invoices = [invoice for invoice in invoices if invoice.get("user_id") == user_id]
        invoices.sort(key=lambda item: item.get("issued_at", ""), reverse=True)
        return [dict(invoice) for invoice in invoices]

    def submit_manual_payment(
        self,
        order_id: str,
        *,
        payment_reference: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with BILLING_DB_LOCK:
            order = self._orders.get(order_id)
            if not order:
                return False, "订单不存在", None
            if order.get("status") != "pending_payment":
                return False, "当前订单状态不允许提交付款备注", None
            if order.get("payment_channel") != "manual_transfer":
                return False, "只有人工转账订单需要提交付款备注", None

            order["status"] = "payment_submitted"
            order["payment_reference"] = payment_reference.strip()
            order["updated_at"] = _utcnow().isoformat()
            self._save()
            return True, "付款备注已提交，等待后台确认", dict(order)

    def mark_order_paid(
        self,
        order_id: str,
        *,
        payment_reference: str = "",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        with BILLING_DB_LOCK:
            order = self._orders.get(order_id)
            if not order:
                return False, "订单不存在", None, None
            if order.get("status") == "paid":
                existing_invoice = self.find_invoice_by_order_id(order_id)
                existing_order = dict(order)
                return True, "订单已是支付完成状态", existing_order, existing_invoice
            if order.get("status") not in {"pending_payment", "payment_submitted"}:
                return False, "当前订单状态不允许确认支付", None, None

            paid_at = _utcnow().isoformat()
            invoice_id = uuid.uuid4().hex
            invoice = {
                "id": invoice_id,
                "invoice_no": f"INV-{invoice_id[:10].upper()}",
                "order_id": order["id"],
                "order_no": order["order_no"],
                "user_id": order["user_id"],
                "user_email": order["user_email"],
                "tier": order["target_tier"],
                "tier_name": order["target_name"],
                "amount": order["amount"],
                "currency": order["currency"],
                "payment_channel": order["payment_channel"],
                "payment_channel_name": order["payment_channel_name"],
                "issued_at": paid_at,
            }

            order["status"] = "paid"
            order["payment_reference"] = payment_reference.strip() or order.get("payment_reference", "")
            order["invoice_id"] = invoice_id
            order["paid_at"] = paid_at
            order["updated_at"] = paid_at
            self._invoices[invoice_id] = invoice
            self._save()
            return True, "订单已完成支付", dict(order), dict(invoice)

    def cancel_order(self, order_id: str, *, reason: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with BILLING_DB_LOCK:
            order = self._orders.get(order_id)
            if not order:
                return False, "订单不存在", None
            if order.get("status") not in {"pending_payment", "payment_submitted"}:
                return False, "当前订单状态不允许取消", None

            order["status"] = "cancelled"
            order["note"] = reason.strip() or order.get("note", "")
            order["updated_at"] = _utcnow().isoformat()
            self._save()
            return True, "订单已取消", dict(order)

    def record_webhook_event(
        self,
        *,
        event_id: str,
        order_id: str,
        event_type: str,
        status: str,
        payload: Dict[str, Any],
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        with BILLING_DB_LOCK:
            existing = self._webhook_events.get(event_id)
            if existing:
                return False, dict(existing)

            event = {
                "event_id": event_id,
                "order_id": order_id,
                "event_type": event_type,
                "status": status,
                "payload": payload,
                "received_at": _utcnow().isoformat(),
            }
            self._webhook_events[event_id] = event
            self._save()
            return True, dict(event)


billing_service = BillingService()
