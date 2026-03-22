#!/usr/bin/env bash
# 检查视频管线 / 通义万相环境（需后端已启动）
set -euo pipefail
BASE="${VIDEO_API_BASE:-http://127.0.0.1:8000}"
echo "GET ${BASE}/api/video/pipeline-env"
curl -sS "${BASE}/api/video/pipeline-env" | python3 -m json.tool 2>/dev/null || curl -sS "${BASE}/api/video/pipeline-env"
echo
