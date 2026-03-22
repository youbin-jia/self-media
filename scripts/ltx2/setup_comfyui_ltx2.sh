#!/usr/bin/env bash
# 在 third_party/ltx2/ 下安装 ComfyUI + ComfyUI-GGUF + ComfyUI-LTXVideo，并链接已下载的 LTX-2 GGUF。
# 用法：在仓库根目录执行  ./scripts/ltx2/setup_comfyui_ltx2.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BASE="${ROOT}/third_party/ltx2"
COMFY="${BASE}/ComfyUI"
VENV="${BASE}/venv-comfyui"
MODELS_DIR="${BASE}/models"
# 与 download_ltx2_gguf.sh 默认一致；可通过环境变量覆盖
GGUF_NAME="${LTX2_GGUF_FILE:-ltx-2-19b-dev-Q5_K_M.gguf}"
GGUF_PATH="${MODELS_DIR}/${GGUF_NAME}"
COMFY_PORT="${LTX2_COMFY_PORT:-8188}"

log() { echo "[ltx2-comfy-setup] $*"; }
die() { echo "[ltx2-comfy-setup] 错误: $*" >&2; exit 1; }

if [[ -d "${HOME}/.local/bin" ]]; then
  PATH="${HOME}/.local/bin:${PATH}"
  export PATH
fi

require_cmd() { command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1"; }

# GitHub 不可达时的替代方式（任选其一，优先级从高到低）：
#   1) export LTX2_GIT_PREFIX=https://ghproxy.net        # 自定义前缀，拼成「前缀 + 原 URL」
#   2) export LTX2_GITHUB_MIRROR=ghproxy|mirror|kkgithub|gitclone  # 内置常用镜像写法
#   3) git / 系统 HTTP 代理（见文档）
# 镜像多为第三方服务，可用性会变，以你当前网络实测为准。
_git_url() {
  local url="$1"
  if [[ -n "${LTX2_GIT_PREFIX:-}" ]]; then
    echo "${LTX2_GIT_PREFIX%/}/${url}"
    return 0
  fi
  case "${LTX2_GITHUB_MIRROR:-}" in
    ghproxy)
      echo "https://ghproxy.net/${url}"
      ;;
    mirror|ghproxy-mirror)
      echo "https://mirror.ghproxy.com/${url}"
      ;;
    kkgithub)
      echo "${url/https:\/\/github.com/https://kkgithub.com}"
      ;;
    gitclone)
      echo "${url/https:\/\/github.com/https://gitclone.com/github.com}"
      ;;
    "")
      echo "${url}"
      ;;
    *)
      die "未知的 LTX2_GITHUB_MIRROR=${LTX2_GITHUB_MIRROR}，请设为 ghproxy|mirror|kkgithub|gitclone 或使用 LTX2_GIT_PREFIX"
      ;;
  esac
}

clone_or_update() {
  local url="$1" dest="$2"
  url="$(_git_url "${url}")"
  if [[ -d "${dest}/.git" ]]; then
    log "已存在 git 仓库，尝试拉取: ${dest}"
    git -C "${dest}" pull --ff-only || log "git pull 失败（可忽略，继续用本地副本）"
  else
    rm -rf "${dest}"
    log "克隆: ${url}"
    if ! git clone --depth 1 "${url}" "${dest}"; then
      echo "" >&2
      echo "[ltx2-comfy-setup] Git 克隆失败。GitHub 不可达时可换源（详见 docs/MIRROR_SOURCES.md）：" >&2
      echo "  export LTX2_GITHUB_MIRROR=ghproxy   # 或 mirror | kkgithub | gitclone" >&2
      echo "  或: export LTX2_GIT_PREFIX=https://ghproxy.net" >&2
      echo "  或配置代理: git config --global http.https://github.com.proxy http://127.0.0.1:7890" >&2
      echo "  然后重新执行本脚本。" >&2
      exit 128
    fi
  fi
}

mkdir -p "${BASE}" "${MODELS_DIR}"

require_cmd python3

log "目标目录: ${BASE}"

# 1) ComfyUI 本体（可用浏览器下载 ZIP 解压到 ${COMFY}，再设 LTX2_SKIP_GIT_CLONE=1 跳过克隆）
if [[ "${LTX2_SKIP_GIT_CLONE:-0}" == "1" ]]; then
  log "跳过 git（LTX2_SKIP_GIT_CLONE=1），使用已解压目录"
  [[ -f "${COMFY}/requirements.txt" ]] || die "未找到 ${COMFY}/requirements.txt。请将 ComfyUI ZIP 解压并改名为 ComfyUI 放在 ${BASE}/（见 docs/MIRROR_SOURCES.md）"
else
  require_cmd git
  clone_or_update "https://github.com/comfyanonymous/ComfyUI.git" "${COMFY}"
  [[ -f "${COMFY}/requirements.txt" ]] || die "ComfyUI requirements.txt 不存在"
fi

# 2) 虚拟环境
if [[ ! -d "${VENV}" ]]; then
  log "创建 venv: ${VENV}"
  python3 -m venv "${VENV}"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
python -m pip install -U pip wheel setuptools

log "安装 ComfyUI 依赖（含 PyTorch，可能较慢）…"
pip install -r "${COMFY}/requirements.txt"

# 3) 自定义节点目录
CN="${COMFY}/custom_nodes"
mkdir -p "${CN}"

if [[ "${LTX2_SKIP_GIT_CLONE:-0}" == "1" ]]; then
  [[ -d "${CN}/ComfyUI-Manager" ]] || die "缺少 ${CN}/ComfyUI-Manager（浏览器 ZIP 解压后请去掉 -main 后缀并改名，见 docs/MIRROR_SOURCES.md）"
  [[ -d "${CN}/ComfyUI-GGUF" ]] || die "缺少 ${CN}/ComfyUI-GGUF"
  [[ -d "${CN}/ComfyUI-LTXVideo" ]] || die "缺少 ${CN}/ComfyUI-LTXVideo"
else
  clone_or_update "https://github.com/ltdrdata/ComfyUI-Manager.git" "${CN}/ComfyUI-Manager"
  clone_or_update "https://github.com/city96/ComfyUI-GGUF.git" "${CN}/ComfyUI-GGUF"
  clone_or_update "https://github.com/Lightricks/ComfyUI-LTXVideo.git" "${CN}/ComfyUI-LTXVideo"
fi

if [[ -f "${CN}/ComfyUI-GGUF/requirements.txt" ]]; then
  log "安装 ComfyUI-GGUF 依赖…"
  pip install -r "${CN}/ComfyUI-GGUF/requirements.txt"
fi
if [[ -f "${CN}/ComfyUI-LTXVideo/requirements.txt" ]]; then
  log "安装 ComfyUI-LTXVideo 依赖…"
  pip install -r "${CN}/ComfyUI-LTXVideo/requirements.txt"
fi

# 4) GGUF → ComfyUI/models/unet（ComfyUI-GGUF 文档约定）
UNET_DIR="${COMFY}/models/unet"
mkdir -p "${UNET_DIR}"
if [[ -f "${GGUF_PATH}" ]]; then
  TARGET="${UNET_DIR}/${GGUF_NAME}"
  if [[ -L "${TARGET}" ]] || [[ -f "${TARGET}" ]]; then
    rm -f "${TARGET}"
  fi
  ln -s "$(realpath "${GGUF_PATH}")" "${TARGET}"
  log "已链接 GGUF: ${TARGET} -> $(realpath "${GGUF_PATH}")"
else
  log "未找到 ${GGUF_PATH}，跳过链接。请先运行: ./scripts/ltx2/download_ltx2_gguf.sh"
fi

# 5) 运行时环境片段
RUNTIME_ENV="${BASE}/comfy.runtime.env"
cat >"${RUNTIME_ENV}" <<EOF
# 由 scripts/ltx2/setup_comfyui_ltx2.sh 生成；source 后再启动 ComfyUI
export LTX2_COMFY_ROOT="${COMFY}"
export LTX2_COMFY_VENV="${VENV}"
export LTX2_COMFY_PORT="${COMFY_PORT}"
# 下载模型仍可走镜像：
# export HF_ENDPOINT=https://hf-mirror.com
EOF
log "已写入: ${RUNTIME_ENV}"

log "完成。"
log "启动（监听所有网卡 ${COMFY_PORT}）:"
log "  source ${BASE}/comfy.runtime.env"
log "  ./scripts/ltx2/start_comfyui_ltx2.sh"
log "浏览器打开: http://127.0.0.1:${COMFY_PORT}"
log "示例工作流: ${CN}/ComfyUI-LTXVideo/example_workflows/ （若目录存在）"
