"""
AI小说生成器 - FastAPI主应用

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 添加项目根目录到Python路径，以便导入src模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.settings import (
    COMMERCIAL_BACKEND_BIND_HOST,
    COMMERCIAL_BACKEND_PORT,
    COMMERCIAL_CORS_ORIGINS,
)
from backend.core.database import init_db


# ---------------------------------------------------------------------------
# Lifespan（替代 @app.on_event("startup")）
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    # ---- startup ----
    init_db()
    yield
    # ---- shutdown ----


# ---------------------------------------------------------------------------
# FastAPI 应用
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Novel Generator API",
    description="智能小说生成器后端服务 - 基于雪花写作法",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=COMMERCIAL_CORS_ORIGINS,
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ---------------------------------------------------------------------------
# 注册路由
# ---------------------------------------------------------------------------

from backend.routers import public, auth, projects, jobs, generation, tools, prompts, settings, payment, admin

for _router in [
    public.router,
    auth.router,
    projects.router,
    jobs.router,
    generation.router,
    tools.router,
    prompts.router,
    settings.router,
    payment.router,
    admin.router,
]:
    app.include_router(_router)


# ---------------------------------------------------------------------------
# 直接运行入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("AI Novel Generator API Server v6.0.0")

    uvicorn.run(
        app,
        host=COMMERCIAL_BACKEND_BIND_HOST,
        port=COMMERCIAL_BACKEND_PORT,
        log_level="info",
    )
