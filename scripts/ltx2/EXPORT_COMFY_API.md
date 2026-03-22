# 导出 LTX Text-to-Video 的 ComfyUI API 工作流

要让侧车走 **真实 LTX 推理**（而非口播兜底），需要把官方示例工作流保存为 **API 格式**，并设置环境变量：

```bash
export LTX2_COMFYUI_URL=http://127.0.0.1:8188
export LTX2_COMFY_API_JSON=/绝对路径/ltx2_t2v.api.json
```

## 步骤

1. 按 `docs/LTX2_LOCAL.md` 安装 ComfyUI + ComfyUI-LTXVideo，并下载官方 **safetensors** 模型（与示例工作流一致，如 `ltx-2-19b-distilled.safetensors`）。
2. 在 ComfyUI 中 **Load** 示例（任选其一）：  
   - 本仓库：`scripts/ltx2/bundled_workflows/LTX-2_T2V_Distilled_wLora.ui.json`（与官方 `example_workflows/2.0/LTX-2_T2V_Distilled_wLora.json` 同源）  
   - 或插件目录：`ComfyUI/custom_nodes/ComfyUI-LTXVideo/example_workflows/2.0/LTX-2_T2V_Distilled_wLora.json`  
   也可运行 `./scripts/ltx2/fetch_official_t2v_ui_workflow.sh` 从 GitHub 更新捆绑文件。
3. 在 ComfyUI 菜单使用 **Save (API Format)** 或 **Export (API)**（名称因版本而异），保存为 `ltx2_t2v.api.json`。
4. 侧车默认按 **Lightricks 2.0 T2V Distilled** 扁平示例的节点 id 打补丁（可在环境变量中覆盖）：

| 环境变量 | 默认 | 含义 |
|----------|------|------|
| `LTX2_COMFY_NODE_PROMPT` | `5222` | 主提示词节点（多为 `PrimitiveStringMultiline`；**子图导出**常为 `CLIPTextEncode`，如 `92:3`） |
| `LTX2_COMFY_NODE_FRAMES` | `5218` | `PrimitiveInt` 总帧数（子图示例常为 **Length** 节点，如 `92:62`） |
| `LTX2_COMFY_NODE_FPS` | `5221` | `PrimitiveFloat` 帧率（子图示例如 `92:102`；若只有 `PrimitiveInt` 帧率可试 `92:103`） |
| `LTX2_COMFY_NODE_EMPTY_IMAGE` | `5217` | `EmptyImage` 宽/高（子图示例如 `92:89`） |

若你导出的 API JSON 节点 id 不同（尤其 **Export (API)** 后出现 **`92:数字`** 这类带冒号的 id），请在 **`scripts/.env.ltx2`** 里设置上述四个变量，并 **重启侧车**。可在 JSON 内搜索 `CLIPTextEncode`、`Length`、`Frame Rate`、`EmptyImage` 对照 `_meta.title` 确认。

5. **先单独在 ComfyUI 点一次 Queue** 确认能出视频，再启动侧车。
