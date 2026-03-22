#!/usr/bin/env bash
# 启动 LTX/口播侧车（默认端口 9820，与 backend .env LTX2_T2V_ENDPOINT 一致）
#
# 接真实 LTX：在启动前 export，或复制 scripts/.env.ltx2.example → .env.ltx2 并填写。
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
if [[ -f "$DIR/.env.ltx2" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$DIR/.env.ltx2"
  set +a
fi
export LTX2_SIDECAR_PORT="${LTX2_SIDECAR_PORT:-9820}"
python3 -m pip install -q fastapi uvicorn httpx pydantic edge-tts 2>/dev/null || pip install -q fastapi uvicorn httpx pydantic edge-tts
exec python3 -m uvicorn ltx2_t2v_sidecar:app --host 0.0.0.0 --port "${LTX2_SIDECAR_PORT}"
