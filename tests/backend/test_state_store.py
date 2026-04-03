from __future__ import annotations

from backend.services.state_store import SqliteStateStore


def test_sqlite_state_store_round_trip(tmp_path):
    db_path = tmp_path / "commercial_state.db"
    store = SqliteStateStore(str(db_path))

    assert store.enabled is True
    assert store.get_json("missing", {"ok": False}) == {"ok": False}

    payload = {"users": {"u-1": {"email": "test@example.com", "role": "customer"}}}
    store.set_json("users", payload, updated_at="2026-03-28T00:00:00+00:00")

    reloaded = SqliteStateStore(str(db_path))
    assert reloaded.get_json("users", {}) == payload
