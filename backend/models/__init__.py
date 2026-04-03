"""
数据模型包

- backend.models.user      : Pydantic 数据模型（已有）
- backend.models.orm_models: SQLAlchemy ORM 模型

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

# Pydantic 模型（从 user.py 导出，保持向后兼容）
from backend.models.user import (
    SUBSCRIPTION_TIERS,
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    UserProfile,
    QuotaInfo,
    APIKeyResponse,
)

# ORM 模型
from backend.models.orm_models import (
    User as ORMUser,
    Project as ORMProject,
    GenerationJob as ORMGenerationJob,
    Order as ORMOrder,
    CardCode as ORMCardCode,
    EmailLog as ORMEmailLog,
    VerificationCode as ORMVerificationCode,
    AdminConfig as ORMAdminConfig,
)

__all__ = [
    # Pydantic
    "SUBSCRIPTION_TIERS",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "UserProfile",
    "QuotaInfo",
    "APIKeyResponse",
    # ORM
    "ORMUser",
    "ORMProject",
    "ORMGenerationJob",
    "ORMOrder",
    "ORMCardCode",
    "ORMEmailLog",
    "ORMVerificationCode",
    "ORMAdminConfig",
]
