#!/usr/bin/env bash
# 将 third_party/ltx2/models 下的权重符号链接到 ComfyUI 标准目录（与官方 LTX 模板 / 节点一致）
# 在仓库根目录执行: ./scripts/ltx2/link_ltx_models_to_comfy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SOURCE="${LTX2_MODELS_DIR:-$ROOT/third_party/ltx2/models}"
COMFY="${ROOT}/third_party/ltx2/ComfyUI"
MD="$COMFY/models"

if [[ ! -d "$COMFY" ]]; then
  echo "未找到 ComfyUI: $COMFY ，请先运行: ./scripts/ltx2/setup_comfyui_ltx2.sh" >&2
  exit 1
fi

mkdir -p "$MD/checkpoints" "$MD/loras" "$MD/text_encoders" \
  "$MD/upscale_models" "$MD/latent_upscale_models" "$MD/unet"

link_one() {
  local name="$1"
  local dest_dir="$2"
  if [[ ! -f "$SOURCE/$name" ]]; then
    echo "[link] 跳过（源文件不存在）: $SOURCE/$name"
    return 0
  fi
  local dest="$dest_dir/$name"
  rm -f "$dest"
  ln -sf "$(realpath "$SOURCE/$name")" "$dest"
  echo "[link] $dest -> $(realpath "$SOURCE/$name")"
}

echo "[link] 源目录: $SOURCE"
echo "[link] ComfyUI: $COMFY"
echo ""

# 主模型：模板里 ckpt_name 选这个（不要用 ltx-2-100-*，与你下载的 19B 不一致）
link_one "ltx-2-19b-dev-fp8.safetensors" "$MD/checkpoints"

# LoRA（蒸馏 / 运镜等，模板若引用则需在 loras 下可见）
link_one "ltx-2-19b-distilled-lora-384.safetensors" "$MD/loras"
link_one "ltx-2-19b-lora-camera-control-dolly-left.safetensors" "$MD/loras"

# 空间放大：部分 LTX 节点列在「Latent Upscale」里，只认 latent_upscale_models；
# 另一些走 upscale_models。两处都链同一份文件，避免弹窗 missing。
link_one "ltx-2-spatial-upscaler-x2-1.0.safetensors" "$MD/upscale_models"
link_one "ltx-2-spatial-upscaler-x2-1.0.safetensors" "$MD/latent_upscale_models"

# 文本编码：单文件 .safetensors 供部分路径使用；完整 Gemma 目录见 docs/LTX2_COMFY_TEMPLATE.md
link_one "gemma_3_12B_it_fp4_mixed.safetensors" "$MD/text_encoders"

# GGUF（若仍用 ComfyUI-GGUF 工作流）
link_one "ltx-2-19b-dev-Q5_K_M.gguf" "$MD/unet"

echo ""
echo "[link] 完成。请在 ComfyUI 模板中将 ckpt_name 改为: ltx-2-19b-dev-fp8.safetensors"
