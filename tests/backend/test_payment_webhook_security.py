from __future__ import annotations

from backend.core.security import sign_payment_webhook, verify_payment_webhook_signature


def test_payment_webhook_signature_round_trip():
    timestamp = "1774656000"
    body = b'{"event_id":"evt_1","status":"paid"}'
    signature = sign_payment_webhook(body, timestamp)

    assert verify_payment_webhook_signature(body, timestamp, signature) is True
    assert verify_payment_webhook_signature(body, timestamp, "invalid-signature") is False
