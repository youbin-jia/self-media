#!/usr/bin/env bash
# Wan2.1 I2V 本地部署：克隆仓库、Python 虚拟环境、可选下载权重、生成 .env 片段。
# 用法见 scripts/wan2.1/README.md
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WAN_BASE="${ROOT_DIR}/third_party/wan2.1"
WAN_REPO_DIR="${WAN_BASE}/Wan2.1"
WAN_VENV="${WAN_BASE}/venv-wan"
WAN_CKPT_DIR="${WAN_BASE}/Wan2.1-I2V-14B-720P"
WAN_HF_REPO="${WAN_HF_REPO:-Wan-AI/Wan2.1-I2V-14B-720P}"
BACKEND_ENV_SNIPPET="${ROOT_DIR}/backend/.env.wan.generated"
RUNTIME_ENV="${WAN_BASE}/wan.runtime.env"
SIDECAR_PORT="${WAN_SIDECAR_PORT:-9810}"

log() { echo "[wan2.1-setup] $*"; }
die() { echo "[wan2.1-setup] 错误: $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1"
}

cmd_install_repo() {
  require_cmd git
  mkdir -p "${WAN_BASE}"
  if [[ -d "${WAN_REPO_DIR}/.git" ]]; then
    if [[ -f "${WAN_REPO_DIR}/generate.py" ]]; then
      log "仓库已存在: ${WAN_REPO_DIR}"
      return 0
    fi
    log "检测到不完整克隆（无 generate.py），将删除后重拉: ${WAN_REPO_DIR}"
    rm -rf "${WAN_REPO_DIR}"
  elif [[ -d "${WAN_REPO_DIR}" ]]; then
    die "目录已存在但不是 git 仓库: ${WAN_REPO_DIR}"
  fi
  log "克隆 Wan-Video/Wan2.1 → ${WAN_REPO_DIR}"
  git clone --depth 1 https://github.com/Wan-Video/Wan2.1.git "${WAN_REPO_DIR}"
  [[ -f "${WAN_REPO_DIR}/generate.py" ]] || die "克隆失败或网络中断，请删除目录后重试: ${WAN_REPO_DIR}"
}

cmd_venv() {
  require_cmd python3
  cmd_install_repo
  [[ -f "${WAN_REPO_DIR}/requirements.txt" ]] || die "未找到 requirements.txt，请先 install-repo"
  if [[ ! -d "${WAN_VENV}" ]]; then
    log "创建虚拟环境: ${WAN_VENV}"
    python3 -m venv "${WAN_VENV}"
  fi
  # shellcheck disable=SC1091
  source "${WAN_VENV}/bin/activate"
  log "升级 pip…"
  pip install -U pip wheel setuptools
  log "安装 Wan2.1 依赖（耗时较长）…"
  pip install -r "${WAN_REPO_DIR}/requirements.txt"
  log "安装侧车所需 fastapi / uvicorn…"
  pip install "fastapi>=0.109" "uvicorn[standard]>=0.27" "httpx>=0.26"
  deactivate || true
  log "venv 就绪: ${WAN_VENV}"
}

cmd_download() {
  require_cmd python3
  if [[ ! -d "${WAN_VENV}" ]]; then
    die "请先运行: $0 venv"
  fi
  # shellcheck disable=SC1091
  source "${WAN_VENV}/bin/activate"
  pip install -U "huggingface_hub[cli]"
  log "从 Hugging Face 下载 ${WAN_HF_REPO} → ${WAN_CKPT_DIR}"
  log "（体积大，请耐心等待；若需鉴权请 export HF_TOKEN=xxx）"
  mkdir -p "${WAN_CKPT_DIR}"
  if [[ -n "${HF_TOKEN:-}" ]]; then
    huggingface-cli download "${WAN_HF_REPO}" --local-dir "${WAN_CKPT_DIR}" --token "${HF_TOKEN}"
  else
    huggingface-cli download "${WAN_HF_REPO}" --local-dir "${WAN_CKPT_DIR}"
  fi
  deactivate || true
  log "权重目录: ${WAN_CKPT_DIR}"
}

cmd_env_snippet() {
  [[ -d "${WAN_REPO_DIR}" ]] || die "请先 install-repo"
  PY="${WAN_VENV}/bin/python"
  [[ -x "${PY}" ]] || die "请先 venv（缺少 ${PY}）"

  REPO_ABS="$(cd "${WAN_REPO_DIR}" && pwd)"
  CKPT_ABS="$(cd "${WAN_BASE}" && pwd)/Wan2.1-I2V-14B-720P"

  mkdir -p "${WAN_BASE}"
  cat > "${RUNTIME_ENV}" <<EOF
# 由 scripts/wan2.1/setup_wan2.1.sh 生成 — 供 start_wan_sidecar.sh 使用
export WAN_I2V_REPO_DIR="${REPO_ABS}"
export WAN_I2V_CKPT_DIR="${CKPT_ABS}"
export WAN_I2V_PYTHON="${PY}"
export WAN_SIDECAR_PORT="${SIDECAR_PORT}"
# 显存紧张时可取消下一行注释：
# export WAN_I2V_EXTRA_ARGS="--offload_model True --t5_cpu"
EOF

  if [[ ! -d "${CKPT_ABS}" ]] || [[ -z "$(ls -A "${CKPT_ABS}" 2>/dev/null || true)" ]]; then
    log "警告: 权重目录为空，请先运行: $0 download"
  fi

  TS="$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')"
  cat > "${BACKEND_ENV_SNIPPET}" <<EOF
# --- Wan2.1 I2V（追加到 backend/.env）---
# 生成时间: ${TS}
WAN_I2V_ENABLED=true
WAN_I2V_MODE=http
WAN_I2V_ENDPOINT=http://127.0.0.1:${SIDECAR_PORT}
WAN_I2V_TIMEOUT_SEC=7200

# 同机不用侧车时，可改为 subprocess 并启用下面几行（注释掉上面 WAN_I2V_MODE/ENDPOINT）
# WAN_I2V_MODE=subprocess
# WAN_I2V_REPO_DIR=${REPO_ABS}
# WAN_I2V_CKPT_DIR=${CKPT_ABS}
# WAN_I2V_PYTHON=${PY}
# WAN_I2V_TASK=i2v-14B
# WAN_I2V_SIZE=1280*720
# WAN_I2V_EXTRA_ARGS=--offload_model True --t5_cpu
EOF

  log "已写入侧车运行时环境: ${RUNTIME_ENV}"
  log "已写入 API 合并片段: ${BACKEND_ENV_SNIPPET}"
  echo ""
  echo ">>> 下一步："
  echo "    1) 若尚未下载权重: ./scripts/wan2.1/setup_wan2.1.sh download"
  echo "    2) 合并环境变量:   cat ${BACKEND_ENV_SNIPPET} >> backend/.env"
  echo "    3) 启动侧车:       ./scripts/wan2.1/start_wan_sidecar.sh"
  echo "    4) 启动主 API（原流程）"
}

cmd_all() {
  local skip_dl=0
  for a in "$@"; do
    [[ "$a" == "--skip-download" ]] && skip_dl=1
  done
  cmd_install_repo
  cmd_venv
  if [[ "${skip_dl}" -eq 0 ]] && [[ "${WAN_AUTO_DOWNLOAD:-}" == "1" ]]; then
    cmd_download
  fi
  cmd_env_snippet
}

print_usage() {
  cat <<EOF
用法: $(basename "$0") <子命令>

子命令:
  install-repo   克隆 Wan2.1 官方仓库到 third_party/wan2.1/Wan2.1
  venv           创建 venv 并安装 requirements.txt + 侧车依赖
  download       使用 huggingface-cli 下载 I2V-14B-720P 权重
  env-snippet    生成 wan.runtime.env 与 backend/.env.wan.generated
  all            install-repo + venv + env-snippet（不加下载）
                 可加 --skip-download（默认即不下载）；若 export WAN_AUTO_DOWNLOAD=1 则 all 会尝试 download

环境变量:
  HF_TOKEN       Hugging Face 令牌（可选）
  WAN_HF_REPO    默认 ${WAN_HF_REPO}
  WAN_SIDECAR_PORT 侧车端口，默认 ${SIDECAR_PORT}
EOF
}

main() {
  local sub="${1:-}"
  shift || true
  case "${sub}" in
    install-repo) cmd_install_repo ;;
    venv) cmd_venv ;;
    download) cmd_download ;;
    env-snippet) cmd_env_snippet ;;
    all) cmd_all "$@" ;;
    ""|-h|--help|help) print_usage ;;
    *) die "未知子命令: ${sub}（使用 --help）" ;;
  esac
}

main "$@"
