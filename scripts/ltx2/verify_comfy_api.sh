#!/usr/bin/env bash
# 验证本机 ComfyUI HTTP API 可用（无需登录的简单探测）
# 用法: COMFY_API_BASE=http://127.0.0.1:8188 ./scripts/ltx2/verify_comfy_api.sh
set -euo pipefail

BASE="${COMFY_API_BASE:-http://127.0.0.1:8188}"
BASE="${BASE%/}"

echo "== ComfyUI API 探测: ${BASE} =="

code="$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/" || true)"
echo "GET ${BASE}/  -> HTTP ${code}"

code_info="$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/object_info" || true)"
echo "GET ${BASE}/object_info -> HTTP ${code_info}"

if [[ "$code_info" != "200" ]]; then
  echo "错误: object_info 非 200，请确认 ComfyUI 已启动: ./scripts/ltx2/start_comfyui_ltx2.sh" >&2
  exit 1
fi

# 节点数量（JSON 顶层 key 数）
n="$(curl -sf "${BASE}/object_info" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")"
echo "object_info 中注册的节点类型数: ${n}"

code_q="$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/queue" || true)"
echo "GET ${BASE}/queue -> HTTP ${code_q}"

echo ""
echo "API 可用。提交工作流请使用 POST ${BASE}/prompt（需完整 workflow JSON，建议从界面 Export API 获取）。"
echo "参考: docs/LTX2_COMFY_TEMPLATE.md"
