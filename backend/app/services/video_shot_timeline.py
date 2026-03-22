"""按视觉规划分镜构建视频合成时间轴（切素材 / AI 生图 / Wan I2V / 占位）。"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.services.ai_generation import get_manager
from app.services.wan_video import generate_i2v_clip_async, wan_i2v_available

logger = logging.getLogger(__name__)

_IMAGE_SUFFIX = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
_VIDEO_SUFFIX = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}


def _is_image_file(path: str) -> bool:
    return Path(path).suffix.lower() in _IMAGE_SUFFIX


def _is_video_file(path: str) -> bool:
    return Path(path).suffix.lower() in _VIDEO_SUFFIX


def normalize_materials_for_video(raw_materials: Optional[list]) -> List[dict]:
    """将项目 materials 规范为合成器可用的列表。"""
    normalized: List[dict] = []
    for item in raw_materials or []:
        if not isinstance(item, dict):
            continue
        path = item.get("local_path") or item.get("path") or item.get("source_url")
        if not path:
            continue
        normalized.append({
            "local_path": path,
            "source_url": item.get("source_url"),
            "material_type": item.get("material_type") or item.get("type")
        })
    return normalized


def visual_shots_from_project_meta(project_meta: dict) -> List[dict]:
    """读取视觉分镜：优先 metadata.visual_plan，其次 steps.visual.output。"""
    vp = project_meta.get("visual_plan") or {}
    raw = vp.get("shots")
    if isinstance(raw, list) and raw:
        cleaned = [s for s in raw if isinstance(s, dict)]
        if cleaned:
            return cleaned
    steps = project_meta.get("steps") or {}
    visual = steps.get("visual") or {}
    out = visual.get("output") or {}
    raw2 = out.get("shots")
    if isinstance(raw2, list) and raw2:
        return [s for s in raw2 if isinstance(s, dict)]
    return []


def shot_to_image_prompt(shot: dict) -> str:
    """用分镜的文案字段拼图像/视频生成提示词。"""
    parts: List[str] = []
    vd = str(shot.get("visual_description") or "").strip()
    if vd:
        parts.append(vd)
    ost = str(shot.get("on_screen_text") or "").strip()
    if ost:
        parts.append(f"字幕要点：{ost}")
    obj = str(shot.get("objective") or "").strip()
    if obj:
        parts.append(f"镜头目标：{obj}")
    ms = shot.get("material_suggestion") or []
    if isinstance(ms, list) and ms:
        parts.append(
            "素材参考：" + "，".join(str(x) for x in ms[:4] if str(x).strip())
        )
    core = " ".join(parts).strip() or "短视频实拍风格分镜画面，信息清晰"
    return (
        "短视频分镜画面，干净构图，无文字水印，适合口播与信息流视频："
        + core
    )[:1800]


def ai_image_generation_available() -> bool:
    try:
        get_manager().get_provider(settings.DEFAULT_AI_GENERATION_PROVIDER)
        return True
    except Exception:
        return False


async def build_visual_shot_timeline(
    shots: List[dict],
    materials: List[dict],
    *,
    project_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    按视觉规划分镜生成合成时间轴：每镜使用 duration_sec。
    - 素材为视频：直接裁切时长。
    - 素材为图或 DALL·E 出图：若启用 Wan I2V，优先生成短视频；否则静态图。
    - 无图：占位。
    """
    stats = {
        "from_material": 0,
        "generated": 0,
        "placeholder": 0,
        "wan_i2v": 0,
    }
    timeline: List[Dict[str, Any]] = []
    can_gen = ai_image_generation_available()
    mgr = get_manager() if can_gen else None
    wan_on = wan_i2v_available()
    cache_dir = Path(settings.DATA_DIR) / "wan_i2v_cache" / (project_id or "default")
    cache_dir.mkdir(parents=True, exist_ok=True)

    for idx, shot in enumerate(shots):
        dur = float(shot.get("duration_sec") or 5)
        dur = max(0.5, min(120.0, dur))
        prompt = shot_to_image_prompt(shot)

        path: Optional[str] = None
        from_generation = False

        if materials:
            mat = materials[idx % len(materials)]
            p = mat.get("local_path") or mat.get("source_url")
            if p and os.path.isfile(str(p)):
                path = str(p)

        if path and _is_video_file(path):
            stats["from_material"] += 1
            timeline.append({"path": path, "duration_sec": dur})
            continue

        if not path and can_gen and mgr is not None:
            try:
                res = await mgr.generate_image(
                    settings.DEFAULT_AI_GENERATION_PROVIDER,
                    prompt,
                    style="cinematic",
                    size=(1920, 1080),
                )
                ip = res.get("image_path") if isinstance(res, dict) else None
                if res and res.get("success") and ip and os.path.isfile(str(ip)):
                    path = str(ip)
                    from_generation = True
            except Exception as exc:
                logger.warning(
                    "分镜 AI 生图失败 shot=%s: %s", shot.get("shot_no"), exc
                )

        if path and _is_image_file(path) and wan_on:
            stem = f"{project_id or 'p'}_{idx}_{shot.get('shot_no', idx)}"
            vp = await generate_i2v_clip_async(
                image_path=path,
                prompt=prompt,
                cache_dir=cache_dir,
                stem=stem,
            )
            if vp:
                stats["wan_i2v"] += 1
                timeline.append({"path": vp, "duration_sec": dur})
                continue

        if path:
            if from_generation:
                stats["generated"] += 1
            else:
                stats["from_material"] += 1
            timeline.append({"path": path, "duration_sec": dur})
            continue

        stats["placeholder"] += 1
        timeline.append({"duration_sec": dur, "placeholder": True})

    return timeline, stats
