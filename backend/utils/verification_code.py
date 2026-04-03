"""
验证码工具模块

提供验证码生成与过期检查功能。
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timezone


def generate_code(length: int = 6) -> str:
    """生成指定位数的数字验证码。

    Args:
        length: 验证码长度，默认6位。

    Returns:
        纯数字验证码字符串。
    """
    return "".join(random.choices(string.digits, k=length))


def is_code_expired(expires_at: datetime) -> bool:
    """检查验证码是否已过期。

    Args:
        expires_at: 验证码的过期时间（带时区信息）。

    Returns:
        True 表示已过期，False 表示仍有效。
    """
    now = datetime.now(timezone.utc)
    # 如果 expires_at 没有时区信息，假定其为 UTC
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now >= expires_at
