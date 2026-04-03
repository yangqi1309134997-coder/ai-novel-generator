"""
用户数据模型

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID, uuid4


# 订阅层级配置
SUBSCRIPTION_TIERS = {
    "free": {
        "name": "免费用户",
        "daily_quota": 3,
        "price": 0,
        "features": ["每天3章", "基础生成功能"]
    },
    "basic": {
        "name": "基础会员",
        "daily_quota": 50,
        "price": 29,
        "features": ["每天50章", "优先生成", "导出功能"]
    },
    "pro": {
        "name": "专业会员",
        "daily_quota": 999999,  # 无限
        "price": 99,
        "features": ["无限章节", "优先生成", "全部功能", "API访问"]
    }
}


class UserBase(BaseModel):
    """用户基础模型"""
    email: EmailStr
    username: Optional[str] = None


class UserCreate(UserBase):
    """用户注册模型"""
    password: str = Field(..., min_length=6, max_length=50)


class UserLogin(BaseModel):
    """用户登录模型"""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """用户响应模型"""
    id: str
    is_active: bool = True
    is_verified: bool = False
    subscription_tier: str = "free"
    daily_quota: int = 3
    used_today: int = 0
    remaining_quota: int = 3
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """令牌响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserProfile(BaseModel):
    """用户资料模型"""
    id: str
    email: str
    username: Optional[str]
    avatar_url: Optional[str]
    subscription_tier: str
    subscription_name: str
    daily_quota: int
    used_today: int
    remaining_quota: int
    total_novels: int = 0
    total_chapters: int = 0
    total_words: int = 0
    created_at: datetime


class QuotaInfo(BaseModel):
    """配额信息模型"""
    tier: str
    tier_name: str
    daily_quota: int
    used_today: int
    remaining_quota: int
    reset_time: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API Key响应模型"""
    api_key: str
    created_at: datetime
    is_active: bool = True


# 数据库模型（SQLAlchemy格式，用于参考）
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(100))
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    subscription_tier = Column(String(50), default='free')
    daily_quota = Column(Integer, default=3)
    used_today = Column(Integer, default=0)
    api_key = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
"""
