#!/usr/bin/env bash
# 从 Lightricks 官方仓库下载 LTX-2.0 T2V Distilled UI 工作流（非 API 格式）。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${DIR}/bundled_workflows/LTX-2_T2V_Distilled_wLora.ui.json"
mkdir -p "$(dirname "$OUT")"
URL="https://raw.githubusercontent.com/Lightricks/ComfyUI-LTXVideo/master/example_workflows/2.0/LTX-2_T2V_Distilled_wLora.json"
echo "Fetching -> $OUT"
curl -fsSL -o "$OUT" "$URL"
wc -c "$OUT"
echo "随后在 ComfyUI 中 Load 此文件，Queue 跑通后 Save (API Format) 为 ltx2_t2v.api.json（见 third_party/ltx2/workflows/README.md）。"
