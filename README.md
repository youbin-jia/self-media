# 自媒体视频自动化平台

**一条流水线，从灵感到成片。** 面向创作者与小型团队的 **AI 视频生产中枢**：脚本、分镜、配音、合成与发布准备可在统一工作台完成，显著压缩从选题到可发成片的时间成本。

> 后端 **FastAPI** + 前端 **React（Vite）**，支持本地/私有化部署，数据与模型密钥掌握在你自己手中。

## 功能特性

### 产品亮点（营销向）

- **爆款效率** — 用多模型 LLM 快速产出口播稿、分镜与画面描述，少改直出、多改精进，适配日更与矩阵号节奏。
- **音画一体** — 可选接入 **LTX-2** 等文本生成音视频能力，单镜即可带对白与环境声；亦可接 **Wan2.1 图生视频**、传统时间轴 + TTS，按项目策略自由组合。
- **多平台心智** — 工作流围绕「可发布的短视频」设计，成片格式与元数据可面向 **抖音、B 站、小红书、视频号** 等主流内容平台做适配与导出（具体能力与配置以当前版本及 `backend/.env` 为准）。
- **团队协作与安全** — JWT + 角色权限，项目隔离；Redis 与异步队列支撑高峰合成，适合从小作坊平滑扩到小团队。
- **可扩展商业叙事** — 素材源 **插件化**，Webhook 与 API 便于对接自有 CMS、审批流或计费系统，方便 OEM 与二次商业化。

### 核心能力

- **智能脚本** — 多厂商 LLM（Claude / OpenAI / GLM / Kimi 等）生成与迭代脚本，支持按项目配置切换，见 `backend/.env`。
- **素材与分镜** — 自动/半自动收集参考素材，视觉步骤结构化输出分镜，为合成与审片打下基础。
- **视频合成** — 时间轴拼接、字幕与包装；可选 **LTX-2 文本音画分镜**（[`docs/LTX2_PIPELINE.md`](docs/LTX2_PIPELINE.md)）、**通义万相 Wan2.1 图生视频**（[`docs/WAN2.1_LOCAL.md`](docs/WAN2.1_LOCAL.md)）；本地 **ComfyUI + GGUF** 部署见 [`docs/LTX2_LOCAL.md`](docs/LTX2_LOCAL.md)。
- **专业配音** — 对接 **Azure Speech、ElevenLabs** 等 TTS，成片听感更接近商业短视频标准。
- **发布与运营辅助** — 导出与任务流可对接多平台发布准备（随版本迭代扩展）；配合话题/热点能力（可按插件与配置启用）放大流量入口。

### 工程能力

- **高性能底座** — Redis 缓存、Celery **多优先级队列**（high / medium / low），大任务不拖死交互。
- **插件式素材生态** — `plugins/material_sources/` 扩展图片来源与抓取策略，避免被单一供应商绑定。
- **全端触达** — 提供 `frontend/pwa/` 等 **PWA** 资源，移动端看进度、过审片更方便。
- **可观测与集成** — Webhook 通知、开放 API，便于接入监控、飞书/钉钉机器人与内部工具链。

## 技术栈

| 后端 | 前端 | 运行依赖 |
|------|------|----------|
| FastAPI、SQLAlchemy、Pydantic | React 18、Vite、Ant Design | Redis、FFmpeg |
| Celery、PyJWT | TypeScript | Conda `self-media`（Python 3.11） |

## 快速开始

### 环境要求

- **Conda**（Miniconda / Miniforge 等），环境名 **`self-media`**
- **Python 3.11**（见根目录 `environment.yml`）
- **Node.js + npm**（前端）
- **Redis**（开发脚本可尝试本机拉起 `redis-server`）
- **FFmpeg**（视频处理；Conda 环境内通常已带）

### 安装

```bash
git clone <repository-url>
cd self-media

conda env create -f environment.yml
conda activate self-media

cp backend/.env.example backend/.env
# 编辑 backend/.env：JWT、LLM、TTS 等密钥与开关
```

### 推荐：一键开发启动（`scripts/dev.sh`）

在仓库根目录执行（会自动创建 `backend/data`、按需 `npm install`、记录 PID 与日志）：

```bash
chmod +x scripts/dev.sh

# 启动：Redis（若需）+ 后端 8000 + Celery Worker + 前端 3000
./scripts/dev.sh start

# 同上，并一并启动 LTX 文本视频侧车（9820，用于调试 LTX 管线）
START_LTX2_SIDECAR=1 ./scripts/dev.sh start

# 改端口后重启（固定端口开发推荐）
FRONTEND_PORT=3000 START_LTX2_SIDECAR=1 ./scripts/dev.sh restart
```

**`dev.sh` 会做什么（摘要）**

- 自检：`ss`、`curl`、`npm`；清理占用 **8000** 的旧 `uvicorn app.main:app`；清理占用 **`FRONTEND_PORT`**（默认 3000）的旧 Vite。
- 后端 **优先使用 Conda 环境 `self-media` 内的 `uvicorn`**（常见路径如 `~/miniconda3/envs/self-media/bin/uvicorn`），避免 PATH 指到错误 Python 导致缺依赖（如 `sqlalchemy`）。
- `START_LTX2_SIDECAR=1` 时：启动前会尝试释放 **9820** 上遗留的 LTX 侧车进程；启动 [`scripts/start_ltx2_t2v_sidecar.sh`](scripts/start_ltx2_t2v_sidecar.sh)（若存在 [`scripts/.env.ltx2`](scripts/.env.ltx2.example) 会自动 `source`）。
- 启动后探测 `http://127.0.0.1:8000/health` 与关键路由，避免跑错目录的旧进程。

**常用命令**

| 命令 | 说明 |
|------|------|
| `./scripts/dev.sh start` | 启动（已在跑则跳过对应项） |
| `./scripts/dev.sh restart` | 先 `stop` 再 `start` |
| `./scripts/dev.sh stop` | 停止由脚本记录的进程（含 LTX 侧车） |
| `./scripts/dev.sh status` | 查看 Redis / 后端 / Worker / 前端 / LTX 侧车是否在跑 |
| `./scripts/dev.sh logs` | 打印日志目录与文件名 |
| `./scripts/dev.sh tail` | 多路日志 `tail -f`（Ctrl+C 退出） |
| `./scripts/dev.sh check-llm` | 检查默认 LLM 配置并试调用 |

**环境变量（可选）**

- `FRONTEND_PORT` — 前端端口（与 `frontend/vite.config.js` 一致，默认 3000）
- `DEV_PROGRESS_INTERVAL` — `npm install` 等长步骤心跳间隔（秒）
- `START_LTX2_SIDECAR=1` — 与 `dev.sh` 一同管理 LTX 侧车（9820）

**运行产物**

- 目录：`.devrun/`
- PID：`.devrun/pids/`（`backend.pid`、`worker.pid`、`frontend.pid`、`ltx2_sidecar.pid`、`redis.pid`）
- 日志：`.devrun/logs/` — `backend.log`、`worker.log`、`frontend.log`、`ltx2_sidecar.log`（启用侧车时）、`redis.log`

启动成功后：

- 前端：<http://127.0.0.1:3000/>（或你设的 `FRONTEND_PORT`）
- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：`curl -s http://127.0.0.1:8000/health`

### LTX-2：配置与调试（视频步走真实 Comfy / 口播兜底）

**两套变量不要混用：**

| 进程 | 配置位置 | 作用 |
|------|----------|------|
| **后端** | `backend/.env` 中 `LTX2_T2V_*` | 是否调用侧车、侧车 URL、超时与分辨率等 |
| **侧车**（9820） | `scripts/.env.ltx2`（复制 `.env.ltx2.example`）或启动前 `export` | `LTX2_COMFYUI_URL` + `LTX2_COMFY_API_JSON` 才走 **Comfy 真 LTX**；否则降级口播兜底 |

**推荐流程**

1. 按 [`docs/LTX2_LOCAL.md`](docs/LTX2_LOCAL.md) 安装并启动 **ComfyUI**（默认 **8188**）；在 UI 里先 Queue 跑通 LTX 工作流。
2. 按 [`scripts/ltx2/EXPORT_COMFY_API.md`](scripts/ltx2/EXPORT_COMFY_API.md) 导出 **API Format** JSON，把路径写入 `scripts/.env.ltx2`。
3. `backend/.env`：`LTX2_T2V_ENABLED=true`，`LTX2_T2V_ENDPOINT=http://127.0.0.1:9820`。
4. `START_LTX2_SIDECAR=1 ./scripts/dev.sh restart`（或单独运行 `./scripts/start_ltx2_t2v_sidecar.sh`）。

**自检**

```bash
curl -s http://127.0.0.1:9820/health | python3 -m json.tool   # comfy_ready_for_real_ltx 应为 true 才走 Comfy
curl -s http://127.0.0.1:8000/api/video/pipeline-env | python3 -m json.tool
```

**侧车排错**：侧车环境加 `LTX2_DEBUG=1` 再启动，看终端 / `ltx2_sidecar.log`；节点 id 与导出 JSON 不一致时设置 `LTX2_COMFY_NODE_*`（见 `EXPORT_COMFY_API.md`）。

完整契约与降级行为见 **[docs/LTX2_PIPELINE.md](docs/LTX2_PIPELINE.md)**。

### Wan2.1 图生视频侧车（可选）

见 **[docs/WAN2.1_LOCAL.md](docs/WAN2.1_LOCAL.md)**。侧车需**单独终端**先起，再将生成的 `backend/.env.wan.generated` 合并进 `backend/.env`。

### 镜像与网络（GitHub / Hugging Face）

见 **[docs/MIRROR_SOURCES.md](docs/MIRROR_SOURCES.md)**（`HF_ENDPOINT`、`LTX2_GITHUB_MIRROR`、`git` 代理等）。

### 手动分步启动（不用 `dev.sh` 时）

```bash
conda activate self-media
# 使用当前环境下的 uvicorn，勿混用 base 或其它环境的 python
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 另开终端
cd backend && celery -A app.tasks.celery_app worker --loglevel=info -Q high,medium,low
# 另开终端
cd frontend && npm install && npm run dev
```

### 常见问题

| 现象 | 处理 |
|------|------|
| `Cannot connect to redis://localhost:6379` | `redis-cli -h localhost -p 6379 ping` 应返回 `PONG` |
| `ModuleNotFoundError: No module named 'sqlalchemy'` | 确认已 `conda activate self-media`，且用该环境内的 `uvicorn`，或直接用 `./scripts/dev.sh start` |
| `vite: not found` | `cd frontend && npm install` |
| `Address already in use`（8000 / 3000 / 9820） | `./scripts/dev.sh stop` 后重试；或改 `FRONTEND_PORT`；9820 可检查是否有旧 `ltx2_t2v_sidecar` |
| 关键路由检查失败 / 接口 404 | `./scripts/dev.sh stop && ./scripts/dev.sh restart`，确认在仓库根目录执行且代码为当前版本 |
| LTX 一直是口播兜底 | 侧车未配 Comfy 或 Comfy 失败；看 `9820/health` 与 `pipeline-env`，并设 `LTX2_DEBUG=1` |

生产环境请勿依赖 `dev.sh`；部署见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构 |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 部署与配置 |
| [USER_GUIDE.md](USER_GUIDE.md) | 使用与 API 示例 |
| [docs/LTX2_PIPELINE.md](docs/LTX2_PIPELINE.md) | LTX-2 侧车与视频步契约 |
| [docs/LTX2_LOCAL.md](docs/LTX2_LOCAL.md) | 本地 Comfy + GGUF |
| [docs/WAN2.1_LOCAL.md](docs/WAN2.1_LOCAL.md) | Wan2.1 侧车 |
| [docs/MIRROR_SOURCES.md](docs/MIRROR_SOURCES.md) | 镜像与代理 |
| [scripts/ltx2/README.md](scripts/ltx2/README.md) | LTX2 脚本索引 |

## 项目结构（节选）

```
self-media/
├── backend/app/          # FastAPI：api、models、services、tasks、middleware
├── frontend/src/         # React + Vite
├── frontend/pwa/         # PWA 静态资源
├── scripts/              # dev.sh、LTX/Wan 侧车与 Comfy 安装脚本
├── plugins/material_sources/
├── docs/                 # LTX、Wan、镜像等专题文档
├── environment.yml       # Conda 环境（Python 3.11）
├── .devrun/              # dev.sh 的 PID 与日志（本地生成，勿提交）
└── third_party/          # 本地 Comfy/权重等（通常 .gitignore）
```

## API 概览（节选）

认证：`POST /api/auth/register`、`POST /api/auth/login`  
项目：`/api/projects` CRUD 与批量操作  
脚本：`POST /api/scripts/generate`  
视频：`POST /api/video/*`，环境自检 `GET /api/video/pipeline-env`  

更多路径以运行中的 **Swagger**（`/docs`）为准。

## 配置（节选）

**安全**：`JWT_SECRET_KEY`、`SECRET_KEY`（生产必改）  
**LLM**：`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`KIMI_*`、`DEFAULT_LLM_PROVIDER` 等（见 `backend/.env.example`）  
**TTS**：`AZURE_SPEECH_*`、`ELEVENLABS_API_KEY` 等  
**LTX 视频步**：`LTX2_T2V_*`（后端）；Comfy 相关变量在**侧车**环境或 `scripts/.env.ltx2`

## 开发

```bash
conda activate self-media
cd backend
pytest tests/ -v

# 代码质量（与 CLAUDE.md 一致）
black app/
mypy app/
ruff check app/
```

## 部署

详见 [DEPLOYMENT.md](DEPLOYMENT.md)。本地可试用：

```bash
docker compose up -d
```

生产常用 Gunicorn + Uvicorn Worker（示例见 DEPLOYMENT.md）。

## 许可证

MIT License

## 贡献

欢迎 Issue 与 Pull Request。
