"""
Authentication and commercial admin routes.

包含：
- 邮箱验证码登录（send-code / verify-code）
- 传统密码登录（register / login）
- Token 刷新、用户信息、API Key 管理
- 管理员策略、用户管理、审计日志
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.models.orm_models import AdminConfig, User, VerificationCode
from backend.schemas.auth import (
    AuthResponse,
    RefreshTokenRequest,
    SendCodeRequest,
    UserPublic,
    VerifyCodeRequest,
)
from backend.services.audit_service import audit_service
from backend.services.auth_service import auth_service
from backend.services.email_service import email_service
from backend.core.settings import COMMERCIAL_AUDIT_LOG_LIMIT
from backend.utils.verification_code import generate_code, is_code_expired


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Pydantic 请求/响应模型（与原有代码保持一致）
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenRequest(BaseModel):
    refresh_token: str


class PlatformPolicyRequest(BaseModel):
    allow_registration: bool = True
    generation_mode: str = Field(default="free", pattern="^(free|member_only)$")
    member_tiers_allowed: List[str] = Field(default_factory=lambda: ["basic", "pro"])
    customer_can_manage_api: bool = False
    customer_can_manage_prompts: bool = False
    default_subscription_tier: str = Field(default="free", pattern="^(free|basic|pro)$")


class UserMembershipUpdateRequest(BaseModel):
    subscription_tier: str = Field(pattern="^(free|basic|pro)$")
    is_active: bool = True


class UserRoleUpdateRequest(BaseModel):
    role: str = Field(pattern="^(customer|support|operator|admin)$")


class APIKeyResponse(BaseModel):
    api_key: str
    message: str


# ---------------------------------------------------------------------------
# 依赖项：用户认证
# ---------------------------------------------------------------------------

def get_current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Authorization 头")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证方式")

    # 优先使用 auth_service 验证（主密钥），回退到 core/security.py（兼容双密钥）
    valid, user_id = auth_service.verify_token(token)
    if not valid or not user_id:
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            valid = bool(user_id)
    if not valid or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")

    user_data = auth_service.get_user(user_id)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return {
        "user_id": user_id,
        "email": user_data.get("email", ""),
        "role": user_data.get("role", "customer"),
        "role_name": auth_service.get_role_name(user_data.get("role", "customer")),
        "permissions": auth_service.get_permissions_for_role(user_data.get("role", "customer")),
        "is_admin": user_data.get("role", "customer") == "admin",
        "is_backoffice": auth_service.has_permission_for_role(user_data.get("role", "customer"), "backoffice.view"),
    }


def get_current_admin(user: dict = Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可访问")
    return user


def require_permission(permission: str):
    def dependency(user: dict = Depends(get_current_user)):
        if not auth_service.has_permission_for_role(user.get("role", "customer"), permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号无权执行该操作")
        return user

    return dependency


# ===========================================================================
# 邮箱验证码登录端点
# ===========================================================================

@router.post("/send-code")
async def send_verification_code(
    payload: SendCodeRequest,
    db: Session = Depends(get_db),
):
    """发送验证码到邮箱。

    流程：
    1. 检查60秒冷却（同邮箱）
    2. 生成6位数字验证码
    3. 存入 VerificationCode 表
    4. 调用邮件服务发送
    5. 返回成功
    """
    email = payload.email.lower().strip()

    # 60秒冷却检查
    recent_cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
    recent_code = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.email == email,
            VerificationCode.created_at >= recent_cutoff,
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )
    if recent_code:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请60秒后再试",
        )

    # 生成验证码
    code = generate_code(length=6)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    # 存入数据库
    verification = VerificationCode(
        email=email,
        code=code,
        expires_at=expires_at,
        used=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(verification)
    db.commit()

    # 发送邮件
    success = await email_service.send_verification_code(email, code)
    if not success:
        logger.warning("验证码邮件发送失败: %s", email)

    return {"success": True, "message": "验证码已发送"}


@router.post("/verify-code", response_model=AuthResponse)
async def verify_code_and_login(
    payload: VerifyCodeRequest,
    db: Session = Depends(get_db),
):
    """验证验证码，首次使用自动注册，返回 JWT。

    流程：
    1. 查找最近的有效验证码
    2. 校验是否过期 / 已使用
    3. 首次邮箱自动创建 User（ORM）
    4. 标记验证码已使用
    5. 生成 JWT（使用 core.security）
    6. 返回 AuthResponse
    """
    email = payload.email.lower().strip()
    code = payload.code.strip()

    # 查找验证码
    verification = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.email == email,
            VerificationCode.code == code,
            VerificationCode.used == False,
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已失效",
        )

    if is_code_expired(verification.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期，请重新获取",
        )

    # 标记验证码已使用
    verification.used = True
    db.commit()

    # 查找或创建用户
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # 首次使用，自动注册
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            email_verified=True,
            display_name=email.split("@")[0],
            role="customer",
            subscription_tier="free",
            balance=0.0,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        audit_service.record(
            "auth.auto_register",
            actor={"email": email, "role": "customer"},
            status="success",
            target_type="user",
            target_id=user.id,
            target_label=email,
            message="邮箱验证码自动注册",
        )
    else:
        # 更新邮箱验证状态
        if not user.email_verified:
            user.email_verified = True
            db.commit()

    # 确保旧的 auth_service 也知道该用户（兼容内存用户库）
    _sync_user_to_auth_service(user, db)

    # 生成 JWT
    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token(data={"sub": user.id, "email": user.email})

    user_public = UserPublic(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        role=user.role,
        subscription_tier=user.subscription_tier,
        subscription_expires_at=user.subscription_expires_at,
        balance=user.balance,
        is_active=user.is_active,
        created_at=user.created_at,
    )

    audit_service.record(
        "auth.verify_code_login",
        actor={"user_id": user.id, "email": email, "role": user.role},
        status="success",
        target_type="user",
        target_id=user.id,
        target_label=email,
        message="验证码登录成功",
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_public,
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(data: TokenRequest):
    """刷新 access_token。先尝试 core.security 解码，再回退到 auth_service。"""
    # 优先使用 core.security 的 decode_token
    payload = decode_token(data.refresh_token)
    if payload and payload.get("type") == "refresh":
        user_id = payload.get("sub")
        user_data = auth_service.get_user(user_id) if user_id else None
        if user_data:
            new_token = create_access_token(data={"sub": user_id, "email": user_data.get("email", "")})
            return {"access_token": new_token, "token_type": "bearer"}

    # 回退到 auth_service 的刷新逻辑
    success, message, result = auth_service.refresh_access_token(data.refresh_token)
    if not success:
        raise HTTPException(status_code=401, detail=message)
    return {"access_token": result["access_token"], "token_type": result["token_type"]}


@router.get("/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    user_data = auth_service.get_user_response(user["user_id"])
    if not user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return {"success": True, "data": user_data}


@router.get("/me/quota")
async def get_quota(user: dict = Depends(get_current_user)):
    has_quota, remaining = auth_service.check_quota(user["user_id"])
    can_generate, reason = auth_service.can_generate(user["user_id"])
    return {
        "success": True,
        "data": {
            "has_quota": has_quota,
            "remaining": remaining,
            "can_generate": can_generate,
            "generation_message": reason,
        },
    }


@router.post("/me/api-key")
async def generate_api_key(user: dict = Depends(get_current_user)):
    success, message, api_key = auth_service.generate_api_key(user["user_id"])
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return APIKeyResponse(api_key=api_key, message=message)


# ===========================================================================
# 公开策略
# ===========================================================================

@router.get("/policy")
async def get_public_policy():
    return {"success": True, "data": auth_service.get_public_platform_policy()}


# ===========================================================================
# 管理员端点
# ===========================================================================

@router.get("/admin/policy")
async def get_platform_policy(_user: dict = Depends(require_permission("policy.view"))):
    return {"success": True, "data": auth_service.get_platform_policy()}


@router.put("/admin/policy")
async def update_platform_policy(payload: PlatformPolicyRequest, user: dict = Depends(require_permission("policy.edit"))):
    policy = auth_service.update_platform_policy(payload.model_dump())
    audit_service.record(
        "admin.policy.update",
        actor=user,
        status="success",
        target_type="platform_policy",
        target_label="commercial_policy",
        message="平台策略已更新",
        metadata={
            "allow_registration": policy.get("allow_registration"),
            "generation_mode": policy.get("generation_mode"),
            "default_subscription_tier": policy.get("default_subscription_tier"),
            "member_tiers_allowed": policy.get("member_tiers_allowed", []),
        },
    )
    return {"success": True, "message": "平台策略已更新", "data": policy}


@router.get("/admin/users")
async def list_users(_user: dict = Depends(require_permission("users.view"))):
    return {"success": True, "data": auth_service.list_users()}


@router.put("/admin/users/{user_id}/membership")
async def update_user_membership(
    user_id: str,
    payload: UserMembershipUpdateRequest,
    user: dict = Depends(require_permission("users.membership.edit")),
):
    success, message, data = auth_service.update_user_membership(
        user_id=user_id,
        subscription_tier=payload.subscription_tier,
        is_active=payload.is_active,
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    audit_service.record(
        "admin.user.membership.update",
        actor=user,
        status="success",
        target_type="user",
        target_id=data["id"],
        target_label=data["email"],
        message=message,
        metadata={
            "subscription_tier": data["subscription_tier"],
            "is_active": data["is_active"],
        },
    )
    return {"success": True, "message": message, "data": data}


@router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    payload: UserRoleUpdateRequest,
    user: dict = Depends(require_permission("users.role.edit")),
):
    success, message, data = auth_service.update_user_role(user_id=user_id, role=payload.role)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    audit_service.record(
        "admin.user.role.update",
        actor=user,
        status="success",
        target_type="user",
        target_id=data["id"],
        target_label=data["email"],
        message=message,
        metadata={
            "role": data["role"],
            "role_name": data["role_name"],
        },
    )
    return {"success": True, "message": message, "data": data}


@router.get("/admin/roles")
async def list_roles(_user: dict = Depends(require_permission("users.view"))):
    return {"success": True, "data": auth_service.list_roles()}


@router.get("/admin/audit-logs")
async def list_audit_logs(
    limit: int = COMMERCIAL_AUDIT_LOG_LIMIT,
    actor_role: str = "",
    action_prefix: str = "",
    _user: dict = Depends(require_permission("audit.view")),
):
    safe_limit = min(max(limit, 1), 200)
    return {
        "success": True,
        "data": audit_service.list_logs(
            limit=safe_limit,
            actor_role=actor_role.strip(),
            action_prefix=action_prefix.strip(),
        ),
    }


# ===========================================================================
# 辅助函数
# ===========================================================================

def _sync_user_to_auth_service(orm_user: User, db: Session) -> None:
    """将 ORM User 同步到 auth_service 的内存用户库，确保两种数据源兼容。"""
    existing = auth_service.get_user(orm_user.id)
    if existing:
        return

    from backend.services.auth_service import USER_DB_LOCK

    with USER_DB_LOCK:
        # 再次检查（双重锁检查模式）
        if auth_service.get_user(orm_user.id):
            return

        user_data = {
            "id": orm_user.id,
            "email": orm_user.email,
            "password_hash": "",  # 验证码用户没有密码
            "username": orm_user.display_name or orm_user.email.split("@")[0],
            "is_active": orm_user.is_active,
            "is_verified": orm_user.email_verified,
            "role": orm_user.role,
            "subscription_tier": orm_user.subscription_tier,
            "daily_quota": auth_service._default_daily_quota(orm_user.subscription_tier),
            "used_today": 0,
            "last_reset_date": datetime.now(timezone.utc).date().isoformat(),
            "created_at": orm_user.created_at.isoformat() if orm_user.created_at else datetime.now(timezone.utc).isoformat(),
            "updated_at": orm_user.updated_at.isoformat() if orm_user.updated_at else datetime.now(timezone.utc).isoformat(),
        }
        auth_service.users[orm_user.id] = user_data
        auth_service._save_users()


def _sync_auth_user_to_db(user_id: str, db: Session) -> None:
    """将 auth_service 中的用户同步到 SQLAlchemy 数据库（反向同步）。

    当 billing/admin 端点通过 user_id 查询数据库但找不到用户时，
    自动从 auth_service 同步过去，确保两个数据源一致。
    """
    user_data = auth_service.get_user(user_id)
    if not user_data:
        return

    existing = db.query(User).filter(User.id == user_id).first()
    if existing:
        return

    orm_user = User(
        id=user_id,
        email=user_data.get("email", ""),
        display_name=user_data.get("username", ""),
        role=user_data.get("role", "customer"),
        is_active=user_data.get("is_active", True),
        email_verified=user_data.get("is_verified", False),
        subscription_tier=user_data.get("subscription_tier", "free"),
        balance=getattr(existing, "balance", 0.0) if existing else 0.0,
    )
    db.add(orm_user)
    db.commit()
    db.refresh(orm_user)
