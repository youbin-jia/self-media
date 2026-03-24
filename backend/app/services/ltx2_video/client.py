"""
LTX-2 文本→视频（含对白/环境音）侧车调用。

侧车需实现 HTTP API（见 scripts/ltx2_t2v_sidecar.py 与 docs/LTX2_PIPELINE.md）：
  POST {ENDPOINT}/generate  JSON body
  返回 application/octet-stream (mp4) 或 JSON {"path": "/abs/path.mp4"}
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def ltx2_t2v_available() -> bool:
    if not getattr(settings, "LTX2_T2V_ENABLED", False):
        return False
    return bool((getattr(settings, "LTX2_T2V_ENDPOINT", None) or "").strip())


def ltx_compliant_frame_count(duration_sec: float, fps: int) -> int:
    """LTX 类模型常要求总帧数为 8n+1。"""
    fps = max(1, int(fps))
    target = max(9, int(round(float(duration_sec) * fps)))
    n = (target - 1) // 8
    if n * 8 + 1 < target:
        n += 1
    return n * 8 + 1


async def generate_ltx2_t2v_clip_async(
    *,
    prompt: str,
    narration: str = "",
    subtitle: str = "",
    duration_sec: float,
    cache_dir: Path,
    stem: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[int] = None,
) -> Optional[str]:
    """
    调用侧车生成单镜 MP4（建议内含音轨）。成功返回本地绝对路径。
    """
    if not ltx2_t2v_available():
        return None

    endpoint = (getattr(settings, "LTX2_T2V_ENDPOINT", None) or "").rstrip("/")
    url = endpoint if "/generate" in endpoint else f"{endpoint}/generate"
    timeout = float(getattr(settings, "LTX2_T2V_TIMEOUT_SEC", 7200) or 7200)
    w = int(width or getattr(settings, "LTX2_T2V_WIDTH", 1920) or 1920)
    h = int(height or getattr(settings, "LTX2_T2V_HEIGHT", 1088) or 1088)
    fp = int(fps or getattr(settings, "LTX2_T2V_FPS", 24) or 24)
    frames = ltx_compliant_frame_count(duration_sec, fp)

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    token = getattr(settings, "LTX2_T2V_HTTP_BEARER", None)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload: Dict[str, Any] = {
        "prompt": (prompt or "").strip(),
        "narration": (narration or "").strip(),
        "subtitle": (subtitle or "").strip(),
        "duration_sec": float(duration_sec),
        "width": w,
        "height": h,
        "fps": fp,
        "frames": frames,
    }

    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{stem or uuid.uuid4().hex[:12]}.mp4"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.warning(
                "LTX-2 T2V HTTP status=%s body=%s",
                resp.status_code,
                (resp.text or "")[:800],
            )
            return None

        ct = (resp.headers.get("content-type") or "").lower()
        body = resp.content
        is_mp4 = "video" in ct or (len(body) > 12 and body[4:8] == b"ftyp")
        if is_mp4:
            out.write_bytes(body)
            if out.is_file():
                logger.info(
                    "LTX-2 T2V 已写入 MP4：%s（%s KiB，frames=%s）",
                    out.resolve(),
                    out.stat().st_size // 1024,
                    frames,
                )
                return str(out.resolve())
            return None

        try:
            data = resp.json()
            p = data.get("path") or data.get("video_path")
            if p and os.path.isfile(str(p)):
                import shutil

                shutil.copy2(str(p), str(out))
                return str(out.resolve()) if out.is_file() else None
        except Exception:
            pass
        logger.warning("LTX-2 T2V 响应无法解析为视频")
        return None
    except Exception as exc:
        logger.warning("LTX-2 T2V 请求异常: %s", exc)
        return None
