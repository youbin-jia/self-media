# LTX-2 本地部署（音画一体 / GGUF 量化）

**LTX-2**（Lightricks）是 DiT 架构的**音视频联合生成**模型：一次推理可产出**带画面 + 环境音/对白**的短片，支持高分辨率与多阶段放大。官方论文与权重说明见 [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2)、代码库 [github.com/Lightricks/LTX-2](https://github.com/Lightricks/LTX-2)。

> **与本仓库关系**：当前自媒体后端流水线以 **脚本 + TTS + Wan I2V 拼接** 为主；**尚未内置 LTX-2 HTTP API**。本文档用于在你自己的 GPU 机器上部署；若需接入平台，可仿照 `scripts/wan_i2v_sidecar.py` 做「侧车」封装后再接 `backend`。

---

## RTX 5070 Ti 16GB：推荐参数（≥1080p 类、≥10s）

你的目标：**分辨率不低于 1080p 观感、时长 ≥10 秒**。LTX-2 对 **宽高**、**帧数**有硬约束，需先在 ComfyUI/工作流里设对，否则易报错或被迫降规格。

### 权重（GGUF）

| 优先级 | 文件（`unsloth/LTX-2-GGUF`） | 说明 |
|--------|------------------------------|------|
| **首选** | `ltx-2-19b-dev-Q5_K_M.gguf` | 单文件约 **14GB 级**，给 16GB 显存留激活/图缓存空间（与脚本默认一致）。 |
| 显存吃紧 / OOM | `ltx-2-19b-dev-Q5_K_S.gguf` 或 `Q4_K_M.gguf` | 略降质换稳。 |
| 不建议首试 | `Q6_K`（单文件约 **16GB**） | 在 **16GB 卡**上极易 **OOM**，除非工作流极省显存且你已关闭其它占显存程序。 |

驱动与栈：5070 Ti 为 **Blackwell**，请用 **较新的 NVIDIA 驱动**；ComfyUI / PyTorch 需支持你当前 CUDA 版本（以各项目发行说明为准）。

### 分辨率（「1080p 以上」且满足 32 倍数）

**标准 1920×1080 不合规**（1080 不是 32 的倍数）。可选用：

| 档位 | 分辨率 | 宽高 ÷32 | 说明 |
|------|--------|----------|------|
| **推荐首试** | **1920 × 1088** | 60 × 34 | 最接近 1080p；竖直多 8px，导出时可裁回 1080 或加细黑边。 |
| 略矮一点（仍算 FHD 类） | **1920 × 1056** | 60 × 33 | 全程可严格 32 对齐。 |
| **高于 1080p** | **2560 × 1440** | 80 × 45 | **2K/1440p** 数学上合规；5070 Ti 16GB 上 **可能偏吃紧**，若 OOM 请降回 **1920×1088** 或改 **Q4**。 |

更高（接近 4K）通常建议走官方多阶段 + **spatial upscaler**，单段直出 4K 对 16GB 不现实。

### 时长 ≥10 秒（帧数 = 8n + 1）

帧数须为 **8 的倍数 + 1**。与常见 fps 搭配示例：

| fps | 合规总帧数（示例） | 约时长 |
|-----|-------------------|--------|
| **24** | **241**（= 8×30+1） | ≈ **10.04 s** |
| 25 | 249（= 8×31+1） | ≈ 9.96 s；或 **257** ≈ 10.28 s |
| 30 | **305**（= 8×38+1） | ≈ **10.17 s** |

在 ComfyUI 里把 **帧数** 设为表中数值即可满足「≥10s」且合规；不要直接填「正好 240 帧 @24fps」这类 **8n**（不满足 +1）。

### 一键下载（与默认权重一致）

```bash
./scripts/ltx2/download_ltx2_gguf.sh
# 等价于 Q5_K_M；若 OOM 再换：
# LTX2_GGUF_FILE=ltx-2-19b-dev-Q5_K_S.gguf ./scripts/ltx2/download_ltx2_gguf.sh
```

---

## 部署路线怎么选

| 路线 | 适用场景 | 显存参考 | 说明 |
|------|-----------|----------|------|
| **A. ComfyUI + GGUF**（本文推荐） | 要 **16GB 级显卡** 尽量流畅、用社区量化 | **约 12–16GB** 建议 **Q5_K_M / Q5_K_S**；Q6_K 单文件约 16GB，整卡 16GB 易 OOM | 使用 [unsloth/LTX-2-GGUF](https://huggingface.co/unsloth/LTX-2-GGUF) + ComfyUI 内置/扩展节点 |
| **B. 官方 PyTorch（uv）** | 要完整管线、可训练、与官方示例一致 | BF16 约 **38GB+**；可配合官方 FP8/蒸馏权重降显存 | Python **≥3.12**，CUDA **>12.7**，PyTorch **≈2.7**，见官方仓库 |

**4K / 更高清**：官方提供 **spatial / temporal upscaler** 等多阶段组件（见 HF 模型卡「Model Checkpoints」表），需在对应路线里单独下载并接入工作流，不是单文件 GGUF 直接「一键 4K」。

---

## A. ComfyUI + GGUF（推荐，16GB 友好）

### 1. 准备目录与权重

在仓库根目录执行（权重落在 `third_party/`，已在 `.gitignore`）：

```bash
# 若提示找不到 hf：安装 huggingface_hub（1.7+ 已内置 hf，无需再写 [cli]，写了会提示 extra 不存在）
pip install -U huggingface_hub
# 若用 pip install --user，请把 ~/.local/bin 加入 PATH，或依赖脚本已自动前置该目录

# 若无法访问 huggingface.co（超时 / Network is unreachable），可试镜像（自行核实可用性）：
# export HF_ENDPOINT=https://hf-mirror.com

chmod +x scripts/ltx2/download_ltx2_gguf.sh

# 默认下载 Q5_K_M（约 14GB 级，16GB 显存较稳）
./scripts/ltx2/download_ltx2_gguf.sh

# 指定量化（示例：更省显存）
LTX2_GGUF_FILE=ltx-2-19b-dev-Q4_K_M.gguf ./scripts/ltx2/download_ltx2_gguf.sh

# 需要登录的私有/限速场景
# export HF_TOKEN=hf_xxx
```

### 2. 安装 ComfyUI 与节点（推荐：仓库一键脚本）

在仓库根目录执行（需已用上一节下载好 GGUF）：

```bash
chmod +x scripts/ltx2/setup_comfyui_ltx2.sh scripts/ltx2/start_comfyui_ltx2.sh
./scripts/ltx2/setup_comfyui_ltx2.sh
./scripts/ltx2/start_comfyui_ltx2.sh
```

脚本会安装 **ComfyUI**、**ComfyUI-Manager**、**ComfyUI-GGUF**、**ComfyUI-LTXVideo** 到 `third_party/ltx2/`，并把 `third_party/ltx2/models/*.gguf` **符号链接**到 **`ComfyUI/models/unet/`**（与 [ComfyUI-GGUF 说明](https://github.com/city96/ComfyUI-GGUF) 一致）。

- **GitHub 连不上**：可使用 **多种镜像/代理**，见 **[docs/MIRROR_SOURCES.md](MIRROR_SOURCES.md)**。安装脚本支持例如：`export LTX2_GITHUB_MIRROR=ghproxy` 或 `export LTX2_GIT_PREFIX=https://ghproxy.net` 后重跑 `setup_comfyui_ltx2.sh`。
- **首次跑工作流** 仍可能下载 **Gemma 等文本编码器**（体积大），可继续用 `HF_ENDPOINT=https://hf-mirror.com`。

更多变量见 **`scripts/ltx2/README.md`**。

### 2b. 手动安装（可选）

1. 安装 [ComfyUI](https://github.com/comfyanonymous/ComfyUI)（官方仓库说明为准）。
2. 使用 **ComfyUI Manager** 安装 **LTXVideo** 相关节点（Lightricks 文档：[Comfy UI 集成](https://docs.ltx.video/open-source-model/integration-tools/comfy-ui)）。
3. GGUF 加载依赖 **ComfyUI-GGUF**（[city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF)）；将 `.gguf` 放在 **`ComfyUI/models/unet/`**。

### 3. 使用提示（官方约束摘要）

- 宽高需为 **32 的倍数**；帧数需满足 **8 的倍数 + 1**（与官方模型卡一致）。
- 提示词技巧见 [LTX 官方 Prompt 指南](https://ltx.video/blog/how-to-prompt-for-ltx-2)。

### 4. 量化文件怎么选（GGUF）

仓库 [unsloth/LTX-2-GGUF](https://huggingface.co/unsloth/LTX-2-GGUF) 中 `ltx-2-19b-dev-*.gguf` 多种量化：

- **16GB 显卡**：优先 **Q5_K_M** 或 **Q5_K_S**，留显存给激活与 UI。
- **更低显存**：**Q4_K_M / Q4_K_S**。
- **Q6_K / Q8_0 / BF16**：文件更大，适合更大显存或台式工作站。

另有 **UD-**（Unsloth Dynamic 2.0）变体，可按 HF 页面体积与说明选择。

---

## B. 官方 PyTorch 仓库（完整能力）

适合开发、多阶段放大、与官方 pipeline 对齐（非 GGUF）。

```bash
git clone https://github.com/Lightricks/LTX-2.git
cd LTX-2
uv sync
source .venv/bin/activate
```

具体推理命令见仓库内 [`packages/ltx-pipelines/README.md`](https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-pipelines/README.md)。

**Diffusers** 路线见 [Hugging Face Diffusers 文档](https://huggingface.co/docs/diffusers) 中 LTX-2 / image-to-video 相关章节（以当前 diffusers 版本为准）。

---

## 许可与合规

使用权重前请阅读 [Hugging Face 模型 LICENSE](https://huggingface.co/Lightricks/LTX-2/blob/main/LICENSE) 及 GGUF 衍生仓库许可；生成内容需符合本地法律法规与平台政策。

---

## 脚本索引

| 路径 | 说明 |
|------|------|
| `scripts/ltx2/download_ltx2_gguf.sh` | 从 HF 下载指定 GGUF 到 `third_party/ltx2/models/` |
| `scripts/ltx2/setup_comfyui_ltx2.sh` | 安装 ComfyUI + Manager + GGUF + LTXVideo，并链接 GGUF |
| `scripts/ltx2/start_comfyui_ltx2.sh` | 启动 ComfyUI（默认端口 8188） |
| `scripts/ltx2/README.md` | 简短命令备忘 |

---

## 后续接入本平台的思路（可选）

1. 在 GPU 机器上固定 ComfyUI API 或自写 **侧车**：接收 `prompt` / 分辨率 / 秒数，返回 `mp4`。
2. 在 `backend/.env` 增加类似 `LTX2_*` 的 endpoint 配置，新建 `app/services/ltx2/client.py` 调用侧车。
3. 在工作流「视频步」中增加策略：全片音画一体生成 vs 现有分镜+TTS+拼接。

其它显卡可参考上文 **「帧数 = 8n+1」** 与 **「宽高为 32 倍数」** 两规则自行换算。
