from __future__ import annotations

from backend.services.payment_gateway import payment_gateway_service


def test_sandbox_checkout_session_shape():
    order = {
        "id": "abc123def456",
        "order_no": "ORD-ABC123DEF4",
        "payment_channel": "sandbox_card",
    }

    session = payment_gateway_service.build_checkout_session(order)
    assert session["provider"] == "sandbox_gateway"
    assert session["mode"] == "instant"
    assert session["provider_order_ref"].startswith("SBX-")
    assert session["instructions"]


def test_manual_transfer_checkout_session_shape():
    order = {
        "id": "manual123456",
        "order_no": "ORD-MANUAL123",
        "payment_channel": "manual_transfer",
    }

    session = payment_gateway_service.build_checkout_session(order)
    assert session["provider"] == "manual_transfer"
    assert session["mode"] == "offline"
    assert session["provider_order_ref"].startswith("MANUAL-")
    assert any("订单号" in item for item in session["instructions"])
