"""
卡密生成器

使用 ``secrets`` 模块生成安全随机卡密，格式：PREFIX-XXXXXXXX-XXXXXXXX。
支持单个和批量生成。

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services.auth_service import SUBSCRIPTION_TIERS

# 卡密前缀段之后的字符集（大写字母 + 数字，排除容易混淆的 0/O、1/I/L）
_SAFE_CHARS = "".join(c for c in (string.ascii_uppercase + string.digits) if c not in "0O1IL")


def _random_segment(length: int = 8) -> str:
    """生成一个由安全随机字符组成的指定长度字符串。"""
    return "".join(secrets.choice(_SAFE_CHARS) for _ in range(length))


def generate_card_code(
    *,
    prefix: str = "NV",
    tier: str = "basic",
    days: int = 30,
) -> dict[str, Any]:
    """生成单个卡密。

    Args:
        prefix: 卡密前缀，默认 ``NV``。
        tier: 会员等级，``basic`` 或 ``pro``。
        days: 有效天数，默认 30。

    Returns:
        包含卡密信息的字典，键包括：
        ``code``, ``tier``, ``days``, ``value_yuan``,
        ``expires_at``（ISO 格式字符串，基于 days 推算）。
    """
    if tier not in SUBSCRIPTION_TIERS:
        raise ValueError(f"无效的会员等级: {tier!r}，有效值: {list(SUBSCRIPTION_TIERS.keys())}")
    if days <= 0:
        raise ValueError("有效天数必须为正整数")

    # 格式: PREFIX-XXXXXXXX-XXXXXXXX
    code = f"{prefix.upper()}-{_random_segment(8)}-{_random_segment(8)}"

    # 价格参照 SUBSCRIPTION_TIERS 配置，按月（30天）折算
    tier_price = SUBSCRIPTION_TIERS[tier]["price"]
    value_yuan = round(tier_price * days / 30, 2)

    # 卡密自身过期时间：从现在起 days 天后（这里取一个较长窗口，给管理员留出发放时间）
    expires_at = datetime.now(timezone.utc) + timedelta(days=days + 90)

    return {
        "code": code,
        "tier": tier,
        "days": days,
        "value_yuan": value_yuan,
        "expires_at": expires_at.isoformat(),
    }


def generate_batch(
    count: int,
    *,
    prefix: str = "NV",
    tier: str = "basic",
    days: int = 30,
) -> list[dict[str, Any]]:
    """批量生成卡密。

    Args:
        count: 生成数量，必须 >= 1。
        prefix: 卡密前缀。
        tier: 会员等级。
        days: 有效天数。

    Returns:
        卡密字典列表。
    """
    if count < 1:
        raise ValueError("生成数量必须 >= 1")
    if count > 1000:
        raise ValueError("单次批量生成上限为 1000 条")

    # 使用集合去重（极小概率重复，但安全起见）
    results: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    while len(results) < count:
        card = generate_card_code(prefix=prefix, tier=tier, days=days)
        if card["code"] not in seen_codes:
            seen_codes.add(card["code"])
            results.append(card)

    return results
