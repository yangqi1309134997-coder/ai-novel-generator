"""
安全模块 - 密码加密和JWT令牌管理

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import os
import hmac
import hashlib
from pathlib import Path

from backend.core.settings import COMMERCIAL_PAYMENT_WEBHOOK_SECRET

# 密码加密上下文 — 兼容 pbkdf2_sha256 (auth_service) 和 bcrypt (旧版)
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def _load_persisted_secret_key() -> str:
    """从 ~/.ai_novel_generator/jwt_secret.key 加载持久化密钥，不存在则创建。"""
    key_path = Path.home() / ".ai_novel_generator" / "jwt_secret.key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()
    secret = secrets.token_urlsafe(32)
    key_path.write_text(secret, encoding="utf-8")
    return secret


# JWT配置 — 优先从持久化文件加载，保证重启后token仍有效
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or _load_persisted_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7天


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = _utcnow() + expires_delta
    else:
        expire = _utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    expire = _utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_api_key() -> str:
    """生成API Key"""
    return f"sk-{secrets.token_urlsafe(32)}"


def sign_payment_webhook(body: bytes, timestamp: str) -> str:
    """Generate a deterministic HMAC signature for payment webhooks."""
    payload = f"{timestamp}.".encode("utf-8") + body
    return hmac.new(
        COMMERCIAL_PAYMENT_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def verify_payment_webhook_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """Verify the HMAC signature used by commercial payment webhooks."""
    if not timestamp or not signature:
        return False
    expected = sign_payment_webhook(body, timestamp)
    return hmac.compare_digest(expected, signature)
