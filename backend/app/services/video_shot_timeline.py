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


def _shot_no_for_sort(shot: dict, list_index: int) -> int:
    try:
        sn = int(shot.get("shot_no") or 0)
        return sn if sn > 0 else list_index + 1
    except (TypeError, ValueError):
        return list_index + 1


def align_visual_shots_with_narrations(
    shots: List[dict], narrations: List[str]
) -> Tuple[List[dict], List[str]]:
    """
    按视觉规划 shot_no 排序，并与口播列表按下标对齐。
    视频合成第 i 个片段与视觉规划「镜头 shot_no」顺序一致。
    """
    n = len(shots)
    if n == 0:
        return [], []
    narr = list(narrations or []) + [""] * n
    narr = narr[:n]
    triples = [(i, shots[i], narr[i]) for i in range(n)]
    triples.sort(key=lambda t: (_shot_no_for_sort(t[1], t[0]), t[0]))
    return [t[1] for t in triples], [t[2] for t in triples]


def build_ltx2_shot_input_block(
    shot: dict, shot_index: int, narration_line: str
) -> str:
    """
    单镜 LTX2.0 输入文档块（与 POST /generate 的 prompt+narration+subtitle 语义对齐）。
    便于落库、排错与人工核对。
    """
    sn = shot.get("shot_no", shot_index + 1)
    dur = float(shot.get("duration_sec") or 5)
    vd = str(shot.get("visual_description") or "").strip()
    cam = str(shot.get("camera_language") or "").strip()
    ost = str(shot.get("on_screen_text") or "").strip()
    obj = str(shot.get("objective") or "").strip()
    nar = str(narration_line or "").strip()
    lines = [
        f"### 镜头 {sn}（时间轴第 {shot_index + 1} 段，约 {dur:.1f}s）",
        "",
        "【画面与动作】",
        vd or "（未填，由模型推断信息清晰画面）",
        "",
    ]
    if cam:
        lines.extend(["【景别/运镜】", cam, ""])
    if obj:
        lines.extend(["【叙事目标】", obj, ""])
    lines.extend(
        [
            "【上屏字幕/花字】",
            ost or "（无单独花字，以口播为主）",
            "",
            "【口播/配音正文】",
            nar or "（空，请检查视觉规划 narration 或脚本分段）",
            "",
            "---",
            "",
        ]
    )
    return "\n".join(lines)


def build_ltx2_full_input_document(
    shots: List[dict], narrations: List[str]
) -> str:
    """整支视频的 LTX2 输入总表：与视觉规划镜头一一对应。"""
    header = (
        "# LTX2 分镜输入总表\n\n"
        "说明：以下每一节对应视觉规划中的一个镜头；"
        "「口播/配音正文」会作为侧车 `narration` 字段提交；"
        "「画面与动作」等与花字合并为侧车 `prompt`；花字另传 `subtitle`。\n\n"
    )
    blocks: List[str] = []
    for idx, shot in enumerate(shots):
        narr = narrations[idx] if idx < len(narrations) else ""
        blocks.append(build_ltx2_shot_input_block(shot, idx, narr))
    return header + "\n".join(blocks)


def shot_to_image_prompt(shot: dict, *, shot_index: int = 0) -> str:
    """用分镜的文案字段拼图像/视频生成提示词。"""
    parts: List[str] = []
    nar = str(shot.get("narration") or shot.get("voiceover") or "").strip()
    if nar:
        parts.append(f"口播对白参考：{nar[:900]}")
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
    # 首镜写全约束，后续镜头缩短公共前缀，避免每镜一大段重复话术
    prefix = (
        "短视频分镜画面，干净构图，无文字水印，适合口播与信息流视频："
        if shot_index == 0
        else "分镜画面，干净构图、无角标水印："
    )
    return (prefix + core)[:1800]


def ai_image_generation_available() -> bool:
    try:
        get_manager().get_provider(settings.DEFAULT_AI_GENERATION_PROVIDER)
        return True
    except Exception:
        return False


def shot_to_ltx2_prompt(
    shot: dict,
    *,
    shot_index: int = 0,
    narration_line: Optional[str] = None,
    subtitle_line: Optional[str] = None,
) -> str:
    """
    LTX-2 文本生成视频：结构化文档式 prompt（画面/花字/叙事），
    完整口播由侧车 narration 字段单独提交，避免与画面描述重复堆叠。
    """
    sn = shot.get("shot_no", shot_index + 1)
    dur = float(shot.get("duration_sec") or 5)
    vd = str(shot.get("visual_description") or "").strip()
    cam = str(shot.get("camera_language") or "").strip()
    ost = (subtitle_line if subtitle_line is not None else "").strip() or str(
        shot.get("on_screen_text") or ""
    ).strip()
    obj = str(shot.get("objective") or "").strip()
    ms = shot.get("material_suggestion") or []
    ms_txt = ""
    if isinstance(ms, list) and ms:
        ms_txt = "，".join(str(x) for x in ms[:4] if str(x).strip())

    nar = str(narration_line or shot.get("narration") or shot.get("voiceover") or "").strip()
    nar_hint = nar[:200] + ("…" if len(nar) > 200 else "") if nar else ""

    lines: List[str] = [
        f"【LTX2·镜头{sn}】时长约{dur:.1f}秒",
        "【画面与动作】" + (vd or "短视频信息画面，主体清晰"),
    ]
    if cam:
        lines.append("【景别/运镜】" + cam)
    if ost:
        lines.append(
            "【上屏字幕/花字】"
            + ost
            + "（短关键词；完整配音以口播字段为准，请口型与语气一致）"
        )
    if obj:
        lines.append("【叙事目标】" + obj)
    if ms_txt:
        lines.append("【素材参考】" + ms_txt)
    if nar_hint:
        lines.append("【对白要点摘要】" + nar_hint)

    if shot_index == 0:
        lines.append(
            "【生成要求】带同步对白的竖屏/横屏短视频片段；自然语气，环境音合理；画面无角标水印。"
        )
    else:
        lines.append("【生成要求】与口播同步对白；语气自然；无角标水印。")

    return "\n".join(lines)[:2400]


def narration_lines_for_shots(
    db: "Session",
    project_id: str,
    num_shots: int,
    visual_shots: Optional[List[dict]] = None,
) -> List[str]:
    """供 LTX 侧车口播：优先使用视觉规划每镜的 narration，缺省再按脚本 segments 轮转。"""
    from app.models.script import Script

    n = max(0, int(num_shots))
    lines: List[str] = [""] * n
    if n <= 0:
        return lines

    if visual_shots:
        for i in range(min(n, len(visual_shots))):
            row = visual_shots[i] if isinstance(visual_shots[i], dict) else {}
            narr = str(
                row.get("narration") or row.get("voiceover") or row.get("narration_script") or ""
            ).strip()
            if narr:
                lines[i] = narr
        if all(str(x or "").strip() for x in lines):
            return lines

    script = (
        db.query(Script)
        .filter(Script.project_id == project_id)
        .order_by(Script.created_at.desc())
        .first()
    )
    if not script:
        return lines

    texts: List[str] = []
    segments = script.segments if isinstance(script.segments, list) else []
    for s in segments:
        if isinstance(s, dict):
            t = str(s.get("text") or "").strip()
        else:
            t = str(s).strip()
        if t:
            texts.append(t)

    if not texts:
        full = (script.full_script or "").strip()
        if full:
            parts = [p.strip() for p in full.split("\n\n") if p.strip()]
            texts = parts if parts else [full]

    if not texts:
        return lines

    for i in range(n):
        if not str(lines[i] or "").strip():
            lines[i] = texts[i % len(texts)]
    return lines


async def build_ltx2_text_shot_timeline(
    shots: List[dict],
    narrations: List[str],
    *,
    project_id: Optional[str] = None,
    on_shot_progress: Optional[Callable[[int, int, str], Awaitable[None]]] = None,
    on_activity_log: Optional[Callable[[str], None]] = None,
    on_shot_board: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    """
    无参考图：按分镜调用 LTX-2 侧车文本生成音视频，再拼接。
    不调用 DALL·E 生图；与 Wan I2V 素材链路无关。

    与视觉规划 1:1：按 shot_no 与口播列表对齐后再逐镜请求侧车。
    """
    from app.services.ltx2_video import generate_ltx2_t2v_clip_async

    shots, narrations = align_visual_shots_with_narrations(list(shots or []), list(narrations or []))

    stats: Dict[str, Any] = {
        "from_material": 0,
        "generated": 0,
        "placeholder": 0,
        "wan_i2v": 0,
        "ltx2_t2v": 0,
    }
    timeline: List[Dict[str, Any]] = []
    cache_dir = Path(settings.DATA_DIR) / "ltx2_t2v_cache" / (project_id or "default")
    cache_dir.mkdir(parents=True, exist_ok=True)

    ltx_shot_board_final: List[Dict[str, Any]] = []
    total = len(shots)
    ltx_doc_full = build_ltx2_full_input_document(shots, narrations)
    w = int(getattr(settings, "LTX2_T2V_WIDTH", 1920) or 1920)
    h = int(getattr(settings, "LTX2_T2V_HEIGHT", 1088) or 1088)
    fps = int(getattr(settings, "LTX2_T2V_FPS", 24) or 24)

    for idx, shot in enumerate(shots):
        dur = float(shot.get("duration_sec") or 5)
        dur = max(0.5, min(120.0, dur))
        sn = shot.get("shot_no", idx + 1)
        narr = ""
        if idx < len(narrations):
            narr = str(narrations[idx] or "").strip()
        subtitle = str(shot.get("on_screen_text") or "").strip()
        shot_block = build_ltx2_shot_input_block(shot, idx, narr)
        prompt = shot_to_ltx2_prompt(
            shot,
            shot_index=idx,
            narration_line=narr,
            subtitle_line=subtitle,
        )

        if on_shot_progress:
            await on_shot_progress(
                idx + 1,
                total,
                f"镜头 {sn}：LTX-2 文本生成音视频（含对白）…",
            )

        if on_shot_board:
            on_shot_board(
                {
                    "event": "start",
                    "shot_index": idx,
                    "shot_no": sn,
                    "total": total,
                    "prompt": prompt,
                    "narration": narr,
                    "subtitle": subtitle,
                    "ltx_input_block": shot_block,
                    "duration_sec": dur,
                }
            )

        stem = f"{project_id or 'p'}_{idx}_{shot.get('shot_no', idx)}"
        if on_activity_log:
            on_activity_log(
                f"镜头 {sn}（{idx + 1}/{total}）：请求 LTX 侧车，时长 {dur:.1f}s，"
                f"分辨率 {w}x{h}@{fps}fps"
            )
        vp = await generate_ltx2_t2v_clip_async(
            prompt=prompt,
            narration=narr,
            subtitle=subtitle,
            duration_sec=dur,
            cache_dir=cache_dir,
            stem=stem,
            width=w,
            height=h,
            fps=fps,
        )
        if vp and os.path.isfile(vp):
            stats["ltx2_t2v"] += 1
            timeline.append({"path": vp, "duration_sec": dur})
            sz = os.path.getsize(vp)
            if on_shot_board:
                on_shot_board(
                    {
                        "event": "complete",
                        "shot_index": idx,
                        "shot_no": sn,
                        "total": total,
                        "ok": True,
                        "output_path": vp,
                        "size_kb": sz // 1024,
                    }
                )
            if on_activity_log:
                on_activity_log(
                    f"镜头 {sn}：侧车返回 OK，已缓存 {vp}（{sz // 1024} KiB）"
                )
            ltx_shot_board_final.append(
                {
                    "shot_index": idx,
                    "shot_no": sn,
                    "total": total,
                    "status": "done",
                    "prompt": prompt,
                    "narration": narr,
                    "subtitle": subtitle,
                    "ltx_input_block": shot_block,
                    "duration_sec": dur,
                    "output_path": vp,
                    "size_kb": sz // 1024,
                }
            )
            continue

        stats["placeholder"] += 1
        timeline.append({"duration_sec": dur, "placeholder": True})
        if on_shot_board:
            on_shot_board(
                {
                    "event": "complete",
                    "shot_index": idx,
                    "shot_no": sn,
                    "total": total,
                    "ok": False,
                    "output_path": None,
                    "size_kb": None,
                }
            )
        if on_activity_log:
            on_activity_log(
                f"镜头 {sn}：LTX 未返回有效文件，使用占位片段（请查侧车/Comfy 日志）"
            )
        ltx_shot_board_final.append(
            {
                "shot_index": idx,
                "shot_no": sn,
                "total": total,
                "status": "placeholder",
                "prompt": prompt,
                "narration": narr,
                "subtitle": subtitle,
                "ltx_input_block": shot_block,
                "duration_sec": dur,
                "output_path": None,
                "size_kb": None,
            }
        )

    hints: List[str] = []
    if total > 0 and stats.get("placeholder") == total:
        hints.append(
            "LTX-2 侧车未返回任何有效片段。请确认 LTX2_T2V_ENDPOINT 可访问、"
            "侧车已实现 POST /generate，并查看后端日志。"
        )
    elif stats.get("ltx2_t2v", 0) > 0:
        hints.append(
            "已使用 LTX-2 生成含对白的分镜视频；若开启 LTX2_T2V_SKIP_EXTERNAL_TTS，"
            "成片默认不再叠整条 TTS 音轨。"
        )

    stats["diagnostics"] = {
        "pipeline": "ltx2_text_shots",
        "ltx2_t2v_endpoint_configured": bool(
            (getattr(settings, "LTX2_T2V_ENDPOINT", None) or "").strip()
        ),
        "wan_i2v_skipped": True,
        "hints": hints,
        "visual_shots_aligned": total,
        "ltx2_input_document": ltx_doc_full,
    }
    return timeline, stats, ltx_shot_board_final


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
    shots, _ = align_visual_shots_with_narrations(list(shots or []), [])
    stats = {
        "from_material": 0,
        "generated": 0,
        "placeholder": 0,
        "wan_i2v": 0,
        "ltx2_t2v": 0,
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
        prompt = shot_to_image_prompt(shot, shot_index=idx)
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
