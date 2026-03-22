# LTX-2 接入视频合成流程（文本 + 分镜 → 音画片段）

## 重要：两套环境变量，别混了

| 进程 | 文件 / 方式 | 作用 |
|------|-------------|------|
| **后端**（FastAPI） | `backend/.env` 里的 `LTX2_T2V_*` | 只负责「要不要调侧车、调哪个 URL」；**不会**替你连 ComfyUI。 |
| **侧车**（`9820`） | 启动侧车时的 shell，或 **`scripts/.env.ltx2`**（复制 `.env.ltx2.example`） | **`LTX2_COMFYUI_URL` + `LTX2_COMFY_API_JSON`** 才走 **真实 LTX（Comfy 队列）**；未配置或 Comfy 失败时才会 **口播兜底**。 |

若 `/health` 里 **`comfy_ready_for_real_ltx` 为 false**，生成一定会落到口播兜底（或 stub/shell）。配好后需 **重启侧车进程** 才能读到新环境变量。

---

本仓库在 **视频合成** 步骤中，当同时满足：

- 项目已有 **视觉分镜**（`visual` 步骤产出）；
- 配置 **`LTX2_T2V_ENABLED=true`** 且 **`LTX2_T2V_ENDPOINT`** 指向可用侧车；

则 **优先** 使用 **LTX-2 文本生成音视频** 管线：**不依赖参考图**，**不调用通义万相 I2V**、**不调用 DALL·E 生图**。

每镜请求体会带上：

- **画面/镜头提示**：来自分镜字段（`visual_description`、`on_screen_text` 等）；
- **口播/独白**：来自当前项目 **脚本的 `segments[].text`**（按分镜序号循环对齐）；若无分段则退回 `full_script` 按段落切分。

生成结果在 `data/ltx2_t2v_cache/<project_id>/` 缓存为 MP4，再由现有 **MoviePy 时间轴** 拼接。

---

## 环境变量（`backend/.env`）

| 变量 | 说明 |
|------|------|
| `LTX2_T2V_ENABLED` | `true` 开启 |
| `LTX2_T2V_ENDPOINT` | 侧车根 URL，如 `http://127.0.0.1:9820`（客户端会请求 `.../generate`） |
| `LTX2_T2V_HTTP_BEARER` | 可选鉴权 |
| `LTX2_T2V_TIMEOUT_SEC` | 单镜超时，默认 `7200` |
| `LTX2_T2V_WIDTH` / `LTX2_T2V_HEIGHT` | 默认 `1920`×`1088`（32 倍数） |
| `LTX2_T2V_FPS` | 默认 `24` |
| `LTX2_T2V_SKIP_EXTERNAL_TTS` | 默认 `true`：LTX 分镜成功时 **不再** 把「音频步」整轨 TTS 叠到成片（避免与 LTX 内嵌对白重复）。若你希望强制叠 TTS，设为 `false`。 |

与 **Wan I2V** 关系：**只要 LTX 侧车就绪，有分镜就走 LTX**；`WAN_I2V_*` 在该路径下不参与分镜生成。

---

## 侧车 HTTP 契约

`POST /generate`，JSON：

```json
{
  "prompt": "画面与镜头描述…",
  "narration": "本镜口播文案…",
  "duration_sec": 6.0,
  "width": 1920,
  "height": 1088,
  "fps": 24,
  "frames": 121
}
```

`frames` 由主服务按 **8n+1** 规则根据 `duration_sec` 与 `fps` 计算。

**响应**（二选一）：

1. `Content-Type: video/mp4`，body 为 MP4 字节；或  
2. JSON：`{"path": "/绝对路径/片段.mp4"}`（服务端可读文件）。

**健康检查**：`GET /health`

---

## 侧车：`scripts/ltx2_t2v_sidecar.py`（默认可直接出片）

侧车按下面**优先级**生成 MP4，**至少会走到最后一档**，保证主流程能合成出可发布的自媒体片段：

| 优先级 | 条件 | 结果 |
|--------|------|------|
| 1 | `LTX2_COMFYUI_URL` + `LTX2_COMFY_API_JSON` | 队列 **ComfyUI**，跑你导出的 **LTX T2V API 工作流**（真实 LTX 音画） |
| 2 | `LTX2_T2V_SHELL` | 执行自定义 shell，由脚本写 `LTX2_OUT` |
| 3 | `LTX2_STUB_MP4` | 复制样例 MP4（联调用） |
| 4 | **默认** | **edge-tts + ffmpeg**：分镜文案 + 口播 → 配音 + 深色底 **1920×1088** MP4（不依赖 GPU） |

### 一键启动侧车（推荐）

```bash
cd /path/to/self-media/scripts
chmod +x start_ltx2_t2v_sidecar.sh
./start_ltx2_t2v_sidecar.sh
```

依赖：`ffmpeg` 在 PATH；Python 包由脚本尝试 `pip install`（含 `edge-tts`）。

口播音色（可选）：`export LTX2_EDGE_VOICE=zh-CN-YunxiNeural`

### 接真实 LTX（ComfyUI）

1. 本机启动 ComfyUI（默认 `http://127.0.0.1:8188`），按 **`scripts/ltx2/EXPORT_COMFY_API.md`** 导出 API 工作流 JSON。  
2. 任选其一配置侧车（变量在 **侧车进程** 内生效）：

```bash
export LTX2_COMFYUI_URL=http://127.0.0.1:8188
export LTX2_COMFY_API_JSON=/你的路径/ltx2_t2v.api.json
./start_ltx2_t2v_sidecar.sh
```

或复制 **`scripts/.env.ltx2.example` → `scripts/.env.ltx2`**，填好路径后只运行 `./start_ltx2_t2v_sidecar.sh`。

3. 自检：`curl -s http://127.0.0.1:9820/health | jq` 中 **`comfy_ready_for_real_ltx` 应为 true**。若为 false，说明 URL/JSON 路径未进侧车环境或文件不存在。  
4. Comfy 报错时：侧车设置 **`LTX2_DEBUG=1`** 再启动，看 stderr 堆栈；并核对 **`LTX2_COMFY_NODE_*`** 与导出 JSON 里的节点 id（见 `EXPORT_COMFY_API.md`）。

未配置或 Comfy 失败时，**自动降级**为口播 MP4，主 API 仍能完成「分镜 + 脚本 → 拼接成片」。

`backend/.env`：

```env
LTX2_T2V_ENABLED=true
LTX2_T2V_ENDPOINT=http://127.0.0.1:9820
```

---

## Celery 异步合成

`video_tasks.synthesize_video_task` 在存在分镜且 `ltx2_t2v_available()` 时，与 HTTP `execute` 视频步同样走 **LTX 分镜时间轴**。

---

## 前端自检

`GET /api/video/pipeline-env` 返回 `ltx2_t2v_enabled`、`ltx2_t2v_ready` 等；工作流页 **视频生成环境** 插件会展示。
