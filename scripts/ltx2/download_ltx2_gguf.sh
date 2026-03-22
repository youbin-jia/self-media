#!/usr/bin/env bash
# 下载 Unsloth 提供的 LTX-2 GGUF 到 third_party（不占 Git）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# pip install --user 时脚本常在 ~/.local/bin，许多发行版默认未加入 PATH
if [[ -d "${HOME}/.local/bin" ]]; then
  PATH="${HOME}/.local/bin:${PATH}"
  export PATH
fi

REPO="${LTX2_GGUF_REPO:-unsloth/LTX-2-GGUF}"
FILE="${LTX2_GGUF_FILE:-ltx-2-19b-dev-Q5_K_M.gguf}"
DEST="${LTX2_MODELS_DIR:-third_party/ltx2/models}"

mkdir -p "$DEST"

echo "仓库: $REPO"
echo "文件: $FILE"
echo "目录: $DEST"
if [[ -n "${HF_ENDPOINT:-}" ]]; then
  echo "HF_ENDPOINT: $HF_ENDPOINT"
fi
echo ""

_print_network_hints() {
  cat <<'HINT' >&2

【下载失败】若日志中出现 Network is unreachable / 连接超时：
  1) 检查本机网络、是否需要 VPN、公司防火墙是否拦截 huggingface.co
  2) 使用镜像（huggingface_hub 会读取环境变量 HF_ENDPOINT），例如：
       export HF_ENDPOINT=https://hf-mirror.com
     然后重新执行本脚本（镜像可用性请自行核实）
  3) 或配置代理后再试：
       export HTTPS_PROXY=http://127.0.0.1:7890

安装 CLI：新版包一般已自带 hf 命令，无需 [cli] 额外依赖：
  pip install -U huggingface_hub
HINT
}

run_download() {
  # 新版 huggingface_hub 提供 hf；旧版可能是 huggingface-cli；均可 python -m 调用
  if command -v hf >/dev/null 2>&1; then
    hf download "$REPO" "$FILE" --local-dir "$DEST"
  elif command -v huggingface-cli >/dev/null 2>&1; then
    huggingface-cli download "$REPO" "$FILE" --local-dir "$DEST"
  elif python3 -c "import huggingface_hub" 2>/dev/null; then
    python3 -m huggingface_hub.cli.hf download "$REPO" "$FILE" --local-dir "$DEST"
  else
    echo "未找到 hf / huggingface-cli，且当前 python3 未安装 huggingface_hub。" >&2
    echo "请安装：" >&2
    echo "  pip install -U huggingface_hub" >&2
    echo "  pip install --user -U huggingface_hub   # 若 hf 在 ~/.local/bin，脚本已尝试加入 PATH" >&2
    return 127
  fi
}

set +e
run_download
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  _print_network_hints
  exit "$rc"
fi

echo ""
echo "完成。请将 .gguf 按 ComfyUI / LTX 节点文档放入 ComfyUI 的模型目录。"
echo "说明: docs/LTX2_LOCAL.md"
