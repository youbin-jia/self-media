#!/usr/bin/env bash
# 启动 Wan2.1 I2V HTTP 侧车（需先运行 setup_wan2.1.sh）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_ENV="${ROOT_DIR}/third_party/wan2.1/wan.runtime.env"

if [[ ! -f "${RUNTIME_ENV}" ]]; then
  echo "未找到 ${RUNTIME_ENV}"
  echo "请先执行: ./scripts/wan2.1/setup_wan2.1.sh all --skip-download"
  echo "           ./scripts/wan2.1/setup_wan2.1.sh env-snippet"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${RUNTIME_ENV}"
set +a

CKPT="${WAN_I2V_CKPT_DIR:-}"
if [[ -z "${CKPT}" ]] || [[ ! -d "${CKPT}" ]] || [[ -z "$(ls -A "${CKPT}" 2>/dev/null || true)" ]]; then
  echo "警告: 权重目录为空。侧车启动后 /health 会失败，请先:"
  echo "  ./scripts/wan2.1/setup_wan2.1.sh download"
fi

export WAN_I2V_REPO_DIR WAN_I2V_CKPT_DIR WAN_I2V_PYTHON

PY="${WAN_I2V_PYTHON:-python3}"
if [[ ! -x "${PY}" ]]; then
  echo "WAN_I2V_PYTHON 无效: ${PY}"
  exit 1
fi

echo "[wan-sidecar] WAN_I2V_REPO_DIR=${WAN_I2V_REPO_DIR}"
echo "[wan-sidecar] WAN_I2V_CKPT_DIR=${WAN_I2V_CKPT_DIR}"
echo "[wan-sidecar] 使用 Python: ${PY}"
echo "[wan-sidecar] 监听端口: ${WAN_SIDECAR_PORT:-9810}"
exec "${PY}" "${ROOT_DIR}/scripts/wan_i2v_sidecar.py"
