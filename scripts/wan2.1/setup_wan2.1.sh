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
# 长步骤期间每隔 N 秒打印「仍在执行 + 已耗时」，便于判断是否卡死或 Ctrl+C 取消
WAN_SETUP_PROGRESS_INTERVAL="${WAN_SETUP_PROGRESS_INTERVAL:-15}"

log() { echo "[wan2.1-setup] $*"; }
die() { echo "[wan2.1-setup] 错误: $*" >&2; exit 1; }

# 在子进程中运行可能很久的命令，同时后台周期性输出进度（不替代 pip/hf 自带的进度条）
run_long_step() {
  local phase="$1"
  shift
  local start hb_pid rc interval elapsed
  interval="${WAN_SETUP_PROGRESS_INTERVAL}"
  start=$(date +%s)
  log "━━ 开始: ${phase}（Ctrl+C 可中止；约每 ${interval}s 提示已耗时）"
  (
    while true; do
      sleep "${interval}" || exit 0
      elapsed=$(($(date +%s) - start))
      echo "[wan2.1-setup] ⏳ ${phase} … 仍在执行，已 ${elapsed}s" >&2
    done
  ) &
  hb_pid=$!
  rc=0
  "$@" || rc=$?
  kill "${hb_pid}" 2>/dev/null || true
  wait "${hb_pid}" 2>/dev/null || true
  elapsed=$(($(date +%s) - start))
  if [[ "${rc}" -eq 0 ]]; then
    log "━━ 完成: ${phase}（耗时 ${elapsed}s）"
  else
    echo "[wan2.1-setup] ━━ 失败: ${phase}（耗时 ${elapsed}s，退出码 ${rc}）" >&2
  fi
  return "${rc}"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1"
}

# flash_attn 需从源码编译：必须存在 nvcc；CUDA_HOME 未设时可由 nvcc 路径推断
ensure_cuda_home_for_flash_attn() {
  if ! command -v nvcc >/dev/null 2>&1; then
    return 1
  fi
  if [[ -z "${CUDA_HOME:-}" ]]; then
    local nvcc_bin
    nvcc_bin="$(command -v nvcc)"
    export CUDA_HOME="$(cd "$(dirname "${nvcc_bin}")/.." && pwd)"
    log "未设置 CUDA_HOME，已从 nvcc 推断: CUDA_HOME=${CUDA_HOME}"
  fi
  return 0
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
  # --progress：即使部分环境下也会向 stderr 输出对象接收进度
  run_long_step "git clone Wan2.1" env GIT_TERMINAL_PROMPT=0 git clone --progress --depth 1 https://github.com/Wan-Video/Wan2.1.git "${WAN_REPO_DIR}"
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
  export PIP_PROGRESS_BAR="${PIP_PROGRESS_BAR:-on}"
  log "升级 pip…"
  run_long_step "pip 升级 pip/wheel/setuptools" pip install -U pip wheel setuptools
  log "安装 Wan2.1 依赖（耗时较长）…"
  # flash_attn 在构建 wheel 时会 import torch；pip 默认构建隔离环境里没有 torch，会报 ModuleNotFoundError。
  # 正确顺序：先装 torch/torchvision → 再装其余（去掉 flash_attn）→ 最后 flash_attn --no-build-isolation
  local req_no_fa="${WAN_BASE}/requirements.wan.no-flash-attn.txt"
  grep -vE '^\s*flash_attn(\s|$|#)' "${WAN_REPO_DIR}/requirements.txt" >"${req_no_fa}"
  if [[ -n "${WAN_TORCH_INDEX_URL:-}" ]]; then
    log "使用 WAN_TORCH_INDEX_URL 安装 PyTorch: ${WAN_TORCH_INDEX_URL}"
    run_long_step "pip 安装 PyTorch / torchvision（CUDA 专用源）" \
      pip install "torch>=2.4.0" "torchvision>=0.19.0" --index-url "${WAN_TORCH_INDEX_URL}"
  else
    run_long_step "pip 安装 PyTorch / torchvision（flash_attn 构建依赖）" \
      pip install "torch>=2.4.0" "torchvision>=0.19.0"
  fi
  run_long_step "pip install Wan2.1 依赖（不含 flash_attn）" pip install -r "${req_no_fa}"
  if [[ "${WAN_SKIP_FLASH_ATTN:-0}" == "1" ]]; then
    log "已跳过 flash_attn（WAN_SKIP_FLASH_ATTN=1）。若推理报错或速度异常，请在有 CUDA Toolkit（nvcc）的环境执行:"
    log "  source ${WAN_VENV}/bin/activate && export CUDA_HOME=/usr/local/cuda  # 按实际路径"
    log "  pip install flash_attn --no-build-isolation"
  elif ! ensure_cuda_home_for_flash_attn; then
    # 常见情况：仅有显卡驱动 + PyTorch 自带 CUDA 运行库，未安装完整 CUDA Toolkit，无法编译 flash_attn
    if [[ "${WAN_REQUIRE_FLASH_ATTN:-0}" == "1" ]]; then
      die "WAN_REQUIRE_FLASH_ATTN=1 但未在 PATH 中找到 nvcc。请安装 CUDA Toolkit（含 nvcc），并设置 CUDA_HOME，再执行本脚本。"
    fi
    log "⚠ 未检测到 nvcc（未装 CUDA Toolkit 或未加入 PATH），已自动跳过 flash_attn，venv 仍可用。"
    log "  PyTorch 已带 CUDA 运行时，Wan 推理多数可走 SDPA/eager；若运行时报缺 flash_attn，请安装 toolkit 后执行:"
    log "  sudo apt install nvidia-cuda-toolkit   # 或从 NVIDIA 安装与驱动匹配的 CUDA"
    log "  source ${WAN_VENV}/bin/activate && export CUDA_HOME=/usr/local/cuda"
    log "  pip install flash_attn --no-build-isolation"
  else
    log "正在安装 flash_attn（nvcc 可用，CUDA_HOME=${CUDA_HOME}）…"
    if ! run_long_step "pip 安装 flash_attn（--no-build-isolation）" pip install flash_attn --no-build-isolation; then
      echo "[wan2.1-setup] flash_attn 编译/安装失败（gcc 版本、CUDA 与 torch 不匹配等）。" >&2
      if [[ "${WAN_REQUIRE_FLASH_ATTN:-0}" == "1" ]]; then
        die "WAN_REQUIRE_FLASH_ATTN=1 且 flash_attn 安装失败，已中止。"
      fi
      echo "[wan2.1-setup] 已改为继续完成 venv（未安装 flash_attn）。需要时可手动安装或设置 WAN_SKIP_FLASH_ATTN=1 明确跳过。" >&2
    fi
  fi
  log "安装侧车所需 fastapi / uvicorn…"
  run_long_step "pip 安装侧车依赖（fastapi/uvicorn/httpx）" pip install "fastapi>=0.109" "uvicorn[standard]>=0.27" "httpx>=0.26"
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
  run_long_step "pip 安装/升级 huggingface_hub（含 hf CLI）" pip install -U "huggingface_hub"
  HF_CLI="${WAN_VENV}/bin/hf"
  if [[ ! -x "${HF_CLI}" ]]; then
    HF_CLI="${WAN_VENV}/bin/huggingface-cli"
  fi
  [[ -x "${HF_CLI}" ]] || die "venv 中未找到 hf / huggingface-cli，请检查 huggingface_hub 安装"
  log "从 Hugging Face 下载 ${WAN_HF_REPO} → ${WAN_CKPT_DIR}（使用 $(basename "${HF_CLI}")）"
  log "（体积大；终端会显示 HF 下载进度，并有周期性耗时提示；若需鉴权请 export HF_TOKEN=xxx）"
  mkdir -p "${WAN_CKPT_DIR}"
  # 保持进度条可见（部分 CI 会关进度条）
  export HF_HUB_DISABLE_PROGRESS_BARS="${HF_HUB_DISABLE_PROGRESS_BARS:-0}"
  if [[ -n "${HF_TOKEN:-}" ]]; then
    run_long_step "hf download 下载权重" "${HF_CLI}" download "${WAN_HF_REPO}" --local-dir "${WAN_CKPT_DIR}" --token "${HF_TOKEN}"
  else
    run_long_step "hf download 下载权重" "${HF_CLI}" download "${WAN_HF_REPO}" --local-dir "${WAN_CKPT_DIR}"
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
  WAN_SETUP_PROGRESS_INTERVAL  长步骤心跳间隔（秒），默认 15
  WAN_SKIP_FLASH_ATTN  设为 1 则跳过 flash_attn
  WAN_REQUIRE_FLASH_ATTN 设为 1 则必须有 nvcc 且 flash_attn 安装成功，否则中止
  WAN_TORCH_INDEX_URL  安装 torch 时使用，例如 CUDA 12.4:
                         https://download.pytorch.org/whl/cu124
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
