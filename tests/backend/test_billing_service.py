from __future__ import annotations

from threading import Lock

from backend.services import billing_service as billing_module


def build_billing_service(tmp_path, monkeypatch):
    monkeypatch.setattr(billing_module, "BILLING_DB_PATH", tmp_path / "billing.json")
    monkeypatch.setattr(billing_module, "BILLING_DB_LOCK", Lock())
    return billing_module.BillingService()


def test_create_and_complete_sandbox_order(tmp_path, monkeypatch):
    service = build_billing_service(tmp_path, monkeypatch)

    success, message, order = service.create_order(
        user_id="u-1",
        user_email="customer@example.com",
        current_tier="free",
        target_tier="basic",
        payment_channel="sandbox_card",
        note="sandbox",
    )
    assert success is True
    assert order["status"] == "pending_payment"
    assert order["amount"] == 29

    success, message, paid_order, invoice = service.mark_order_paid(order["id"], payment_reference="SANDBOX-123")
    assert success is True
    assert paid_order["status"] == "paid"
    assert paid_order["invoice_id"] == invoice["id"]
    assert invoice["order_id"] == order["id"]
    assert invoice["amount"] == 29


def test_manual_transfer_order_submit_and_cancel(tmp_path, monkeypatch):
    service = build_billing_service(tmp_path, monkeypatch)

    success, _, order = service.create_order(
        user_id="u-2",
        user_email="customer2@example.com",
        current_tier="free",
        target_tier="pro",
        payment_channel="manual_transfer",
        note="manual",
    )
    assert success is True
    assert order["status"] == "pending_payment"

    success, message, submitted = service.submit_manual_payment(order["id"], payment_reference="BANK-REF-001")
    assert success is True
    assert submitted["status"] == "payment_submitted"
    assert submitted["payment_reference"] == "BANK-REF-001"

    success, message, cancelled = service.cancel_order(order["id"], reason="customer changed mind")
    assert success is True
    assert cancelled["status"] == "cancelled"


def test_webhook_event_idempotency(tmp_path, monkeypatch):
    service = build_billing_service(tmp_path, monkeypatch)

    success, first = service.record_webhook_event(
        event_id="evt_123",
        order_id="ord_123",
        event_type="payment.paid",
        status="paid",
        payload={"ok": True},
    )
    assert success is True
    assert first["event_id"] == "evt_123"

    success, duplicate = service.record_webhook_event(
        event_id="evt_123",
        order_id="ord_123",
        event_type="payment.paid",
        status="paid",
        payload={"ok": True},
    )
    assert success is False
    assert duplicate["event_id"] == "evt_123"
