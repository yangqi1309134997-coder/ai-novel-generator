"""
Commercial audit logging service.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from backend.services.state_store import state_store


AUTH_DATA_DIR = Path.home() / ".ai_novel_generator"
AUDIT_LOG_PATH = AUTH_DATA_DIR / "audit_logs.jsonl"
AUDIT_LOG_LOCK = Lock()
AUDIT_LOG_KEY = "audit_logs"
SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "password",
    "access_token",
    "refresh_token",
    "token",
    "secret",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in SENSITIVE_KEYS:
                sanitized[key_text] = "***"
            else:
                sanitized[key_text] = _sanitize(item)
        return sanitized

    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item) for item in value]

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


class AuditService:
    def __init__(self) -> None:
        AUTH_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _read_file_logs(self) -> List[Dict[str, Any]]:
        if not AUDIT_LOG_PATH.exists():
            return []

        events: List[Dict[str, Any]] = []
        for raw in AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return events

    def _load_logs(self) -> List[Dict[str, Any]]:
        if state_store.enabled:
            logs = state_store.get_json(AUDIT_LOG_KEY, [])
            if logs:
                return logs
            file_logs = self._read_file_logs()
            if file_logs:
                state_store.set_json(AUDIT_LOG_KEY, file_logs, updated_at=_utcnow().isoformat())
            return file_logs
        return self._read_file_logs()

    def record(
        self,
        action: str,
        actor: Optional[Dict[str, Any]] = None,
        *,
        status: str = "success",
        target_type: str = "",
        target_id: str = "",
        target_label: str = "",
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event = {
            "id": uuid.uuid4().hex,
            "timestamp": _utcnow().isoformat(),
            "action": action,
            "status": status,
            "actor_user_id": (actor or {}).get("user_id", ""),
            "actor_email": (actor or {}).get("email", ""),
            "actor_role": (actor or {}).get("role", ""),
            "target_type": target_type,
            "target_id": target_id,
            "target_label": target_label,
            "message": message,
            "metadata": _sanitize(metadata or {}),
        }

        with AUDIT_LOG_LOCK:
            if state_store.enabled:
                logs = self._load_logs()
                logs.append(event)
                state_store.set_json(AUDIT_LOG_KEY, logs, updated_at=event["timestamp"])
            else:
                AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                with AUDIT_LOG_PATH.open("a", encoding="utf-8") as file:
                    file.write(json.dumps(event, ensure_ascii=False) + "\n")

        return event

    def list_logs(
        self,
        *,
        limit: int = 100,
        actor_role: str = "",
        action_prefix: str = "",
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        with AUDIT_LOG_LOCK:
            logs = self._load_logs()

        for event in reversed(logs):

            if actor_role and event.get("actor_role") != actor_role:
                continue
            if action_prefix and not str(event.get("action", "")).startswith(action_prefix):
                continue

            events.append(event)
            if len(events) >= max(1, limit):
                break

        return events


audit_service = AuditService()
