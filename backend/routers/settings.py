"""
Settings and API configuration routes.

包含：
- GET  /api/settings/api-config — 读取API配置
- POST /api/settings/api-config — 保存API配置
- GET  /api/providers           — 列出提供商
- POST /api/test-api            — 测试API连接

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.routers.auth import get_current_user, require_permission
from backend.services.audit_service import audit_service
from backend.services.auth_service import auth_service
from src.config.providers import PRESET_PROVIDERS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])

project_root = Path(__file__).resolve().parents[2]

USER_CONFIG_PATH = project_root / "config" / "user_config.json"


# ---------------------------------------------------------------------------
# Pydantic 请求模型
# ---------------------------------------------------------------------------

class APIConfig(BaseModel):
    """API配置"""
    provider: str
    api_key: str
    base_url: Optional[str] = ""
    model: str


class SaveAPIConfigRequest(BaseModel):
    """保存API配置请求"""
    provider: str
    api_key: str
    base_url: Optional[str] = ""
    model: str
    enabled: bool = True


# ---------------------------------------------------------------------------
# 辅助函数（被多个模块引用，因此在此模块中定义）
# ---------------------------------------------------------------------------

def _load_user_config() -> Dict[str, Any]:
    """加载用户配置"""
    if not USER_CONFIG_PATH.exists():
        return {"providers": []}

    with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_user_config(config: Dict[str, Any]) -> None:
    """保存用户配置"""
    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _mask_secret(secret: str) -> str:
    """掩码敏感信息"""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


def _serialize_provider_config(provider: Dict[str, Any]) -> Dict[str, Any]:
    """序列化提供商配置给前端"""
    return {
        "provider": provider.get("provider_id", ""),
        "base_url": provider.get("base_url", ""),
        "model": provider.get("model", ""),
        "enabled": provider.get("enabled", True),
        "has_api_key": bool(provider.get("api_key")),
        "api_key_masked": _mask_secret(provider.get("api_key", "")),
    }


# ---------------------------------------------------------------------------
# 路由端点
# ---------------------------------------------------------------------------

@router.get("/api/settings/api-config")
async def get_api_config(user: dict = Depends(get_current_user)):
    """读取当前API配置"""
    try:
        config = _load_user_config()
        providers = config.get("providers", [])
        if auth_service.has_permission_for_role(user.get("role", "customer"), "api_config.view"):
            data = _serialize_provider_config(providers[0]) if providers else None
        else:
            data = {
                "has_api_key": bool(providers and providers[0].get("api_key")),
                "enabled": bool(providers and providers[0].get("enabled", True)),
            }
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"读取API配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/settings/api-config")
async def save_api_config(config: SaveAPIConfigRequest, user: dict = Depends(require_permission("api_config.edit"))):
    """保存API配置"""
    try:
        existing_config = _load_user_config()
        existing_providers = existing_config.get("providers", [])
        existing_api_key = existing_providers[0].get("api_key", "") if existing_providers else ""

        provider_config = {
            "provider_id": config.provider,
            "api_key": config.api_key or existing_api_key,
            "base_url": config.base_url or "",
            "model": config.model,
            "enabled": config.enabled,
        }
        _save_user_config({"providers": [provider_config]})
        audit_service.record(
            "admin.api_config.save",
            actor=user,
            status="success",
            target_type="api_provider",
            target_label=config.provider,
            message="接口配置已保存",
            metadata={
                "provider": config.provider,
                "model": config.model,
                "base_url": config.base_url or "",
                "enabled": config.enabled,
                "api_key_supplied": bool(config.api_key),
            },
        )

        return {
            "success": True,
            "message": "API配置已保存",
            "data": _serialize_provider_config(provider_config),
        }
    except Exception as e:
        logger.error(f"保存API配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/providers")
async def list_providers(_user: dict = Depends(require_permission("api_config.view"))):
    """列出可选API提供商"""
    providers = []
    for provider in PRESET_PROVIDERS.values():
        providers.append({
            "id": provider.id,
            "name": provider.name,
            "base_url": provider.base_url,
            "default_model": provider.default_model,
            "models": provider.models,
            "requires_key": provider.requires_key,
            "icon": provider.icon,
            "description": provider.description,
        })

    providers.sort(key=lambda item: item["name"])
    return {"success": True, "data": providers}


@router.post("/api/test-api")
async def test_api_connection(config: APIConfig, user: dict = Depends(require_permission("api_config.test"))):
    """测试API连接"""
    audit_status = "success"
    audit_message = "接口连接测试成功"
    try:
        from src.api import create_api_client

        existing_config = _load_user_config()
        existing_providers = existing_config.get("providers", [])
        existing_api_key = existing_providers[0].get("api_key", "") if existing_providers else ""

        # 构建provider_configs列表
        provider_config = {
            "provider_id": config.provider,
            "api_key": config.api_key or existing_api_key,
            "base_url": config.base_url or "",
            "model": config.model,
            "enabled": True,
        }

        api_client = create_api_client([provider_config])

        # 简单测试
        result = api_client.generate([
            {"role": "user", "content": "你好"}
        ], max_tokens=10)

        return {
            "success": True,
            "message": "API连接成功",
            "result": result[:100] if result else "",
        }

    except Exception as e:
        logger.error(f"API测试失败: {e}")
        audit_status = "failed"
        audit_message = str(e)
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        audit_service.record(
            "admin.api_config.test",
            actor=user,
            status=audit_status,
            target_type="api_provider",
            target_label=config.provider,
            message=audit_message,
            metadata={
                "provider": config.provider,
                "model": config.model,
                "base_url": config.base_url or "",
                "api_key_supplied": bool(config.api_key),
            },
        )
