"""
SQLAlchemy 数据库连接模块

支持 SQLite（默认）和 PostgreSQL
使用 SQLAlchemy 2.x 风格（DeclarativeBase, Mapped, mapped_column）

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# 数据库路径与连接 URL
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB_PATH = _PROJECT_ROOT / "data" / "novel_platform.db"


def _build_database_url() -> str:
    """根据环境变量构建数据库连接 URL。

    优先使用 ``COMMERCIAL_DATABASE_URL`` 环境变量（完整的 SQLAlchemy URL）。
    如果未设置，则回退到 ``COMMERCIAL_DB_PATH`` 或默认 SQLite 路径。
    """
    explicit_url = os.getenv("COMMERCIAL_DATABASE_URL", "").strip()
    if explicit_url:
        return explicit_url

    db_path = os.getenv("COMMERCIAL_DB_PATH", "").strip()
    if db_path:
        resolved = Path(db_path).expanduser()
    else:
        resolved = _DEFAULT_DB_PATH

    # 确保父目录存在
    resolved.parent.mkdir(parents=True, exist_ok=True)

    # SQLite URL 需要三个斜杠（Windows 路径用正斜号）
    return f"sqlite:///{resolved.as_posix()}"


DATABASE_URL: str = _build_database_url()

# ---------------------------------------------------------------------------
# Engine & Session
# ---------------------------------------------------------------------------

engine: Engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    # SQLite 不支持池化，使用 StaticPool 避免多线程问题
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# SQLite 外键支持
# ---------------------------------------------------------------------------

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """为 SQLite 连接启用外键约束。"""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """SQLAlchemy 2.x 声明式基类。"""
    pass


# ---------------------------------------------------------------------------
# 依赖注入
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：提供数据库 session 并在请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------

def init_db() -> None:
    """创建所有数据表（如果不存在）。

    应在应用启动时调用一次。
    """
    # 延迟导入，确保所有 ORM 模型都已注册到 Base.metadata
    import backend.models.orm_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
