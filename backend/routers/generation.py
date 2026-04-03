"""
Novel generation routes (outline, snowflake, blueprint).

包含：
- POST /api/quick/outline         — 快速生成大纲
- POST /api/snowflake/architecture — 雪花架构
- POST /api/snowflake/blueprint    — 章节蓝图
- POST /api/parse-blueprint        — 解析蓝图

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.routers.auth import get_current_user
from backend.services.auth_service import auth_service
from project_manager import ProjectManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generation"])

project_root = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Pydantic 请求模型
# ---------------------------------------------------------------------------

class QuickStartRequest(BaseModel):
    """快速模式请求"""
    title: str
    genre: str
    character_setting: str = ""
    world_setting: str = ""
    plot_idea: str = ""
    chapter_count: int = Field(default=50, ge=1, le=500)


class SnowflakeConfigRequest(BaseModel):
    """雪花写作法配置请求"""
    topic: str
    genre: str
    number_of_chapters: int = Field(default=50, ge=1, le=500)
    word_number: int = Field(default=3000, ge=500, le=10000)
    user_guidance: str = ""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100, le=32000)


class BlueprintRequest(BaseModel):
    """章节蓝图请求"""
    architecture: Dict[str, str]
    number_of_chapters: int = Field(ge=1, le=500)
    existing_blueprint: str = ""


class ParseBlueprintRequest(BaseModel):
    """蓝图解析请求"""
    blueprint: str


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _require_generation_access(user: Dict[str, any]) -> None:
    allowed, reason = auth_service.can_generate(user["user_id"])
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)


def _get_runtime_api_client():
    from src.api import create_api_client

    from backend.routers.settings import _load_user_config
    config = _load_user_config()
    providers = config.get("providers", [])
    if not providers:
        raise HTTPException(status_code=400, detail="请先在设置中配置 API")
    return create_api_client(providers)


# ---------------------------------------------------------------------------
# 路由端点
# ---------------------------------------------------------------------------

@router.post("/api/quick/outline")
async def generate_quick_outline(payload: QuickStartRequest, user: dict = Depends(get_current_user)):
    """快速模式：生成大纲并创建项目"""
    try:
        _require_generation_access(user)
        from src.api import get_api_client
        from src.core.prompts import PromptManager
        from src.ui.features.auto_generation import AutoNovelGenerator

        api_client = get_api_client()
        if not api_client:
            raise HTTPException(status_code=400, detail="请先在系统设置中配置 API")

        prompt_manager = PromptManager(project_root / "config")
        generator = AutoNovelGenerator(
            api_client=api_client,
            prompt_manager=prompt_manager,
            coherence_system={
                "character_tracker": None,
                "plot_manager": None,
                "world_db": None,
            },
            project_dir=project_root / "projects",
        )

        success, message, outline = generator.generate_outline(
            title=payload.title,
            genre=payload.genre,
            character_setting=payload.character_setting,
            world_setting=payload.world_setting,
            plot_idea=payload.plot_idea,
            chapter_count=payload.chapter_count,
        )

        project_id, create_message = ProjectManager.create_project(
            title=payload.title,
            genre=payload.genre,
            character_setting=payload.character_setting,
            world_setting=payload.world_setting,
            plot_idea=payload.plot_idea,
            chapter_count=payload.chapter_count,
            owner_user_id=user["user_id"],
            owner_email=user["email"],
        )

        if not project_id:
            raise HTTPException(status_code=400, detail=create_message)

        project_data = ProjectManager.get_project(project_id)
        project_data["outline"] = outline if success else []
        ProjectManager.save_project(project_id, project_data)

        response_message = "快速模式已生成大纲并创建项目" if success else "项目已创建，但自动大纲生成失败，可继续在项目中心或规划模式中完善"
        return {
            "success": True,
            "message": response_message,
            "data": {
                "project": project_data,
                "outline": outline if success else [],
                "outline_error": "" if success else message,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"快速模式生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/snowflake/architecture")
async def generate_snowflake_architecture(config: SnowflakeConfigRequest, user: dict = Depends(get_current_user)):
    """生成雪花写作法架构"""
    try:
        _require_generation_access(user)
        from src.core.prompts.snowflake import (
            SnowflakeManager,
            SnowflakeConfig,
            create_snowflake_manager,
        )
        from src.api import get_api_client

        # 获取API客户端
        api_client = get_api_client()
        if not api_client:
            raise HTTPException(
                status_code=400,
                detail="请先配置API"
            )

        # 创建配置
        snowflake_config = SnowflakeConfig(
            topic=config.topic,
            genre=config.genre,
            number_of_chapters=config.number_of_chapters,
            word_number=config.word_number,
            user_guidance=config.user_guidance,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        # 创建管理器
        manager = create_snowflake_manager(api_client)

        # 生成架构
        success, message, architecture = manager.generate_architecture(snowflake_config)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": "架构生成成功",
            "data": architecture.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"架构生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/snowflake/blueprint")
async def generate_chapter_blueprint(payload: BlueprintRequest, user: dict = Depends(get_current_user)):
    """生成章节蓝图"""
    try:
        _require_generation_access(user)
        from src.core.prompts.snowflake import (
            SnowflakeManager,
            SnowflakeConfig,
            SnowflakeArchitecture,
            create_snowflake_manager,
        )
        from src.api import get_api_client

        # 获取API客户端
        api_client = get_api_client()
        if not api_client:
            raise HTTPException(
                status_code=400,
                detail="请先配置API"
            )

        # 创建架构对象
        arch = SnowflakeArchitecture(**payload.architecture)

        # 创建配置
        config = SnowflakeConfig(
            number_of_chapters=payload.number_of_chapters
        )

        # 创建管理器
        manager = create_snowflake_manager(api_client)

        # 生成蓝图
        success, message, blueprint = manager.generate_chapter_blueprint(
            config,
            arch,
            payload.existing_blueprint
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": "章节蓝图生成成功",
            "data": {
                "blueprint": blueprint,
                "chapter_count": len(blueprint.split("第"))
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"蓝图生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/parse-blueprint")
async def parse_blueprint(payload: ParseBlueprintRequest):
    """解析章节蓝图"""
    try:
        from src.core.prompts.snowflake import parse_chapter_blueprint

        chapters = parse_chapter_blueprint(payload.blueprint)

        return {
            "success": True,
            "message": f"解析到 {len(chapters)} 个章节",
            "data": {
                "chapters": [ch.to_dict() for ch in chapters],
                "count": len(chapters)
            }
        }

    except Exception as e:
        logger.error(f"蓝图解析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
