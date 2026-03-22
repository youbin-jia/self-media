# backend/app/api/video.py
"""Video API Routes"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.project import Project
from app.tasks.video_tasks import synthesize_video_task
from app.config import settings
from app.services.video_shot_timeline import (
    load_project_materials_for_video,
    visual_shots_from_project_meta,
)

router = APIRouter()


def _wan_ckpt_dir_populated(ckpt: str) -> bool:
    if not ckpt:
        return False
    path = Path(ckpt)
    if not path.is_dir():
        return False
    try:
        return any(path.iterdir())
    except OSError:
        return False


@router.get("/pipeline-env")
async def get_video_pipeline_environment() -> Dict[str, Any]:
    """
    返回视频合成 / 通义万相 Wan I2V 相关环境状态（不含密钥），供前端展示与自检。
    """
    from app.services.wan_video import wan_i2v_available

    ckpt = getattr(settings, "WAN_I2V_CKPT_DIR", None) or ""
    repo = getattr(settings, "WAN_I2V_REPO_DIR", None) or ""
    ckpt_ok = _wan_ckpt_dir_populated(ckpt)
    repo_ok = bool(repo and (Path(repo) / "generate.py").is_file())

    return {
        "wan_i2v_enabled": bool(getattr(settings, "WAN_I2V_ENABLED", False)),
        "wan_i2v_ready": wan_i2v_available(),
        "wan_i2v_mode": getattr(settings, "WAN_I2V_MODE", "subprocess") or "subprocess",
        "wan_endpoint_configured": bool(getattr(settings, "WAN_I2V_ENDPOINT", None)),
        "wan_repo_dir_configured": bool(repo),
        "wan_repo_has_generate_py": repo_ok,
        "wan_ckpt_dir_configured": bool(ckpt),
        "wan_ckpt_dir_populated": ckpt_ok,
        "wan_task": getattr(settings, "WAN_I2V_TASK", "i2v-14B"),
        "wan_size": getattr(settings, "WAN_I2V_SIZE", "1280*720"),
        "default_ai_image_provider": settings.DEFAULT_AI_GENERATION_PROVIDER,
        "data_dir": settings.DATA_DIR,
        "hints": _pipeline_env_hints(
            wan_ready=wan_i2v_available(),
            ckpt_ok=ckpt_ok,
            repo_ok=repo_ok,
        ),
    }


def _pipeline_env_hints(*, wan_ready: bool, ckpt_ok: bool, repo_ok: bool) -> List[str]:
    hints: List[str] = []
    if not getattr(settings, "WAN_I2V_ENABLED", False):
        hints.append("WAN_I2V_ENABLED 未开启：分镜时间轴将使用静图/DALL·E，不走通义万相 I2V。")
        return hints
    mode = (getattr(settings, "WAN_I2V_MODE", None) or "subprocess").lower()
    if mode == "http":
        if not getattr(settings, "WAN_I2V_ENDPOINT", None):
            hints.append("HTTP 模式需配置 WAN_I2V_ENDPOINT，并启动 scripts/wan2.1/start_wan_sidecar.sh。")
        elif not wan_ready:
            hints.append("侧车地址已配置但 wan_i2v_ready=false，请检查侧车 /health 与权重目录。")
    else:
        if not repo_ok:
            hints.append("subprocess 模式需要 WAN_I2V_REPO_DIR 指向含 generate.py 的 Wan2.1 克隆。")
        if not ckpt_ok:
            hints.append("请下载权重到 WAN_I2V_CKPT_DIR（见 docs/WAN2.1_LOCAL.md）。")
    if wan_ready:
        hints.append(
            "通义万相 I2V 已就绪：每镜需先有参考图（本地图/视频）；"
            "视频步会自动合并数据库「采集素材」与 metadata.materials，再按需调用 I2V。"
        )
    if mode == "http":
        hints.append(
            "HTTP 模式：权重在「侧车」机器上配置即可；主 API 上的「权重目录未配」可忽略。"
        )
    return hints


class SynthesizeRequest(BaseModel):
    """Request model for video synthesis"""
    project_id: str
    platforms: List[str] = ["horizontal"]  # Support multi-platform export


class SynthesizeResponse(BaseModel):
    """Response model for video synthesis"""
    task_id: str
    project_id: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    task_id: str
    status: str
    progress: int
    message: str
    result: Dict[str, Any] = {}


@router.post("/synthesize", response_model=SynthesizeResponse, status_code=202)
async def trigger_synthesis(
    request: SynthesizeRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger video synthesis for a project

    Args:
        request: Synthesis request with project_id
        db: Database session

    Returns:
        Task ID and project ID for tracking

    Raises:
        HTTPException: 404 if project not found, 400 if project not ready
    """
    # Check if project exists
    project = db.query(Project).filter(Project.id == request.project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 与 execute 视频步一致：合并 DB 素材；有视觉分镜时可无 metadata.materials
    metadata = dict(project.project_metadata or {})
    materials = load_project_materials_for_video(db, request.project_id, metadata)
    shots = visual_shots_from_project_meta(metadata)

    if not materials and not shots:
        raise HTTPException(
            status_code=400,
            detail="项目无可用素材且无视觉分镜。请先采集素材或完成视觉规划后再合成。"
        )

    # Trigger Celery task
    task = synthesize_video_task.delay(request.project_id, request.platforms)

    return SynthesizeResponse(
        task_id=task.id,
        project_id=request.project_id,
        message="Video synthesis task started"
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a video synthesis task

    Args:
        task_id: The Celery task ID

    Returns:
        Task status with progress information
    """
    from app.tasks.celery_app import celery_app

    # Get task result
    task_result = celery_app.AsyncResult(task_id)

    # Prepare response
    response = TaskStatusResponse(
        task_id=task_id,
        status=task_result.status,
        progress=0,
        message="",
        result={}
    )

    if task_result.status == "PENDING":
        response.message = "Task is waiting to start"
        response.progress = 0

    elif task_result.status == "PROGRESS":
        # Get progress info from task state
        info = task_result.info or {}
        response.progress = info.get("progress", 0)
        response.message = info.get("status", "In progress...")

    elif task_result.status == "SUCCESS":
        response.progress = 100
        response.message = "Task completed successfully"
        response.result = task_result.result or {}

    elif task_result.status == "FAILURE":
        response.message = "Task failed"
        response.result = {
            "error": "An error occurred during video synthesis. Please check logs for details."
        }

    else:
        response.message = f"Task status: {task_result.status}"

    return response
