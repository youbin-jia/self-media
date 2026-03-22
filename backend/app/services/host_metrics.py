"""主机 CPU/内存与 NVIDIA GPU 指标（供前端实时监控；GPU 走 nvidia-smi，无需 pynvml）。"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from typing import Any, Dict, List

import psutil

logger = logging.getLogger(__name__)


def _nvidia_smi_gpus() -> List[Dict[str, Any]]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    try:
        proc = subprocess.run(
            [
                exe,
                "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
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
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            try:
                idx = int(parts[0])
                name = parts[1]
                util = int(re.sub(r"\D", "", parts[2]) or 0)
                mem_used = int(re.sub(r"\D", "", parts[3]) or 0)
                mem_total = int(re.sub(r"\D", "", parts[4]) or 0)
                temp = None
                if len(parts) > 5 and parts[5] not in ("", "[N/A]"):
                    try:
                        temp = int(float(parts[5]))
                    except ValueError:
                        pass
                rows.append(
                    {
                        "index": idx,
                        "name": name,
                        "utilization_gpu": util,
                        "mem_used_mb": mem_used,
                        "mem_total_mb": mem_total,
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
    }
