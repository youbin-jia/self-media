# LTX-2 部署脚本

详细说明见 **[docs/LTX2_LOCAL.md](../../docs/LTX2_LOCAL.md)**。  
**GitHub / Hugging Face 访问替代源**（镜像、代理、ZIP）：**[docs/MIRROR_SOURCES.md](../../docs/MIRROR_SOURCES.md)**。

## 快速下载 GGUF（Unsloth）

在仓库根目录：

```bash
chmod +x scripts/ltx2/download_ltx2_gguf.sh
./scripts/ltx2/download_ltx2_gguf.sh
```

环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `LTX2_GGUF_REPO` | `unsloth/LTX-2-GGUF` | Hugging Face 仓库 |
| `LTX2_GGUF_FILE` | `ltx-2-19b-dev-Q5_K_M.gguf` | 要下载的文件名 |
| `LTX2_MODELS_DIR` | `third_party/ltx2/models` | 本地保存目录 |
| `HF_TOKEN` | 空 | 需要时设置 |

**找不到 `hf` 命令**：执行 `pip install -U huggingface_hub`（1.7+ 不需要 `[cli]` extra）。若仍提示未找到，多半是 `~/.local/bin` 未在 `PATH` 中；本脚本会自动把该目录加入本次 `PATH`，或写入 `~/.bashrc`：`export PATH="$HOME/.local/bin:$PATH"`。

**无法连接 Hugging Face**（`Network is unreachable` 等）：先检查网络/VPN；或尝试 `export HF_ENDPOINT=https://hf-mirror.com` 后重跑下载脚本（镜像以当地可用为准）。

## 一键安装 ComfyUI + LTXVideo + ComfyUI-GGUF（推荐）

在仓库根目录（需已下载 GGUF，见上一节）：

```bash
chmod +x scripts/ltx2/setup_comfyui_ltx2.sh scripts/ltx2/start_comfyui_ltx2.sh
./scripts/ltx2/setup_comfyui_ltx2.sh
```

会安装到 **`third_party/ltx2/`**（已 `.gitignore`）：

| 路径 | 说明 |
|------|------|
| `venv-comfyui/` | 独立 Python 虚拟环境 |
| `ComfyUI/` | ComfyUI 本体 |
| `ComfyUI/custom_nodes/ComfyUI-Manager` | 扩展管理 |
| `ComfyUI/custom_nodes/ComfyUI-GGUF` | GGUF UNet 加载 |
| `ComfyUI/custom_nodes/ComfyUI-LTXVideo` | LTX-2 节点 |
| `ComfyUI/models/unet/*.gguf` | 指向你已下载文件的 **符号链接** |
| `comfy.runtime.env` | 可选 `source`，内含端口等变量 |

**GitHub 克隆失败**（超时 / Couldn't connect）：见 **[docs/MIRROR_SOURCES.md](../../docs/MIRROR_SOURCES.md)**。可任选：

```bash
export LTX2_GITHUB_MIRROR=ghproxy   # 或 mirror | kkgithub | gitclone
./scripts/ltx2/setup_comfyui_ltx2.sh

# 或自定义前缀（与部分代理站文档一致）：
export LTX2_GIT_PREFIX=https://ghproxy.net
./scripts/ltx2/setup_comfyui_ltx2.sh
```

启动 Web UI（默认端口 **8188**）：

```bash
./scripts/ltx2/start_comfyui_ltx2.sh
# 浏览器: http://127.0.0.1:8188
```

首次在 ComfyUI 里跑 LTX 工作流时，仍可能自动下载 **文本编码器** 等（体积大）；建议保持 `export HF_ENDPOINT=https://hf-mirror.com`（若你之前下载 GGUF 时用过）。

| 变量 | 默认 | 说明 |
|------|------|------|
| `LTX2_COMFY_PORT` | `8188` | ComfyUI 监听端口 |
| `LTX2_GITHUB_MIRROR` | 空 | `ghproxy` / `mirror` / `kkgithub` / `gitclone`，见 MIRROR_SOURCES.md |
| `LTX2_GIT_PREFIX` | 空 | 自定义克隆前缀（优先级高于 `LTX2_GITHUB_MIRROR`） |
| `LTX2_GGUF_FILE` | `ltx-2-19b-dev-Q5_K_M.gguf` | 与 `download_ltx2_gguf.sh` 一致，用于链接到 `models/unet/` |
| `LTX2_SKIP_GIT_CLONE` | `0` | 设为 `1` 时跳过 git，使用已按 **[docs/MIRROR_SOURCES.md](../../docs/MIRROR_SOURCES.md)** 放置的 ZIP 解压目录 |

## RTX 5070 Ti 16GB 备忘（1080p+、≥10s）

- **GGUF**：默认 `ltx-2-19b-dev-Q5_K_M.gguf`；OOM 时换 `Q5_K_S` / `Q4_K_M`。
- **分辨率**：用 **1920×1088**（不是 1920×1080）或 **2560×1440**（更吃显存）；须为 32 的倍数。
- **帧数**：须为 **8n+1**，例如 **24fps → 241 帧 ≈10.04s**；**30fps → 305 帧 ≈10.17s**。

详见 **[docs/LTX2_LOCAL.md](../../docs/LTX2_LOCAL.md)** 专节。

## 相关链接

- 官方代码：<https://github.com/Lightricks/LTX-2>
- GGUF 权重：<https://huggingface.co/unsloth/LTX-2-GGUF>
- ComfyUI 集成文档：<https://docs.ltx.video/open-source-model/integration-tools/comfy-ui>
