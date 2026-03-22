"""
Wan2.1 Image-to-Video 调用封装。

支持：
- subprocess：在本机已克隆的 Wan-Video/Wan2.1 仓库中执行官方 generate.py
- http：调用侧车服务（见 scripts/wan_i2v_sidecar.py），便于 GPU 与 API 服务分离
"""
from __future__ import annotations

import asyncio
import logging
import os
import shlex
import uuid
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def wan_i2v_available() -> bool:
    if not getattr(settings, "WAN_I2V_ENABLED", False):
        return False
    mode = (getattr(settings, "WAN_I2V_MODE", None) or "subprocess").lower()
    if mode == "http":
        return bool(getattr(settings, "WAN_I2V_ENDPOINT", None))
    repo = getattr(settings, "WAN_I2V_REPO_DIR", None) or ""
    ckpt = getattr(settings, "WAN_I2V_CKPT_DIR", None) or ""
    return bool(repo and ckpt and Path(repo).is_dir() and Path(ckpt).is_dir())


def _parse_extra_args() -> list:
    raw = getattr(settings, "WAN_I2V_EXTRA_ARGS", None) or ""
    raw = str(raw).strip()
    if not raw:
        return []
    try:
        return shlex.split(raw)
    except ValueError:
        logger.warning("WAN_I2V_EXTRA_ARGS 解析失败，已忽略: %s", raw)
        return []


async def _i2v_via_http(
    image_path: str,
    prompt: str,
    output_mp4: Path,
) -> bool:
    endpoint = (getattr(settings, "WAN_I2V_ENDPOINT", None) or "").rstrip("/")
    if not endpoint:
        return False
    url = endpoint if "/generate" in endpoint else f"{endpoint}/generate"
    timeout = float(getattr(settings, "WAN_I2V_TIMEOUT_SEC", 7200) or 7200)
    headers = {}
    token = getattr(settings, "WAN_I2V_HTTP_BEARER", None)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            with open(image_path, "rb") as f:
                files = {"image": ("input.png", f, "application/octet-stream")}
                data = {"prompt": prompt}
                resp = await client.post(url, files=files, data=data, headers=headers)
            if resp.status_code != 200:
                logger.warning(
                    "Wan I2V HTTP 失败 status=%s body=%s",
                    resp.status_code,
                    resp.text[:500],
                )
                return False
            ct = (resp.headers.get("content-type") or "").lower()
            body = resp.content
            is_mp4 = "video" in ct or (
                len(body) > 12 and body[4:8] == b"ftyp"
            )
            if is_mp4:
                output_mp4.parent.mkdir(parents=True, exist_ok=True)
                output_mp4.write_bytes(body)
                return output_mp4.is_file()
            # JSON { "path": "..." } 兼容共享盘部署
            try:
                payload = resp.json()
                p = payload.get("path") or payload.get("video_path")
                if p and os.path.isfile(str(p)):
                    import shutil

                    output_mp4.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(p), str(output_mp4))
                    return True
            except Exception:
                pass
            logger.warning("Wan I2V HTTP 响应无法解析为视频")
            return False
    except Exception as exc:
        logger.warning("Wan I2V HTTP 请求异常: %s", exc)
        return False


async def _i2v_via_subprocess(
    image_path: str,
    prompt: str,
    output_mp4: Path,
) -> bool:
    repo = Path(getattr(settings, "WAN_I2V_REPO_DIR", "") or "")
    ckpt = getattr(settings, "WAN_I2V_CKPT_DIR", None) or ""
    if not repo.is_dir() or not ckpt or not Path(ckpt).is_dir():
        logger.warning("Wan I2V subprocess 缺少 WAN_I2V_REPO_DIR 或 WAN_I2V_CKPT_DIR")
        return False

    py = getattr(settings, "WAN_I2V_PYTHON", None) or "python"
    task = getattr(settings, "WAN_I2V_TASK", None) or "i2v-14B"
    size = getattr(settings, "WAN_I2V_SIZE", None) or "1280*720"
    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        py,
        str(repo / "generate.py"),
        "--task",
        task,
        "--size",
        size,
        "--ckpt_dir",
        str(ckpt),
        "--image",
        str(Path(image_path).resolve()),
        "--prompt",
        prompt,
        "--save_file",
        str(output_mp4.resolve()),
    ]
    cmd.extend(_parse_extra_args())

    timeout = int(getattr(settings, "WAN_I2V_TIMEOUT_SEC", 7200) or 7200)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(repo.resolve()),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.warning("Wan I2V subprocess 超时 (%ss)", timeout)
            return False

        if proc.returncode != 0:
            err = (stderr or b"").decode("utf-8", errors="replace")[-2000:]
            logger.warning(
                "Wan I2V subprocess 退出码=%s stderr_tail=%s",
                proc.returncode,
                err,
            )
            return False
        if output_mp4.is_file() and output_mp4.stat().st_size > 0:
            return True
        logger.warning("Wan I2V 未生成有效文件: %s", output_mp4)
        return False
    except FileNotFoundError:
        logger.warning("未找到 Wan I2V Python 可执行文件: %s", py)
        return False
    except Exception as exc:
        logger.warning("Wan I2V subprocess 异常: %s", exc)
        return False


async def generate_i2v_clip_async(
    *,
    image_path: str,
    prompt: str,
    cache_dir: Path,
    stem: Optional[str] = None,
) -> Optional[str]:
    """
    基于单张参考图生成短视频片段，返回 mp4 绝对路径；失败返回 None。
    """
    if not wan_i2v_available():
        return None
    if not image_path or not os.path.isfile(image_path):
        return None

    stem = stem or f"wan_i2v_{uuid.uuid4().hex[:12]}"
    out = (cache_dir / f"{stem}.mp4").resolve()
    mode = (getattr(settings, "WAN_I2V_MODE", None) or "subprocess").lower()

    ok = False
    if mode == "http":
        ok = await _i2v_via_http(image_path, prompt, out)
    else:
        ok = await _i2v_via_subprocess(image_path, prompt, out)

    if ok and out.is_file():
        return str(out)
    return None
