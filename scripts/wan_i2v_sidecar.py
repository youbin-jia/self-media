#!/usr/bin/env python3
"""
通义万相 Wan2.1 I2V HTTP 侧车：接收参考图 + 提示词，调用官方 generate.py，返回 MP4。

必填环境变量:
  WAN_I2V_REPO_DIR  — Wan-Video/Wan2.1 克隆根目录（含 generate.py）
  WAN_I2V_CKPT_DIR  — Wan2.1-I2V-14B-720P 等模型目录

可选:
  WAN_I2V_PYTHON, WAN_I2V_TASK, WAN_I2V_SIZE, WAN_I2V_EXTRA_ARGS, WAN_I2V_TIMEOUT_SEC, WAN_SIDECAR_PORT

启动:
  WAN_I2V_REPO_DIR=/path/Wan2.1 WAN_I2V_CKPT_DIR=/path/Wan2.1-I2V-14B-720P \\
    python scripts/wan_i2v_sidecar.py
"""
from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="Wan2.1 I2V Sidecar", version="1.0.0")


def _extra_args() -> list:
    raw = (os.environ.get("WAN_I2V_EXTRA_ARGS") or "").strip()
    if not raw:
        return []
    return shlex.split(raw)


@app.get("/health")
async def health():
    miss = [
        k
        for k in ("WAN_I2V_REPO_DIR", "WAN_I2V_CKPT_DIR")
        if not (os.environ.get(k) or "").strip()
    ]
    if miss:
        return JSONResponse(
            {"ok": False, "missing_env": miss},
            status_code=503,
        )
    repo = Path(os.environ["WAN_I2V_REPO_DIR"])
    gen = repo / "generate.py"
    if not gen.is_file():
        return JSONResponse(
            {"ok": False, "error": f"generate.py not found under {repo}"},
            status_code=503,
        )
    return {"ok": True}


@app.post("/generate")
async def generate(
    image: UploadFile = File(...),
    prompt: str = Form(...),
):
    repo = (os.environ.get("WAN_I2V_REPO_DIR") or "").strip()
    ckpt = (os.environ.get("WAN_I2V_CKPT_DIR") or "").strip()
    if not repo or not ckpt:
        raise HTTPException(status_code=500, detail="Missing WAN_I2V_REPO_DIR or WAN_I2V_CKPT_DIR")

    py = os.environ.get("WAN_I2V_PYTHON") or "python"
    task = os.environ.get("WAN_I2V_TASK") or "i2v-14B"
    size = os.environ.get("WAN_I2V_SIZE") or "1280*720"
    timeout = int(os.environ.get("WAN_I2V_TIMEOUT_SEC") or "7200")

    repo_path = Path(repo).resolve()
    gen_py = repo_path / "generate.py"
    if not gen_py.is_file():
        raise HTTPException(status_code=500, detail="generate.py not found in WAN_I2V_REPO_DIR")

    suffix = Path(image.filename or "in.png").suffix or ".png"
    if suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"):
        suffix = ".png"

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        in_img = td_path / f"input{suffix}"
        out_mp4 = td_path / f"out_{uuid.uuid4().hex[:10]}.mp4"
        in_img.write_bytes(await image.read())

        cmd = [
            py,
            str(gen_py),
            "--task",
            task,
            "--size",
            size,
            "--ckpt_dir",
            str(Path(ckpt).resolve()),
            "--image",
            str(in_img.resolve()),
            "--prompt",
            prompt,
            "--save_file",
            str(out_mp4.resolve()),
        ]
        cmd.extend(_extra_args())

        def _run():
            return subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                timeout=timeout,
            )

        proc = await asyncio.to_thread(_run)
        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", errors="replace")[-1500:]
            raise HTTPException(
                status_code=500,
                detail=f"generate.py failed: {err}",
            )
        if not out_mp4.is_file() or out_mp4.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="empty output video")
        data = out_mp4.read_bytes()

    return Response(content=data, media_type="video/mp4")


def main():
    import uvicorn

    host = os.environ.get("WAN_SIDECAR_HOST", "0.0.0.0")
    port = int(os.environ.get("WAN_SIDECAR_PORT", "9810"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
