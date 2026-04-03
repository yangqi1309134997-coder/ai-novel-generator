"""
Background job management routes.

包含：
- GET    /api/jobs                  — 列出任务
- GET    /api/jobs/{job_id}         — 获取任务详情
- DELETE /api/jobs/{job_id}         — 删除任务
- POST   /api/jobs/full-generate    — 创建全本生成任务
- POST   /api/jobs/{job_id}/retry   — 重试任务

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.routers.auth import get_current_user
from backend.services.auth_service import auth_service
from project_manager import ProjectManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

project_root = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Pydantic 请求模型
# ---------------------------------------------------------------------------

class FullGenerationJobRequest(BaseModel):
    title: str
    genre: str
    character_setting: str = ""
    world_setting: str = ""
    plot_idea: str = ""
    chapter_count: int = Field(default=50, ge=1, le=500)
    export_format: str = "txt"


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _is_admin_user(user: Dict[str, Any]) -> bool:
    return bool(user.get("is_admin"))


def _serialize_job(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": job["id"],
        "status": job["status"],
        "title": job["title"],
        "project_id": job.get("project_id"),
        "progress": job.get("progress", 0),
        "current_step": job.get("current_step", ""),
        "message": job.get("message", ""),
        "export_format": job.get("export_format", "txt"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "error": job.get("error", ""),
        "download_ready": bool(job.get("project_id") and job["status"] == "completed"),
        "retry_available": job["status"] == "failed",
    }


def _filter_jobs_for_user(jobs: List[Dict[str, Any]], user: Dict[str, Any]) -> List[Dict[str, Any]]:
    if _is_admin_user(user):
        return jobs
    return [job for job in jobs if job.get("owner_user_id") == user["user_id"]]


def _ensure_job_access(job: Optional[Dict[str, Any]], user: Dict[str, Any]) -> Dict[str, Any]:
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if _is_admin_user(user):
        return job
    if job.get("owner_user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="你无权访问该任务")
    return job


def _require_generation_access(user: Dict[str, Any]) -> None:
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


def _get_prompt_manager():
    from src.core.prompts import PromptManager

    return PromptManager(project_root / "config")


# ---------------------------------------------------------------------------
# JobStore
# ---------------------------------------------------------------------------

class JobStore:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._storage_path = project_root / "backend" / "cache" / "jobs.json"
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
            jobs = raw.get("jobs", {})
            for job in jobs.values():
                if job.get("status") in {"queued", "running"}:
                    job["status"] = "failed"
                    job["current_step"] = "interrupted"
                    job["error"] = "服务重启，任务已中断，请重新提交"
                    job["message"] = "服务重启，任务已中断，请重新提交"
            self._jobs = jobs
        except Exception as exc:
            logger.warning(f"加载任务缓存失败: {exc}")
            self._jobs = {}

    def _save(self) -> None:
        try:
            payload = {"jobs": self._jobs, "updated_at": datetime.now().isoformat()}
            self._storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"保存任务缓存失败: {exc}")

    def create(self, payload: FullGenerationJobRequest, owner_user_id: str = "", owner_email: str = "") -> Dict[str, Any]:
        job_id = uuid.uuid4().hex
        now = datetime.now().isoformat()
        request_payload = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        job = {
            "id": job_id,
            "status": "queued",
            "title": payload.title,
            "project_id": None,
            "progress": 0,
            "current_step": "queued",
            "message": "任务已进入队列",
            "export_format": payload.export_format,
            "created_at": now,
            "updated_at": now,
            "error": "",
            "owner_user_id": owner_user_id,
            "owner_email": owner_email,
            "request_payload": request_payload,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._save()
        return job

    def update(self, job_id: str, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            self._jobs[job_id].update(fields)
            self._jobs[job_id]["updated_at"] = datetime.now().isoformat()
            self._save()
            return dict(self._jobs[job_id])

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            jobs = [dict(job) for job in self._jobs.values()]
        jobs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return jobs

    def delete(self, job_id: str) -> bool:
        with self._lock:
            if job_id not in self._jobs:
                return False
            del self._jobs[job_id]
            self._save()
            return True


job_store = JobStore()


# ---------------------------------------------------------------------------
# 后台生成逻辑
# ---------------------------------------------------------------------------

def _run_full_generation_job(job_id: str, payload: FullGenerationJobRequest) -> None:
    from src.core.coherence import CharacterTracker, PlotManager, WorldDatabase
    from src.ui.features.auto_generation import AutoNovelGenerator

    try:
        job_store.update(job_id, status="running", current_step="outline", message="正在生成大纲", progress=5)
        job_meta = job_store.get(job_id) or {}
        api_client = _get_runtime_api_client()
        prompt_manager = _get_prompt_manager()

        bootstrap_generator = AutoNovelGenerator(
            api_client=api_client,
            prompt_manager=prompt_manager,
            coherence_system={"character_tracker": None, "plot_manager": None, "world_db": None},
            project_dir=project_root / "projects",
        )

        success, outline_message, outline = bootstrap_generator.generate_outline(
            title=payload.title,
            genre=payload.genre,
            character_setting=payload.character_setting,
            world_setting=payload.world_setting,
            plot_idea=payload.plot_idea,
            chapter_count=payload.chapter_count,
        )
        if not success:
            job_store.update(job_id, status="failed", current_step="outline", error=outline_message, message=outline_message, progress=100)
            return

        project_id, create_message = ProjectManager.create_project(
            title=payload.title,
            genre=payload.genre,
            character_setting=payload.character_setting,
            world_setting=payload.world_setting,
            plot_idea=payload.plot_idea,
            chapter_count=payload.chapter_count,
            owner_user_id=job_meta.get("owner_user_id", ""),
            owner_email=job_meta.get("owner_email", ""),
        )
        if not project_id:
            job_store.update(job_id, status="failed", current_step="project", error=create_message, message=create_message, progress=100)
            return

        project_data = ProjectManager.get_project(project_id)
        project_data["outline"] = outline
        ProjectManager.save_project(project_id, project_data)

        coherence_cache_dir = project_root / "cache" / "coherence"
        coherence_cache_dir.mkdir(parents=True, exist_ok=True)
        generator = AutoNovelGenerator(
            api_client=api_client,
            prompt_manager=prompt_manager,
            coherence_system={
                "character_tracker": CharacterTracker(project_id, coherence_cache_dir),
                "plot_manager": PlotManager(project_id, coherence_cache_dir),
                "world_db": WorldDatabase(project_id, coherence_cache_dir),
            },
            project_dir=project_root / "projects",
        )

        job_store.update(job_id, project_id=project_id, current_step="chapters", message="开始后台生成章节", progress=10)

        def progress_callback(current: int, total: int, step_message: str) -> None:
            chapter_progress = 10 + int((current / max(total, 1)) * 85)
            job_store.update(job_id, progress=min(chapter_progress, 95), current_step="chapters", message=step_message)

        success, final_message, _chapters = generator.generate_full_novel(
            project_id=project_id,
            outline=outline,
            progress_callback=progress_callback,
        )

        if not success:
            job_store.update(job_id, status="failed", current_step="chapters", error=final_message, message=final_message, progress=100)
            return

        job_store.update(
            job_id,
            status="completed",
            current_step="completed",
            message="整本小说生成完成，可直接下载",
            progress=100,
        )
    except HTTPException as exc:
        job_store.update(job_id, status="failed", current_step="error", error=str(exc.detail), message=str(exc.detail), progress=100)
    except Exception as exc:
        logger.error(f"后台生成任务失败: {exc}", exc_info=True)
        job_store.update(job_id, status="failed", current_step="error", error=str(exc), message=str(exc), progress=100)


# ---------------------------------------------------------------------------
# 路由端点
# ---------------------------------------------------------------------------

@router.get("")
async def list_jobs(
    job_status: Optional[str] = Query(default=None, alias="status"),
    user: dict = Depends(get_current_user),
):
    jobs = _filter_jobs_for_user(job_store.list(), user)
    if job_status:
        jobs = [j for j in jobs if j.get("status") == job_status]
    return {"success": True, "data": [_serialize_job(job) for job in jobs]}


@router.get("/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    job = _ensure_job_access(job_store.get(job_id), user)
    return {"success": True, "data": _serialize_job(job)}


@router.delete("/{job_id}")
async def delete_job(job_id: str, user: dict = Depends(get_current_user)):
    _ensure_job_access(job_store.get(job_id), user)
    success = job_store.delete(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True, "message": "任务已移除"}


@router.post("/full-generate")
async def create_full_generation_job(payload: FullGenerationJobRequest, user: dict = Depends(get_current_user)):
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")
    _require_generation_access(user)

    job = job_store.create(payload, owner_user_id=user["user_id"], owner_email=user["email"])
    worker = threading.Thread(target=_run_full_generation_job, args=(job["id"], payload), daemon=True)
    worker.start()
    return {"success": True, "message": "后台生成任务已提交", "data": _serialize_job(job)}


@router.post("/{job_id}/retry")
async def retry_job(job_id: str, user: dict = Depends(get_current_user)):
    _require_generation_access(user)
    job = _ensure_job_access(job_store.get(job_id), user)

    payload_data = job.get("request_payload")
    if not payload_data:
        raise HTTPException(status_code=400, detail="该任务缺少重试所需的原始参数")

    payload = FullGenerationJobRequest(**payload_data)
    new_job = job_store.create(payload, owner_user_id=user["user_id"], owner_email=user["email"])
    worker = threading.Thread(target=_run_full_generation_job, args=(new_job["id"], payload), daemon=True)
    worker.start()
    return {"success": True, "message": "任务已重新提交", "data": _serialize_job(new_job)}
