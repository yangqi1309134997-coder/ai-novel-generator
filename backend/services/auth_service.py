"""
Authentication and commercial user management service.
"""

from __future__ import annotations

import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from jose import jwt
from passlib.context import CryptContext

from backend.core.security import pwd_context, SECRET_KEY as PERSISTED_SECRET_KEY
from backend.services.audit_service import audit_service
from backend.services.platform_service import platform_service
from backend.services.state_store import state_store


logger = logging.getLogger(__name__)

AUTH_DATA_DIR = Path.home() / ".ai_novel_generator"
SECRET_KEY_PATH = AUTH_DATA_DIR / "jwt_secret.key"
USER_DB_PATH = AUTH_DATA_DIR / "users.json"
USER_DB_LOCK = Lock()
USER_DB_KEY = "users"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(hours=24)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)

SUBSCRIPTION_TIERS: Dict[str, Dict[str, Any]] = {
    "free": {"daily_quota": 3, "price": 0, "name": "免费用户"},
    "basic": {"daily_quota": 50, "price": 29, "name": "基础会员"},
    "pro": {"daily_quota": -1, "price": 99, "name": "专业会员"},
}

ROLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "customer": {
        "name": "客户用户",
        "permissions": [
            "billing.create",
            "billing.view_own",
        ],
    },
    "support": {
        "name": "客服支持",
        "permissions": [
            "backoffice.view",
            "billing.view_all",
            "users.view",
            "audit.view",
        ],
    },
    "operator": {
        "name": "运营人员",
        "permissions": [
            "backoffice.view",
            "policy.view",
            "policy.edit",
            "users.view",
            "users.membership.edit",
            "billing.view_all",
            "billing.manage",
            "api_config.view",
            "api_config.edit",
            "api_config.test",
            "audit.view",
        ],
    },
    "admin": {
        "name": "管理员",
        "permissions": [
            "backoffice.view",
            "policy.view",
            "policy.edit",
            "users.view",
            "users.membership.edit",
            "users.role.edit",
            "billing.view_all",
            "billing.manage",
            "api_config.view",
            "api_config.edit",
            "api_config.test",
            "audit.view",
            "prompts.view",
            "prompts.edit",
            # Admin router permissions (with admin. prefix)
            "admin.stats.view",
            "admin.config.view",
            "admin.config.edit",
            "admin.users.view",
            "admin.users.ban",
            "admin.users.balance",
            "admin.card_codes.generate",
            "admin.card_codes.view",
            "admin.card_codes.disable",
            "admin.orders.view",
            "admin.audit.view",
        ],
    },
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# 使用 core/security.py 中的统一持久化密钥
SECRET_KEY = PERSISTED_SECRET_KEY


class AuthService:
    def __init__(self) -> None:
        self.users: Dict[str, Dict[str, Any]] = {}
        self._load_users()

    def _load_users(self) -> None:
        try:
            if state_store.enabled:
                data = state_store.get_json(USER_DB_KEY, {})
                self.users = data.get("users", {}) if isinstance(data, dict) else {}
                if not self.users and USER_DB_PATH.exists():
                    with open(USER_DB_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.users = data.get("users", {})
                    self._save_users()
            elif USER_DB_PATH.exists():
                with open(USER_DB_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.users = data.get("users", {})
            self._ensure_admin_exists()
            logger.info("已加载 %s 个用户", len(self.users))
        except Exception as exc:
            logger.error("加载用户数据失败: %s", exc)
            self.users = {}

    def _save_users(self) -> None:
        payload = {"users": self.users}
        if state_store.enabled:
            state_store.set_json(USER_DB_KEY, payload, updated_at=_utcnow().isoformat())
            return

        USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USER_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _ensure_admin_exists(self) -> None:
        if not self.users:
            return

        admins = [user for user in self.users.values() if user.get("role") == "admin"]
        if admins:
            return

        first_user = sorted(
            self.users.values(),
            key=lambda item: item.get("created_at", ""),
        )[0]
        first_user["role"] = "admin"
        first_user["updated_at"] = _utcnow().isoformat()
        self._save_users()

    def _default_daily_quota(self, tier: str) -> int:
        return SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])["daily_quota"]

    def _normalize_role(self, role: str) -> str:
        return role if role in ROLE_DEFINITIONS else "customer"

    def get_role_name(self, role: str) -> str:
        normalized = self._normalize_role(role)
        return ROLE_DEFINITIONS[normalized]["name"]

    def get_permissions_for_role(self, role: str) -> List[str]:
        normalized = self._normalize_role(role)
        return list(ROLE_DEFINITIONS[normalized]["permissions"])

    def has_permission_for_role(self, role: str, permission: str) -> bool:
        return permission in self.get_permissions_for_role(role)

    def list_roles(self) -> List[Dict[str, Any]]:
        return [
            {
                "value": value,
                "label": definition["name"],
                "permissions": list(definition["permissions"]),
            }
            for value, definition in ROLE_DEFINITIONS.items()
        ]

    def _create_access_token(self, user_id: str, email: str) -> str:
        payload = {
            "sub": user_id,
            "email": email,
            "exp": (_utcnow() + ACCESS_TOKEN_EXPIRE).timestamp(),
            "type": "access",
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def _create_refresh_token(self, user_id: str, email: str) -> str:
        payload = {
            "sub": user_id,
            "email": email,
            "exp": (_utcnow() + REFRESH_TOKEN_EXPIRE).timestamp(),
            "type": "refresh",
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def _remaining_quota(self, user_data: Dict[str, Any]) -> int:
        tier = user_data.get("subscription_tier", "free")
        daily_quota = self._default_daily_quota(tier)
        if daily_quota == -1:
            return 999999
        return max(0, daily_quota - user_data.get("used_today", 0))

    def _reset_quota_if_needed(self, user_data: Dict[str, Any]) -> None:
        today = _utcnow().date()
        last_reset_raw = user_data.get("last_reset_date")
        last_reset = None
        if last_reset_raw:
            try:
                last_reset = datetime.fromisoformat(last_reset_raw)
            except Exception:
                last_reset = None

        if not last_reset or last_reset.date() < today:
            user_data["used_today"] = 0
            user_data["last_reset_date"] = today.isoformat()

    def _build_generation_status(self, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        allowed, reason = platform_service.evaluate_generation_access(user_data)
        if not allowed:
            return False, reason

        tier = user_data.get("subscription_tier", "free")
        daily_quota = self._default_daily_quota(tier)
        if daily_quota == -1:
            return True, "当前账号可生成"

        remaining = self._remaining_quota(user_data)
        if remaining <= 0:
            return False, "今日生成配额已用完"
        return True, "当前账号可生成"

    def _to_user_response(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        self._reset_quota_if_needed(user_data)
        tier = user_data.get("subscription_tier", "free")
        role = self._normalize_role(user_data.get("role", "customer"))
        can_generate, generation_message = self._build_generation_status(user_data)

        return {
            "id": user_data["id"],
            "email": user_data["email"],
            "username": user_data.get("username"),
            "is_active": user_data.get("is_active", True),
            "is_verified": user_data.get("is_verified", False),
            "role": role,
            "role_name": self.get_role_name(role),
            "permissions": self.get_permissions_for_role(role),
            "is_admin": role == "admin",
            "is_backoffice": self.has_permission_for_role(role, "backoffice.view"),
            "subscription_tier": tier,
            "subscription_name": SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])["name"],
            "daily_quota": self._default_daily_quota(tier),
            "used_today": user_data.get("used_today", 0),
            "remaining_quota": self._remaining_quota(user_data),
            "can_generate": can_generate,
            "generation_message": generation_message,
            "created_at": user_data.get("created_at", _utcnow().isoformat()),
        }

    def create_user(self, email: str, password: str, username: str = None) -> Tuple[bool, str, Dict]:
        with USER_DB_LOCK:
            if self.users and not platform_service.allow_registration():
                audit_service.record(
                    "auth.register",
                    actor={"email": email, "role": "anonymous"},
                    status="denied",
                    target_type="user",
                    target_label=email,
                    message="注册被平台策略拒绝",
                )
                return False, "当前平台已关闭注册，请联系管理员开通账号", {}

            for user_data in self.users.values():
                if user_data.get("email") == email:
                    audit_service.record(
                        "auth.register",
                        actor={"email": email, "role": "anonymous"},
                        status="failed",
                        target_type="user",
                        target_label=email,
                        message="邮箱已被注册",
                    )
                    return False, "邮箱已被注册", {}

            user_id = str(uuid.uuid4())
            is_first_user = not self.users
            tier = platform_service.get_policy().get("default_subscription_tier", "free")
            tier = tier if tier in SUBSCRIPTION_TIERS else "free"
            role = "admin" if is_first_user else "customer"

            user_data = {
                "id": user_id,
                "email": email,
                "password_hash": pwd_context.hash(password),
                "username": username or email.split("@")[0],
                "is_active": True,
                "is_verified": False,
                "role": role,
                "subscription_tier": tier,
                "daily_quota": self._default_daily_quota(tier),
                "used_today": 0,
                "last_reset_date": _utcnow().date().isoformat(),
                "created_at": _utcnow().isoformat(),
                "updated_at": _utcnow().isoformat(),
            }

            self.users[user_id] = user_data
            self._save_users()

            audit_service.record(
                "auth.register",
                actor={"user_id": user_id, "email": email, "role": role},
                status="success",
                target_type="user",
                target_id=user_id,
                target_label=email,
                message="账号注册成功",
            )

            access_token = self._create_access_token(user_id, email)
            refresh_token = self._create_refresh_token(user_id, email)
            return True, "注册成功", {
                "user": self._to_user_response(user_data),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            }

    def login(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        with USER_DB_LOCK:
            user_data = next((data for data in self.users.values() if data.get("email") == email), None)
            if not user_data:
                audit_service.record(
                    "auth.login",
                    actor={"email": email, "role": "anonymous"},
                    status="failed",
                    target_type="user",
                    target_label=email,
                    message="邮箱不存在或密码错误",
                )
                return False, "邮箱或密码错误", None
            if not pwd_context.verify(password, user_data.get("password_hash", "")):
                audit_service.record(
                    "auth.login",
                    actor={"user_id": user_data["id"], "email": email, "role": user_data.get("role", "customer")},
                    status="failed",
                    target_type="user",
                    target_id=user_data["id"],
                    target_label=email,
                    message="邮箱不存在或密码错误",
                )
                return False, "邮箱或密码错误", None
            if not user_data.get("is_active", True):
                audit_service.record(
                    "auth.login",
                    actor={"user_id": user_data["id"], "email": email, "role": user_data.get("role", "customer")},
                    status="denied",
                    target_type="user",
                    target_id=user_data["id"],
                    target_label=email,
                    message="账号已被禁用",
                )
                return False, "账号已被禁用", None

            user_data["last_login_at"] = _utcnow().isoformat()
            user_data["updated_at"] = _utcnow().isoformat()
            self._save_users()

            audit_service.record(
                "auth.login",
                actor={"user_id": user_data["id"], "email": email, "role": user_data.get("role", "customer")},
                status="success",
                target_type="user",
                target_id=user_data["id"],
                target_label=email,
                message="登录成功",
            )

            access_token = self._create_access_token(user_data["id"], email)
            refresh_token = self._create_refresh_token(user_data["id"], email)
            return True, "登录成功", {
                "user": self._to_user_response(user_data),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            }

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.users.get(user_id)

    def get_user_response(self, user_id: str) -> Optional[Dict[str, Any]]:
        user_data = self.get_user(user_id)
        if not user_data:
            return None
        return self._to_user_response(user_data)

    def list_users(self) -> List[Dict[str, Any]]:
        users = [self._to_user_response(user) for user in self.users.values()]
        users.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return users

    def update_user_membership(
        self,
        user_id: str,
        subscription_tier: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with USER_DB_LOCK:
            user_data = self.users.get(user_id)
            if not user_data:
                return False, "用户不存在", None

            if subscription_tier:
                if subscription_tier not in SUBSCRIPTION_TIERS:
                    return False, "无效的会员等级", None
                user_data["subscription_tier"] = subscription_tier
                user_data["daily_quota"] = self._default_daily_quota(subscription_tier)

            if is_active is not None:
                user_data["is_active"] = is_active

            user_data["updated_at"] = _utcnow().isoformat()
            self._save_users()
            return True, "用户会员状态已更新", self._to_user_response(user_data)

    def update_user_role(self, user_id: str, role: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with USER_DB_LOCK:
            user_data = self.users.get(user_id)
            if not user_data:
                return False, "用户不存在", None

            normalized_role = self._normalize_role(role)
            current_role = self._normalize_role(user_data.get("role", "customer"))

            if current_role == "admin" and normalized_role != "admin":
                admin_count = sum(
                    1 for item in self.users.values() if self._normalize_role(item.get("role", "customer")) == "admin"
                )
                if admin_count <= 1:
                    return False, "至少保留一个管理员账号", None

            user_data["role"] = normalized_role
            user_data["updated_at"] = _utcnow().isoformat()
            self._save_users()
            return True, "账号角色已更新", self._to_user_response(user_data)

    def verify_token(self, token: str) -> Tuple[bool, Optional[str]]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") == "access":
                return True, payload.get("sub")
            return False, None
        except Exception:
            return False, None

    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, str, Optional[Dict]]:
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "refresh":
                return False, "无效的刷新令牌", None

            user_id = payload.get("sub")
            user_data = self.users.get(user_id)
            if not user_data:
                return False, "用户不存在", None

            access_token = self._create_access_token(user_id, user_data["email"])
            return True, "令牌刷新成功", {
                "access_token": access_token,
                "token_type": "bearer",
            }
        except Exception:
            return False, "令牌刷新失败", None

    def check_quota(self, user_id: str) -> Tuple[bool, int]:
        user_data = self.users.get(user_id)
        if not user_data:
            return False, 0

        self._reset_quota_if_needed(user_data)
        remaining = self._remaining_quota(user_data)
        if self._default_daily_quota(user_data.get("subscription_tier", "free")) == -1:
            return True, 999999
        return remaining > 0, remaining

    def use_quota(self, user_id: str) -> Tuple[bool, str]:
        user_data = self.users.get(user_id)
        if not user_data:
            return False, "用户不存在"

        self._reset_quota_if_needed(user_data)
        has_quota, remaining = self.check_quota(user_id)
        if not has_quota:
            return False, f"今日配额已用完，剩余: {remaining}"

        if self._default_daily_quota(user_data.get("subscription_tier", "free")) != -1:
            user_data["used_today"] = user_data.get("used_today", 0) + 1
            user_data["updated_at"] = _utcnow().isoformat()
            self._save_users()
            return True, f"配额使用成功，剩余: {remaining - 1}"

        return True, "专业会员不限配额"

    def can_generate(self, user_id: str) -> Tuple[bool, str]:
        user_data = self.users.get(user_id)
        if not user_data:
            return False, "用户不存在"
        self._reset_quota_if_needed(user_data)
        return self._build_generation_status(user_data)

    def generate_api_key(self, user_id: str) -> Tuple[bool, str, Optional[str]]:
        user_data = self.users.get(user_id)
        if not user_data:
            return False, "用户不存在", None

        if user_data.get("subscription_tier") != "pro":
            return False, "只有专业会员可以使用 API Key", None

        api_key = f"sk-{secrets.token_urlsafe(32)}"
        user_data["api_key"] = api_key
        user_data["updated_at"] = _utcnow().isoformat()
        self._save_users()
        return True, "API Key 生成成功", api_key

    def is_admin(self, user_id: str) -> bool:
        user_data = self.users.get(user_id)
        return bool(user_data and user_data.get("role") == "admin")

    def get_platform_policy(self) -> Dict[str, Any]:
        return platform_service.get_policy()

    def update_platform_policy(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        return platform_service.update_policy(updates)

    def get_public_platform_policy(self) -> Dict[str, Any]:
        return platform_service.get_public_policy()


auth_service = AuthService()
