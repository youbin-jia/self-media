"""按视觉规划分镜构建视频合成时间轴（切素材 / AI 生图 / Wan I2V / 占位）。"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.services.ai_generation import get_manager
from app.services.wan_video import generate_i2v_clip_async, wan_i2v_available

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

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


def load_project_materials_for_video(
    db: "Session",
    project_id: str,
    project_meta: dict,
) -> List[dict]:
    """
    合并 metadata.materials 与数据库 Material 表。

    采集素材 API 只写入 ORM 表，历史上未同步到 project_metadata，
    导致视频步读不到素材、分镜全占位且通义 I2V 从未被调用。
    """
    from app.models.material import Material

    meta_norm = normalize_materials_for_video(project_meta.get("materials"))
    rows = (
        db.query(Material)
        .filter(Material.project_id == project_id)
        .order_by(Material.created_at.asc())
        .all()
    )
    db_norm = normalize_materials_for_video(
        [
            {
                "local_path": m.local_path,
                "source_url": m.source_url,
                "material_type": m.material_type or m.type,
            }
            for m in rows
        ]
    )

    seen: set[str] = set()
    merged: List[dict] = []

    def _add(m: dict) -> None:
        lp = str(m.get("local_path") or "").strip()
        su = str(m.get("source_url") or "").strip()
        key = lp if lp else su
        if not key:
            return
        if key in seen:
            return
        seen.add(key)
        merged.append(m)

    for m in meta_norm:
        _add(m)
    for m in db_norm:
        _add(m)
    return merged


def _count_usable_local_files(materials: List[dict]) -> int:
    n = 0
    for m in materials:
        p = m.get("local_path") or m.get("source_url")
        if p and os.path.isfile(str(p)):
            n += 1
    return n


async def _fetch_http_material_to_local(url: str, dest_dir: Path, slot: int) -> Optional[str]:
    """将 http(s) 素材下载到本地缓存，供分镜与 I2V 使用。缓存键仅依赖 URL。"""
    logger.debug("fetch material slot=%s", slot)
    u = str(url).strip()
    if not u.lower().startswith(("http://", "https://")):
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(u.encode("utf-8")).hexdigest()[:28]

    def _pick_ext(content: bytes) -> str:
        if content.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            return ".webp"
        if len(content) >= 8 and content[4:8] == b"ftyp":
            return ".mp4"
        lu = u.lower()
        for suf in (".png", ".webp", ".jpeg", ".jpg", ".gif", ".mp4", ".webm", ".mov"):
            if lu.split("?", 1)[0].endswith(suf):
                return ".jpg" if suf == ".jpeg" else suf
        return ".jpg"

    for p in dest_dir.glob(f"fetch_{digest}.*"):
        if p.is_file() and p.suffix != ".part" and p.stat().st_size > 0:
            return str(p.resolve())

    part = dest_dir / f"fetch_{digest}.part"
    try:
        async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
            r = await client.get(u)
            r.raise_for_status()
            body = r.content
        ext = _pick_ext(body[:64] if body else b"")
        final = dest_dir / f"fetch_{digest}{ext}"
        final.write_bytes(body)
        part.unlink(missing_ok=True)
        return str(final.resolve())
    except Exception as exc:
        logger.warning("下载远程素材失败 url=%s err=%s", u[:120], exc)
        part.unlink(missing_ok=True)
        return None


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
    on_shot_progress: Optional[Callable[[int, int, str], Awaitable[None]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
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
    fetch_dir = Path(settings.DATA_DIR) / "video_material_fetch" / (project_id or "default")

    total_shots = len(shots)
    for idx, shot in enumerate(shots):
        dur = float(shot.get("duration_sec") or 5)
        dur = max(0.5, min(120.0, dur))
        prompt = shot_to_image_prompt(shot)
        sn = shot.get("shot_no", idx + 1)

        if on_shot_progress:
            await on_shot_progress(
                idx + 1,
                total_shots,
                f"镜头 {sn}：解析素材与画面来源…",
            )

        path: Optional[str] = None
        from_generation = False

        if materials:
            mat = materials[idx % len(materials)]
            p = mat.get("local_path") or mat.get("source_url")
            if p:
                ps = str(p).strip()
                if os.path.isfile(ps):
                    path = ps
                elif ps.lower().startswith(("http://", "https://")):
                    if on_shot_progress:
                        await on_shot_progress(
                            idx + 1,
                            total_shots,
                            f"镜头 {sn}：下载远程素材…",
                        )
                    path = await _fetch_http_material_to_local(ps, fetch_dir, idx)

        if path and _is_video_file(path):
            if on_shot_progress:
                await on_shot_progress(
                    idx + 1,
                    total_shots,
                    f"镜头 {sn}：使用本地视频素材（裁切时长）…",
                )
            stats["from_material"] += 1
            timeline.append({"path": path, "duration_sec": dur})
            continue

        if not path and can_gen and mgr is not None:
            if on_shot_progress:
                await on_shot_progress(
                    idx + 1,
                    total_shots,
                    f"镜头 {sn}：AI 生成参考图…",
                )
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
            if on_shot_progress:
                await on_shot_progress(
                    idx + 1,
                    total_shots,
                    f"镜头 {sn}：通义万相 I2V 生成视频（较慢，请稍候）…",
                )
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

    usable_local = _count_usable_local_files(materials)
    hints: List[str] = []
    if total_shots > 0 and stats["placeholder"] == total_shots:
        if not materials:
            hints.append(
                "未找到任何素材：已合并 metadata.materials 与数据库采集记录。"
                "请先在工作流中执行「素材采集」，或配置 OPENAI_API_KEY 以启用 DALL·E 参考图。"
            )
        elif usable_local == 0 and not any(
            str((m.get("local_path") or m.get("source_url") or "")).lower().startswith(
                ("http://", "https://")
            )
            for m in materials
        ):
            hints.append(
                "有素材条目但本地文件均不存在（路径可能过期）。请重新采集素材或检查 DATA_DIR 下文件是否仍在。"
            )
        elif wan_on and not can_gen and stats["generated"] == 0:
            hints.append(
                "通义万相 I2V 是「图生视频」：需要每张分镜的参考图。"
                "当前未配置可用的 AI 生图（如 OPENAI_API_KEY / DALL·E），且没有可用本地图，故无法调用 I2V。"
            )
        elif can_gen and stats["generated"] == 0 and usable_local == 0:
            hints.append(
                "已配置生图，但本任务未得到任何参考图（可能 API 失败）。请查看后端日志中的「分镜 AI 生图失败」。"
            )

    stats["diagnostics"] = {
        "ai_image_generation_available": can_gen,
        "wan_i2v_available": wan_on,
        "material_entries": len(materials),
        "usable_local_material_files_before_fetch": usable_local,
        "hints": hints,
    }

    return timeline, stats
