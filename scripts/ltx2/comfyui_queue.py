"""
在已运行的 ComfyUI 上队列执行 API 格式 workflow，并拉取 SaveVideo 产出。
需：ComfyUI 监听 LTX2_COMFYUI_URL（如 http://127.0.0.1:8188）
   + LTX2_COMFY_API_JSON 为「Save (API Format)」导出的 JSON。
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx


def patch_ltx_api_prompt(
    prompt: Dict[str, Any],
    *,
    combined_text: str,
    frames: int,
    width: int,
    height: int,
    fps: float,
    node_prompt: str,
    node_frames: str,
    node_fps: Optional[str] = None,
    node_empty_image: Optional[str] = None,
) -> None:
    """按节点 id（字符串）写入文本/帧率/分辨率。"""
    if node_prompt in prompt and isinstance(prompt[node_prompt], dict):
        node = prompt[node_prompt]
        inp = node.setdefault("inputs", {})
        if node.get("class_type") == "PrimitiveStringMultiline":
            inp["value"] = combined_text
            inp["text"] = combined_text
        elif "text" in inp:
            inp["text"] = combined_text
        elif "string" in inp:
            inp["string"] = combined_text

    if node_frames in prompt and isinstance(prompt[node_frames], dict):
        node = prompt[node_frames]
        if node.get("class_type") == "PrimitiveInt":
            node.setdefault("inputs", {})["value"] = int(frames)

    if node_fps and node_fps in prompt and isinstance(prompt[node_fps], dict):
        node = prompt[node_fps]
        if node.get("class_type") == "PrimitiveFloat":
            node.setdefault("inputs", {})["value"] = float(fps)

    if node_empty_image and node_empty_image in prompt and isinstance(
        prompt[node_empty_image], dict
    ):
        node = prompt[node_empty_image]
        if node.get("class_type") == "EmptyImage":
            inp = node.setdefault("inputs", {})
            inp["width"] = int(width)
            inp["height"] = int(height)


def queue_and_wait_video(
    server: str,
    prompt: Dict[str, Any],
    *,
    timeout_sec: float = 7200.0,
    poll_interval: float = 2.0,
) -> bytes:
    server = server.rstrip("/")
    client_id = str(uuid.uuid4())
    payload = {"prompt": prompt, "client_id": client_id}
    with httpx.Client(timeout=60.0) as client:
        r = client.post(f"{server}/prompt", json=payload)
        if r.status_code != 200:
            raise RuntimeError(f"ComfyUI /prompt failed: {r.status_code} {r.text[:500]}")
        data = r.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"No prompt_id in response: {data}")

        deadline = time.time() + timeout_sec
        hist: Optional[dict] = None
        while time.time() < deadline:
            hr = client.get(f"{server}/history/{prompt_id}")
            if hr.status_code == 200:
                body = hr.json()
                if prompt_id in body:
                    hist = body[prompt_id]
                    break
            time.sleep(poll_interval)

        if not hist:
            raise TimeoutError(f"ComfyUI prompt {prompt_id} did not finish in {timeout_sec}s")

        outputs = hist.get("outputs") or {}
        for _nid, out in outputs.items():
            for key in ("videos", "gifs"):
                if key not in out:
                    continue
                for item in out[key]:
                    q = {
                        "filename": item["filename"],
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                    }
                    url = f"{server}/view?{urlencode(q)}"
                    vr = client.get(url, timeout=600.0)
                    if vr.status_code == 200 and len(vr.content) > 1000:
                        return vr.content

        raise RuntimeError(f"No video/gif in ComfyUI outputs: {json.dumps(outputs)[:800]}")


def _load_prompt_from_api_file(api_json_path: Path) -> Dict[str, Any]:
    """Comfy 导出的 API JSON 可能是纯 prompt 字典，或包一层 {\"prompt\": {...}}。"""
    raw: Any = json.loads(api_json_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "prompt" in raw and isinstance(raw["prompt"], dict):
        return raw["prompt"]
    if not isinstance(raw, dict):
        raise ValueError("API JSON 根节点必须是对象")
    return raw


def run_from_api_file(
    api_json_path: Path,
    server: str,
    *,
    combined_text: str,
    frames: int,
    width: int,
    height: int,
    fps: float,
) -> bytes:
    prompt = _load_prompt_from_api_file(api_json_path)
    patch_ltx_api_prompt(
        prompt,
        combined_text=combined_text,
        frames=frames,
        width=width,
        height=height,
        fps=fps,
        node_prompt=os.environ.get("LTX2_COMFY_NODE_PROMPT", "5222"),
        node_frames=os.environ.get("LTX2_COMFY_NODE_FRAMES", "5218"),
        node_fps=os.environ.get("LTX2_COMFY_NODE_FPS") or "5221",
        node_empty_image=os.environ.get("LTX2_COMFY_NODE_EMPTY_IMAGE") or "5217",
    )
    return queue_and_wait_video(
        server,
        prompt,
        timeout_sec=float(os.environ.get("LTX2_COMFY_TIMEOUT", "7200")),
    )
