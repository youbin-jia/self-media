#!/usr/bin/env bash
# 启动 third_party/ltx2 内的 ComfyUI（LTX + GGUF 环境）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BASE="${ROOT}/third_party/ltx2"
COMFY="${BASE}/ComfyUI"
VENV="${BASE}/venv-comfyui"
RUNTIME_ENV="${BASE}/comfy.runtime.env"
COMFY_PORT="${LTX2_COMFY_PORT:-8188}"

if [[ -f "${RUNTIME_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${RUNTIME_ENV}"
fi

[[ -d "${COMFY}" ]] || { echo "未找到 ${COMFY}，请先运行: ./scripts/ltx2/setup_comfyui_ltx2.sh" >&2; exit 1; }
[[ -d "${VENV}" ]] || { echo "未找到 venv ${VENV}，请先运行 setup_comfyui_ltx2.sh" >&2; exit 1; }

# shellcheck disable=SC1091
source "${VENV}/bin/activate"

cd "${COMFY}"
exec python main.py --listen 0.0.0.0 --port "${COMFY_PORT}" "$@"
