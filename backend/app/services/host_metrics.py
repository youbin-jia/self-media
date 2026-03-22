"""主机 CPU/内存与 NVIDIA GPU 指标（供前端实时监控；GPU 走 nvidia-smi，无需 pynvml）。"""
from __future__ import annotations

import csv
import io
import logging
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


def _parse_smi_int_field(raw: str) -> Optional[int]:
    """解析 nvidia-smi CSV 中的整数字段；[N/A] 或空为 None。"""
    s = (raw or "").strip()
    if not s or "[n/a]" in s.lower():
        return None
    digits = re.sub(r"\D", "", s)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _nvidia_smi_gpus() -> List[Dict[str, Any]]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    try:
        proc = subprocess.run(
            [
                exe,
                "--query-gpu=index,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2.5,
            check=False,
        )
        if proc.returncode != 0 or not (proc.stdout or "").strip():
            return []
        rows: List[Dict[str, Any]] = []
        for line in proc.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # 显卡名里可能含逗号，必须用 CSV 解析，不能 split(',')
            try:
                parts = next(csv.reader(io.StringIO(line)))
            except StopIteration:
                continue
            parts = [p.strip() for p in parts]
            if len(parts) < 6:
                continue
            try:
                idx = int(parts[0])
                name = parts[1]
                util_gpu = _parse_smi_int_field(parts[2])
                util_mem = _parse_smi_int_field(parts[3])
                mem_used = _parse_smi_int_field(parts[4]) or 0
                mem_total = _parse_smi_int_field(parts[5]) or 0
                temp = None
                if len(parts) > 6 and parts[6] not in ("", "[N/A]"):
                    try:
                        temp = int(float(parts[6]))
                    except ValueError:
                        pass
                mem_percent = None
                if mem_total > 0:
                    mem_percent = round(100.0 * mem_used / mem_total, 1)
                rows.append(
                    {
                        "index": idx,
                        "name": name,
                        # SM 占用：瞬时采样，轻负载时常为 0；无法读取时为 null
                        "utilization_gpu": util_gpu,
                        # 显存控制器占用，推理时往往比 utilization.gpu 更明显
                        "utilization_memory": util_mem,
                        "mem_used_mb": mem_used,
                        "mem_total_mb": mem_total,
                        "mem_percent": mem_percent,
                        "temperature_c": temp,
                    }
                )
            except (ValueError, IndexError):
                continue
        return rows
    except Exception as exc:
        logger.debug("nvidia-smi failed: %s", exc)
        return []


def collect_host_metrics() -> Dict[str, Any]:
    """CPU、内存与 GPU 列表（cpu_percent 短 interval 平滑采样）。"""
    cpu_percent = float(psutil.cpu_percent(interval=0.12))
    vm = psutil.virtual_memory()
    gpus = _nvidia_smi_gpus()

    return {
        "cpu_percent": round(cpu_percent, 1),
        "cpu_count_logical": psutil.cpu_count(logical=True) or 0,
        "cpu_count_physical": psutil.cpu_count(logical=False) or 0,
        "mem_percent": round(float(vm.percent), 1),
        "mem_used_mb": int(vm.used // (1024 * 1024)),
        "mem_total_mb": int(vm.total // (1024 * 1024)),
        "gpus": gpus,
        "gpu_available": len(gpus) > 0,
        "metrics_hint": (
            "本接口采样的是「运行后端 API 的这台机器」上的 nvidia-smi。"
            "若 ComfyUI / 侧车在另一台主机或 Docker 内用 GPU，此处核心利用率可能长期接近 0；"
            "可结合「显存占用」与「显存控制器」判断本机显卡是否在干活。"
        ),
    }
