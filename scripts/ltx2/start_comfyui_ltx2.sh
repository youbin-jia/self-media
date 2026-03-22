#!/usr/bin/env bash
# 启动 third_party/ltx2 内的 ComfyUI（LTX + GGUF 环境）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BASE="${ROOT}/third_party/ltx2"
COMFY="${BASE}/ComfyUI"
VENV="${BASE}/venv-comfyui"
RUNTIME_ENV="${BASE}/comfy.runtime.env"
COMFY_PORT="${LTX2_COMFY_PORT:-8188}"

_port_in_use() {
  local p="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -tln 2>/dev/null | grep -qE ":${p}[[:space:]]"
    return $?
  fi
  # fallback
  (echo >/dev/tcp/127.0.0.1/"$p") >/dev/null 2>&1
}

if [[ -z "${LTX2_COMFY_ALLOW_PORT_CONFLICT:-}" ]] && _port_in_use "${COMFY_PORT}"; then
  echo "[start_comfyui_ltx2] 端口 ${COMFY_PORT} 已被占用，通常表示 **ComfyUI 已在运行**。" >&2
  echo "  → 直接在浏览器打开: http://127.0.0.1:${COMFY_PORT}" >&2
  echo "  → 若要重启：先结束旧进程再启动，例如：" >&2
  echo "       ss -tlnp | grep :${COMFY_PORT}" >&2
  echo "       kill <PID>    # 或: fuser -k ${COMFY_PORT}/tcp" >&2
  echo "  → 若故意要开第二实例，请换端口: LTX2_COMFY_PORT=8189 ./scripts/ltx2/start_comfyui_ltx2.sh" >&2
  echo "  → 跳过本检查（不推荐）: LTX2_COMFY_ALLOW_PORT_CONFLICT=1 ..." >&2
  exit 1
fi

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
