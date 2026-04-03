"""
ORM 模型定义

使用 SQLAlchemy 2.x 风格（Mapped, mapped_column）定义所有数据表。
每个模型提供 ``to_dict()`` 方法用于 JSON 序列化。

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="customer",
    )  # customer / admin / operator

    subscription_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="free",
    )  # free / basic / pro

    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    balance: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # relationships
    projects: Mapped[list[Project]] = relationship(
        "Project", back_populates="owner", lazy="selectin",
    )
    generation_jobs: Mapped[list[GenerationJob]] = relationship(
        "GenerationJob", back_populates="owner", lazy="selectin",
    )
    orders: Mapped[list[Order]] = relationship(
        "Order", back_populates="user", lazy="selectin",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "email_verified": self.email_verified,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "role": self.role,
            "subscription_tier": self.subscription_tier,
            "subscription_expires_at": self.subscription_expires_at.isoformat() if self.subscription_expires_at else None,
            "balance": self.balance,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    character_setting: Mapped[str | None] = mapped_column(Text, nullable=True)
    world_setting: Mapped[str | None] = mapped_column(Text, nullable=True)
    plot_idea: Mapped[str | None] = mapped_column(Text, nullable=True)
    chapter_count: Mapped[int] = mapped_column(Integer, default=0)

    # JSON 文本字段
    outline: Mapped[str | None] = mapped_column(Text, nullable=True)
    chapters: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # relationships
    owner: Mapped[User] = relationship("User", back_populates="projects")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "genre": self.genre,
            "character_setting": self.character_setting,
            "world_setting": self.world_setting,
            "plot_idea": self.plot_idea,
            "chapter_count": self.chapter_count,
            "outline": json.loads(self.outline) if self.outline else None,
            "chapters": json.loads(self.chapters) if self.chapters else None,
            "owner_user_id": self.owner_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# GenerationJob
# ---------------------------------------------------------------------------

class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", index=True,
    )  # queued / running / completed / failed

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=True, index=True,
    )

    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    export_format: Mapped[str | None] = mapped_column(String(20), nullable=True)

    owner_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True,
    )

    # JSON 文本字段
    request_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # relationships
    owner: Mapped[User] = relationship("User", back_populates="generation_jobs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "title": self.title,
            "project_id": self.project_id,
            "progress": self.progress,
            "current_step": self.current_step,
            "message": self.message,
            "error": self.error,
            "export_format": self.export_format,
            "owner_user_id": self.owner_user_id,
            "request_payload": json.loads(self.request_payload) if self.request_payload else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    order_no: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True,
    )

    target_tier: Mapped[str] = mapped_column(String(20), nullable=False)  # basic / pro
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="CNY")

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending_payment", index=True,
    )  # pending_payment / paid / cancelled / refunded

    payment_channel: Mapped[str] = mapped_column(
        String(30), nullable=False, default="alipay",
    )  # alipay / card_code / manual_transfer

    payment_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # relationships
    user: Mapped[User] = relationship("User", back_populates="orders")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "order_no": self.order_no,
            "user_id": self.user_id,
            "target_tier": self.target_tier,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "payment_channel": self.payment_channel,
            "payment_reference": self.payment_reference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# CardCode
# ---------------------------------------------------------------------------

class CardCode(Base):
    __tablename__ = "card_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
    )

    tier: Mapped[str] = mapped_column(String(20), nullable=False)  # basic / pro
    days: Mapped[int] = mapped_column(Integer, nullable=False)  # 30 / 365
    value_yuan: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available", index=True,
    )  # available / redeemed / expired / disabled

    redeemed_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True,
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "tier": self.tier,
            "days": self.days,
            "value_yuan": self.value_yuan,
            "status": self.status,
            "redeemed_by_user_id": self.redeemed_by_user_id,
            "redeemed_at": self.redeemed_at.isoformat() if self.redeemed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


# ---------------------------------------------------------------------------
# EmailLog
# ---------------------------------------------------------------------------

class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    email_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # verification_code / notification / etc

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sent",
    )  # sent / failed

    content_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "to_email": self.to_email,
            "email_type": self.email_type,
            "status": self.status,
            "content_summary": self.content_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# VerificationCode
# ---------------------------------------------------------------------------

class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    # 复合索引：email + code，加速验证查询
    __table_args__ = (
        Index("ix_verification_codes_email_code", "email", "code"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "code": self.code,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "used": self.used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# AdminConfig
# ---------------------------------------------------------------------------

class AdminConfig(Base):
    __tablename__ = "admin_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    config_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
    )
    config_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    value_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="string",
    )  # string / json / number / boolean

    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    def to_dict(self) -> dict[str, Any]:
        """序列化时根据 ``value_type`` 自动解析 ``config_value``。"""
        raw = self.config_value
        parsed: Any = raw
        if raw is not None:
            match self.value_type:
                case "json":
                    try:
                        parsed = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        parsed = raw
                case "number":
                    try:
                        parsed = float(raw)
                        if parsed == int(parsed):
                            parsed = int(parsed)
                    except (ValueError, TypeError):
                        parsed = raw
                case "boolean":
                    parsed = raw.lower() in ("true", "1", "yes")
        return {
            "id": self.id,
            "config_key": self.config_key,
            "config_value": parsed,
            "value_type": self.value_type,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
