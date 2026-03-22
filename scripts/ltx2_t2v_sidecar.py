#!/usr/bin/env python3
"""
LTX-2 / 视频侧车：与主项目 POST /generate 契约一致，**默认保证产出可用 MP4**。

优先级（前者成功则不再尝试后者）：
  1) LTX2_COMFYUI_URL + LTX2_COMFY_API_JSON → 队列 ComfyUI（真实 LTX 工作流，需你已导出 API JSON）
  2) LTX2_T2V_SHELL
  3) LTX2_STUB_MP4
  4) **口播兜底**：edge-tts + ffmpeg（深色底 + 配音，适合自媒体先行发布）

依赖（按需）：
  pip install fastapi uvicorn httpx pydantic
  pip install edge-tts          # 兜底路径
  系统需 ffmpeg 在 PATH 中

启动（仓库根目录）：
  export LTX2_COMFYUI_URL=http://127.0.0.1:8188
  export LTX2_COMFY_API_JSON=$PWD/third_party/ltx2/workflows/ltx2_t2v.api.json
  uvicorn scripts.ltx2_t2v_sidecar:app --host 0.0.0.0 --port 9820
或：
  cd scripts && PYTHONPATH=. python -m uvicorn ltx2_t2v_sidecar:app --host 0.0.0.0 --port 9820
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# 允许导入同目录下 ltx2/comfyui_queue.py（本文件位于 scripts/，子目录为 scripts/ltx2/）
_SCRIPTS = Path(__file__).resolve().parent
_LTX_DIR = _SCRIPTS / "ltx2"
if _LTX_DIR.is_dir():
    sys.path.insert(0, str(_LTX_DIR))

app = FastAPI(title="LTX-2 T2V Sidecar", version="0.2")


class GenerateBody(BaseModel):
    prompt: str = ""
    narration: str = ""
    duration_sec: float = Field(5.0, ge=0.5, le=120)
    width: int = 1920
    height: int = 1088
    fps: int = 24
    frames: int = 121


def _combined_script(body: GenerateBody) -> str:
    p = (body.prompt or "").strip()
    n = (body.narration or "").strip()
    if p and n:
        return f"{p}\n\n【口播】{n}"
    return p or n or "短视频内容"


def _generate_ffmpeg_voiceover(body: GenerateBody, out: Path) -> None:
    """edge-tts + ffmpeg，不依赖 GPU。"""
    text = _combined_script(body)[:5000]
    w, h, fps = body.width, body.height, max(1, body.fps)
    voice = os.environ.get("LTX2_EDGE_VOICE", "zh-CN-XiaoxiaoNeural")
    tmp = Path(tempfile.mkdtemp(prefix="ltx2fb_"))
    mp3 = tmp / "narration.mp3"
    try:
        subprocess.run(
            [
                "edge-tts",
                "--voice",
                voice,
                "--text",
                text,
                "--write-media",
                str(mp3),
            ],
            check=True,
            timeout=120,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail="未找到 edge-tts，请 pip install edge-tts",
        ) from e
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"edge-tts 失败: {e.stderr or e}",
        ) from e

    if not mp3.is_file() or mp3.stat().st_size < 100:
        raise HTTPException(status_code=500, detail="edge-tts 未生成有效音频")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x14141c:s={w}x{h}:r={fps}",
                "-i",
                str(mp3),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(out),
            ],
            check=True,
            timeout=300,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail="未找到 ffmpeg，请安装 ffmpeg 并加入 PATH",
        ) from e
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"ffmpeg 失败: {e.stderr or e}",
        ) from e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _try_comfy(body: GenerateBody, out: Path) -> bool:
    server = (os.environ.get("LTX2_COMFYUI_URL") or "").strip().rstrip("/")
    api_path = os.environ.get("LTX2_COMFY_API_JSON") or ""
    if not server or not api_path:
        return False
    p = Path(api_path).expanduser()
    if not p.is_file():
        return False
    try:
        from comfyui_queue import run_from_api_file
    except ImportError:
        return False
    try:
        data = run_from_api_file(
            p,
            server,
            combined_text=_combined_script(body),
            frames=int(body.frames),
            width=int(body.width),
            height=int(body.height),
            fps=float(body.fps),
        )
        out.write_bytes(data)
        return out.is_file() and out.stat().st_size > 1000
    except Exception as e:
        if (os.environ.get("LTX2_DEBUG") or "").strip().lower() in ("1", "true", "yes"):
            import traceback

            traceback.print_exc()
            sys.stderr.write(f"[ltx2 sidecar] ComfyUI 路径失败: {e!r}\n")
        return False


def _comfy_ready() -> dict:
    """真实 LTX 是否「已配置好」：侧车进程内 URL + 存在的 API JSON 文件。"""
    server = (os.environ.get("LTX2_COMFYUI_URL") or "").strip()
    api_env = (os.environ.get("LTX2_COMFY_API_JSON") or "").strip()
    p = Path(api_env).expanduser() if api_env else None
    exists = bool(p and p.is_file())
    return {
        "comfyui_url_set": bool(server),
        "comfy_api_json_env_set": bool(api_env),
        "comfy_api_json_exists": exists,
        "comfy_ready_for_real_ltx": bool(server and exists),
    }


def _voiceover_fallback_capable() -> bool:
    return bool(shutil.which("edge-tts") and shutil.which("ffmpeg"))


@app.get("/health")
def health():
    comfy = _comfy_ready()
    return {
        "status": "ok",
        **comfy,
        # 兼容旧字段：曾误把口播兜底标成 true；现用 comfy_ready_for_real_ltx 判断是否走 Comfy
        "comfyui": comfy["comfyui_url_set"],
        "comfy_api_json": comfy["comfy_api_json_env_set"] and comfy["comfy_api_json_exists"],
        "shell": bool(os.environ.get("LTX2_T2V_SHELL")),
        "stub": bool(os.environ.get("LTX2_STUB_MP4")),
        "voiceover_fallback_capable": _voiceover_fallback_capable(),
        "hint": (
            "未配置 Comfy 或未导出 API JSON 时会用口播兜底；"
            "请在**启动侧车的 shell**里设置 LTX2_COMFYUI_URL 与 LTX2_COMFY_API_JSON，"
            "或创建 scripts/.env.ltx2（见 .env.ltx2.example）后重启侧车。"
        ),
    }


@app.post("/generate")
def generate(body: GenerateBody):
    out = Path(tempfile.mkdtemp(prefix="ltx2t2v_")) / "out.mp4"

    if _try_comfy(body, out):
        return FileResponse(str(out), media_type="video/mp4", filename="clip.mp4")

    stub = os.environ.get("LTX2_STUB_MP4")
    if stub and Path(stub).is_file():
        shutil.copy2(stub, out)
        return FileResponse(str(out), media_type="video/mp4", filename="clip.mp4")

    shell = os.environ.get("LTX2_T2V_SHELL")
    if shell:
        env = os.environ.copy()
        env["LTX2_PROMPT"] = body.prompt
        env["LTX2_NARRATION"] = body.narration
        env["LTX2_OUT"] = str(out)
        env["LTX2_FRAMES"] = str(body.frames)
        env["LTX2_WIDTH"] = str(body.width)
        env["LTX2_HEIGHT"] = str(body.height)
        env["LTX2_FPS"] = str(body.fps)
        env["LTX2_DURATION_SEC"] = str(body.duration_sec)
        try:
            subprocess.run(shell, shell=True, env=env, check=True, timeout=7200)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"LTX2_T2V_SHELL failed: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise HTTPException(status_code=504, detail="LTX2_T2V_SHELL timeout") from e
        if out.is_file():
            return FileResponse(str(out), media_type="video/mp4", filename="clip.mp4")

    # 默认兜底：口播 MP4（自媒体可用）
    _generate_ffmpeg_voiceover(body, out)
    if out.is_file():
        return FileResponse(str(out), media_type="video/mp4", filename="clip.mp4")
    raise HTTPException(status_code=500, detail="生成失败")
