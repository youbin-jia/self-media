# LTX-2 ComfyUI 模板对齐说明（与当前下载的 19B 权重）

你在模板广场打开的 **「Text to Video (LTX 2.0)」** 默认写的是 **`ltx-2-100-dev-fp8.safetensors`**。  
本仓库脚本与 HF 实际常见命名是 **19B**：**`ltx-2-19b-dev-fp8.safetensors`**，需要 **在模板里改 ckpt**，并把文件放到 ComfyUI 能扫到的目录。

---

## 1. 一键链接模型到 ComfyUI 目录

在仓库根目录执行：

```bash
chmod +x scripts/ltx2/link_ltx_models_to_comfy.sh
./scripts/ltx2/link_ltx_models_to_comfy.sh
```

会把 `third_party/ltx2/models/` 下的文件链到：

| 文件 | ComfyUI 目录 |
|------|----------------|
| `ltx-2-19b-dev-fp8.safetensors` | `models/checkpoints/` |
| `ltx-2-19b-distilled-lora-384.safetensors` | `models/loras/` |
| `ltx-2-19b-lora-camera-control-dolly-left.safetensors` | `models/loras/` |
| `ltx-2-spatial-upscaler-x2-1.0.safetensors` | `models/upscale_models/` **与** `models/latent_upscale_models/`（LTX 模板常从后者下拉框读；两处都要有或链过去） |
| `gemma_3_12B_it_fp4_mixed.safetensors` | `models/text_encoders/` |
| `ltx-2-19b-dev-Q5_K_M.gguf` | `models/unet/`（GGUF 工作流用） |

---

## 2. 在模板里要改的地方

1. **`ckpt_name`**（或主模型下拉框）  
   - 改为：**`ltx-2-19b-dev-fp8.safetensors`**  
   - **不要**再用 **`ltx-2-100-dev-fp8.safetensors`**（与你磁盘上的 19B 文件不是同一套命名）。

2. **`width` / `height`**  
   - 宽高都必须是 **32 的倍数**。  
   - 例如 **1280×720 不合法**（720 不是 32 的倍数）。可改为 **1280×736** 或 **1280×704**。

3. **帧数 / 时长**  
   - 总帧数需满足 **8n+1**（与 LTX 模型约束一致）。  
   - 例如 **24fps、约 10 秒 → 241 帧**。

4. **LoRA / Upscaler**（若节点里有下拉框）  
   - 链接脚本已把蒸馏 LoRA、运镜 LoRA、spatial upscaler 放进对应目录，在列表里选与你文件名一致的一项即可。

---

## 3. Gemma 文本编码（重要）

**「LTXV Gemma CLIP Loader」** 类节点会在 `text_encoders` 下列目录，并在目录树里查找 **`tokenizer.model`**、`model*.safetensors` 等（类似 HuggingFace 快照布局）。

若你只有一个 **`gemma_3_12B_it_fp4_mixed.safetensors`** 单文件：

- **简化模板**若把 Gemma 包在子图里且能自动拉取，可能仍能跑；  
- 若报错缺 **tokenizer** / **config**，请从 Hugging Face 下载 **完整 Gemma-3 目录** 到例如：  
  `ComfyUI/models/text_encoders/gemma-3-12b-it/`（内含 tokenizer 与权重，具体仓库名以 Lightricks / 官方 Comfy 文档为准）。

---

## 4. 验证 ComfyUI HTTP API

ComfyUI 启动后（默认 **8188**）：

```bash
chmod +x scripts/ltx2/verify_comfy_api.sh
./scripts/ltx2/verify_comfy_api.sh
# 或
COMFY_API_BASE=http://127.0.0.1:8188 ./scripts/ltx2/verify_comfy_api.sh
```

期望：`GET /object_info` 返回 **HTTP 200**，并打印节点类型数量。

真正 **跑图** 需 **`POST /prompt`**，请求体为 **API 格式工作流**（在 ComfyUI 里 **Save (API Format)** 或导出 API JSON 再调用）。

常用端点（无鉴权默认安装下）：

- `GET /` — Web UI  
- `GET /object_info` — 节点与输入类型  
- `GET /queue` — 队列状态  
- `POST /prompt` — 提交执行  

---

## 5. FP8 `.safetensors` 与 GGUF 的区别（简要）

| | **FP8 safetensors**（如 `ltx-2-19b-dev-fp8`） | **GGUF**（如 `Q5_K_M`） |
|--|-----------------------------------------------|-------------------------|
| 典型用途 | 当前 **官方 Comfy 模板 / ckpt 下拉** | **ComfyUI-GGUF** 的 UNet 加载节点 |
| 放置目录 | `models/checkpoints/`（或节点约定路径） | `models/unet/` |
| 与当前模板 | **一致**（改文件名即可） | 需 **GGUF 专用工作流**，不能混在同一个 `ckpt_name` 里 |

按模板配置时，以 **checkpoints 里的 fp8 safetensors** 为准即可；GGUF 留给另一套 JSON 工作流。
