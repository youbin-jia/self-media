# 自媒体视频自动化平台

一个完整的自媒体视频自动化生成平台，支持从话题发现到视频导出的全流程自动化。

## 功能特性

### 核心功能

- 🔥 **话题监控** - 自动抓取微博、知乎等平台热门话题
- 📝 **脚本生成** - AI驱动的脚本自动生成（支持Claude/GPT/GLM）
- 🖼️ **素材收集** - 自动收集图片、视频、音频素材
- 🎬 **视频合成** - 自动合成视频，支持字幕、特效；可选接入本地 **通义万相 Wan2.1 图生视频**（见 [`docs/WAN2.1_LOCAL.md`](docs/WAN2.1_LOCAL.md)）；**LTX-2 音画一体模型**本地部署见 [`docs/LTX2_LOCAL.md`](docs/LTX2_LOCAL.md)
- 🔊 **语音合成** - 多种TTS引擎（Azure/ElevenLabs）
- 📤 **多平台导出** - 一键导出到抖音、B站、小红书等

### 系统特性

- 🔐 **用户认证** - JWT Token认证，RBAC权限控制
- 📦 **插件系统** - 可扩展的插件架构
- 🔔 **Webhook通知** - 事件驱动的通知机制
- 📱 **移动端适配** - PWA支持，移动端专用API
- ⚡ **性能优化** - Redis缓存，Celery异步任务队列

## 技术栈

| 后端 | 前端 | 服务 |
|------|------|------|
| FastAPI | Vue 3 / React | Redis |
| SQLAlchemy | Vite | Celery |
| Pydantic | TypeScript | FFmpeg |
| PyJWT | PWA | PostgreSQL |

## 快速开始

### 环境要求

- Conda (Miniconda 或 Anaconda)
- Python 3.10+
- Redis 6.0+
- FFmpeg 4.0+

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd self-media

# 创建并激活 conda 环境
conda env create -f environment.yml
conda activate self-media

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env 文件，配置必要的API密钥

# 启动服务
cd backend
uvicorn app.main:app --reload
```

### 启动Celery Worker

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info -Q high,medium,low
```

### 验证安装

```bash
# 访问API文档
open http://localhost:8000/docs

# 健康检查
curl http://localhost:8000/health
```

### 一键开发启动（推荐）

项目提供 `scripts/dev.sh` 用于一键启动本地开发依赖与服务（Redis、API、Celery Worker、Frontend）。

#### 前置要求

- 已安装并可使用 `conda`（并激活 `self-media` 环境）
- 已安装 Node.js 和 npm（用于前端）
- 已安装 Redis（脚本会尝试自动启动本机 `redis-server`）

#### 首次使用

```bash
cd self-media
chmod +x scripts/dev.sh
./scripts/dev.sh start
```

脚本会自动执行以下操作：

- 启动前自检（`ss`、`curl`、`npm` 命令可用性）
- 启动前端口检查（`8000` 后端 + `3000` 前端，可用环境变量 `FRONTEND_PORT` 修改）
  - 若发现外部旧 `uvicorn app.main:app` 占用 `8000`，会自动停止并拉起最新后端
  - 若 `FRONTEND_PORT`（默认 3000）被旧的 Vite 进程占用，会自动结束该进程，**避免静默换端口**
  - 前端使用 Vite `strictPort: true`，端口被非 Vite 进程占用时会中断启动并提示处理
- 若 `backend/.env` 不存在，则由 `backend/.env.example` 自动生成
- 自动创建 `backend/data` 目录（避免 SQLite 文件路径报错）
- 前端缺少依赖时自动执行 `npm install`（长耗时时会周期性打印已耗时，可用 `DEV_PROGRESS_INTERVAL` 调整间隔，见 `./scripts/dev.sh` 帮助）
- 启动并托管以下进程：
  - `uvicorn app.main:app --reload`
  - `celery -A app.tasks.celery_app worker --loglevel=info -Q high,medium,low`
  - `npm run dev`
- 启动后健康检查：
  - 后端 `/health` 可用性检查
  - 关键路由检查：`/api/projects/{id}/steps/script/execute`（避免旧进程导致功能 404）

#### Wan2.1 图生视频侧车（可选）

若已按 **[`docs/WAN2.1_LOCAL.md`](docs/WAN2.1_LOCAL.md)** 完成 `setup_wan2.1.sh` 与权重下载，请在**另开终端**先启动侧车，再执行 `./scripts/dev.sh start`：

```bash
./scripts/wan2.1/start_wan_sidecar.sh
```

并将 `backend/.env.wan.generated` 合并进 `backend/.env`。

#### 镜像与代理（可选）

若 **GitHub / Hugging Face** 访问不稳定，见 **[`docs/MIRROR_SOURCES.md`](docs/MIRROR_SOURCES.md)**（如 `HF_ENDPOINT`、`LTX2_GITHUB_MIRROR`、`git` 代理等）。

#### 常用命令

```bash
# 一键启动所有开发服务
./scripts/dev.sh start

# 停止后重新启动（固定端口更新部署推荐）
./scripts/dev.sh restart

# 指定前端端口（需与未被占用的端口一致）
FRONTEND_PORT=3001 ./scripts/dev.sh start

# 查看服务状态
./scripts/dev.sh status

# 查看日志目录与日志文件
./scripts/dev.sh logs

# 实时查看日志（Ctrl+C 退出）
./scripts/dev.sh tail

# 检查默认LLM是否可用（配置 + 实际调用）
./scripts/dev.sh check-llm

# 一键停止服务（仅停止由脚本启动的进程）
./scripts/dev.sh stop
```

#### 日志与运行文件

- 目录：`.devrun/`
- PID 文件：`.devrun/pids/`
- 日志文件：`.devrun/logs/`
  - `backend.log`
  - `worker.log`
  - `frontend.log`
  - `redis.log`（仅脚本拉起 Redis 时）

可直接使用以下命令查看实时日志：

```bash
tail -f .devrun/logs/backend.log
tail -f .devrun/logs/worker.log
tail -f .devrun/logs/frontend.log
```

#### 常见问题排查

- `Cannot connect to redis://localhost:6379/0`
  - Redis 未启动或端口被占用，先执行 `redis-cli -h localhost -p 6379 ping`，期待返回 `PONG`
- `vite: not found`
  - 前端依赖未安装，执行 `cd frontend && npm install`
- `sqlite3.OperationalError: unable to open database file`
  - 确保 `backend/data` 目录存在；脚本已自动处理，如手动启动请自行创建
- `Address already in use`
  - 端口冲突（常见 8000/3000/6379），先 `./scripts/dev.sh stop` 或结束占用进程；前端可设 `FRONTEND_PORT`
- 启动时提示 `关键路由缺失` 或脚本生成仍 404
  - 说明正在运行的后端不是最新代码版本（或运行目录错误）
  - 执行 `./scripts/dev.sh stop && ./scripts/dev.sh start`，并确认 `status` 正常
- 启动时提示 `端口 8000 被其他进程占用`
  - 脚本仅会自动停止可识别的旧 uvicorn 进程
  - 若是其他进程占用，请手动释放端口后重试

#### 注意事项

- `./scripts/dev.sh stop` 只会停止由该脚本记录 PID 的进程，不会影响你手动启动且未被脚本记录的其他进程
- 若你已经手动启动了某项服务，脚本会尽量复用（或提示已在运行）
- 生产环境请勿使用该脚本，生产部署请参考 [DEPLOYMENT.md](DEPLOYMENT.md)

## 文档

| 文档 | 描述 |
|------|------|
| [架构文档](ARCHITECTURE.md) | 系统架构设计说明 |
| [部署指南](DEPLOYMENT.md) | 详细部署步骤和配置 |
| [使用说明](USER_GUIDE.md) | API使用指南和示例 |

## 项目结构

```
self-media/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务服务
│   │   ├── tasks/          # Celery任务
│   │   ├── middleware/     # 中间件
│   │   └── schemas/        # Pydantic模型
│   ├── tests/              # 测试文件
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端代码
│   ├── src/
│   └── pwa/               # PWA支持
├── plugins/               # 插件目录
│   └── material_sources/  # 素材源插件
├── data/                  # 数据存储
├── environment.yml        # Conda环境配置
├── ARCHITECTURE.md        # 架构文档
├── DEPLOYMENT.md          # 部署指南
└── USER_GUIDE.md          # 使用说明
```

## API概览

### 认证

```bash
# 注册
POST /api/auth/register

# 登录
POST /api/auth/login
```

### 项目管理

```bash
# 项目CRUD
GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}
PUT    /api/projects/{id}
DELETE /api/projects/{id}

# 批量操作
POST /api/projects/batch/delete
POST /api/projects/batch/update-status
```

### 视频生成

```bash
# 生成脚本
POST /api/scripts/generate

# 收集素材
POST /api/materials/collect

# 生成视频
POST /api/video/generate

# 导出视频
POST /api/video/export
```

### 其他功能

```bash
# 插件管理
GET  /api/plugins
POST /api/plugins/{id}/enable

# Webhook管理
GET  /api/webhooks
POST /api/webhooks

# 推荐系统
GET /api/recommendations/topics

# 移动端API
GET /api/mobile/projects
GET /api/mobile/dashboard
```

## 配置

### 必需配置

| 变量 | 描述 |
|------|------|
| `JWT_SECRET_KEY` | JWT签名密钥（生产环境必须修改） |
| `SECRET_KEY` | 应用密钥 |

### LLM配置

| 变量 | 描述 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API密钥 |
| `OPENAI_API_KEY` | OpenAI API密钥 |
| `KIMI_API_KEY` | Kimi API密钥（Moonshot） |
| `KIMI_BASE_URL` | Kimi 接口地址（默认 `https://api.moonshot.cn/v1`） |
| `KIMI_MODEL` | Kimi 模型名（默认 `moonshot-v1-8k`） |
| `DEFAULT_LLM_PROVIDER` | 默认LLM（claude/openai/kimi） |

### TTS配置

| 变量 | 描述 |
|------|------|
| `AZURE_SPEECH_KEY` | Azure语音服务密钥 |
| `AZURE_SPEECH_REGION` | Azure服务区域 |
| `ELEVENLABS_API_KEY` | ElevenLabs API密钥 |

## 开发

### 运行测试

```bash
cd backend
pytest tests/ -v
```

### 代码规范

```bash
# 格式化
black app/

# 类型检查
mypy app/

# 代码检查
ruff check app/
```

## 部署

详见 [部署指南](DEPLOYMENT.md)

### Docker部署

```bash
docker-compose up -d
```

### 生产部署

```bash
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。