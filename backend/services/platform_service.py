"""
Commercial platform policy service.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Tuple

from backend.services.state_store import state_store


AUTH_DATA_DIR = Path.home() / ".ai_novel_generator"
PLATFORM_POLICY_PATH = AUTH_DATA_DIR / "platform_policy.json"
PLATFORM_POLICY_LOCK = Lock()
PLATFORM_POLICY_KEY = "platform_policy"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

DEFAULT_PLATFORM_POLICY: Dict[str, Any] = {
    "commercial_mode": True,
    "allow_registration": True,
    "generation_mode": "free",
    "member_tiers_allowed": ["basic", "pro"],
    "customer_can_manage_api": False,
    "customer_can_manage_prompts": False,
    "default_subscription_tier": "free",
}


class PlatformService:
    def __init__(self) -> None:
        self._policy = DEFAULT_PLATFORM_POLICY.copy()
        self._load()

    def _load(self) -> None:
        AUTH_DATA_DIR.mkdir(parents=True, exist_ok=True)
        if state_store.enabled:
            data = state_store.get_json(PLATFORM_POLICY_KEY, {})
            if data:
                self._policy = {**DEFAULT_PLATFORM_POLICY, **data}
                return
            if PLATFORM_POLICY_PATH.exists():
                try:
                    data = json.loads(PLATFORM_POLICY_PATH.read_text(encoding="utf-8"))
                    self._policy = {**DEFAULT_PLATFORM_POLICY, **data}
                    self._save()
                    return
                except Exception:
                    pass
            self._save()
            return

        if not PLATFORM_POLICY_PATH.exists():
            self._save()
            return

        try:
            data = json.loads(PLATFORM_POLICY_PATH.read_text(encoding="utf-8"))
            self._policy = {**DEFAULT_PLATFORM_POLICY, **data}
        except Exception:
            self._policy = DEFAULT_PLATFORM_POLICY.copy()
            self._save()

    def _save(self) -> None:
        AUTH_DATA_DIR.mkdir(parents=True, exist_ok=True)
        if state_store.enabled:
            state_store.set_json(PLATFORM_POLICY_KEY, self._policy, updated_at=self._policy.get("updated_at", ""))
            return
        PLATFORM_POLICY_PATH.write_text(
            json.dumps(self._policy, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_policy(self) -> Dict[str, Any]:
        with PLATFORM_POLICY_LOCK:
            return dict(self._policy)

    def update_policy(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        with PLATFORM_POLICY_LOCK:
            next_policy = {**self._policy, **updates}
            next_policy["member_tiers_allowed"] = list(next_policy.get("member_tiers_allowed", []))
            next_policy["updated_at"] = _utcnow_iso()
            self._policy = next_policy
            self._save()
            return dict(self._policy)

    def allow_registration(self) -> bool:
        return bool(self._policy.get("allow_registration", True))

    def get_public_policy(self) -> Dict[str, Any]:
        return {
            "commercial_mode": bool(self._policy.get("commercial_mode", True)),
            "generation_mode": self._policy.get("generation_mode", "free"),
            "customer_can_manage_api": bool(self._policy.get("customer_can_manage_api", False)),
            "customer_can_manage_prompts": bool(self._policy.get("customer_can_manage_prompts", False)),
            "allow_registration": bool(self._policy.get("allow_registration", True)),
        }

    def evaluate_generation_access(self, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        if not user_data:
            return False, "用户不存在"

        if not user_data.get("is_active", True):
            return False, "账号已被禁用"

        if user_data.get("role") == "admin":
            return True, "管理员可直接使用"

        mode = self._policy.get("generation_mode", "free")
        tier = user_data.get("subscription_tier", "free")
        allowed_tiers: List[str] = list(self._policy.get("member_tiers_allowed", ["basic", "pro"]))

        if mode == "free":
            return True, "当前平台允许免费生成"

        if tier in allowed_tiers:
            return True, f"{tier} 会员可生成"

        return False, "当前平台仅允许会员生成，请联系管理员开通会员"


platform_service = PlatformService()
