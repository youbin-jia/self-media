#!/usr/bin/env bash
# 自检：后端 pipeline-env + 侧车 /health + 可选 POST /generate（口播兜底）
# 用法：BACKEND=http://127.0.0.1:8000 SIDECAR=http://127.0.0.1:9820 ./verify_ltx2_stack.sh
set -euo pipefail
BACKEND="${BACKEND:-http://127.0.0.1:8000}"
SIDECAR="${SIDECAR:-http://127.0.0.1:9820}"

echo "== GET ${BACKEND}/api/video/pipeline-env =="
curl -sS -m 10 "${BACKEND}/api/video/pipeline-env" | python3 -m json.tool | head -60

echo ""
echo "== GET ${SIDECAR}/health =="
curl -sS -m 5 "${SIDECAR}/health" | python3 -m json.tool

if [[ "${VERIFY_GENERATE:-}" == "1" ]]; then
  echo ""
  echo "== POST ${SIDECAR}/generate (口播兜底，约数秒) =="
  OUT="${TMPDIR:-/tmp}/ltx2_stack_verify_$$.mp4"
  curl -sS -m 180 -X POST "${SIDECAR}/generate" \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"stack verify","narration":"验证侧车","duration_sec":2.5,"width":1920,"height":1088,"fps":24,"frames":57}' \
    -o "$OUT"
  file "$OUT"
  ls -la "$OUT"
fi

echo ""
echo "完成。若 comfy_ready_for_real_ltx 为 false：请将 API JSON 放到 third_party/ltx2/workflows/ltx2_t2v.api.json 并重启侧车。"
