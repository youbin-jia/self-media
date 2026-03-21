# 自媒体视频自动化平台

一个完整的自媒体视频自动化生成平台，支持从话题发现到视频导出的全流程自动化。

## 功能特性

### 核心功能

- 🔥 **话题监控** - 自动抓取微博、知乎等平台热门话题
- 📝 **脚本生成** - AI驱动的脚本自动生成（支持Claude/GPT/GLM）
- 🖼️ **素材收集** - 自动收集图片、视频、音频素材
- 🎬 **视频合成** - 自动合成视频，支持字幕、特效
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
| `DEFAULT_LLM_PROVIDER` | 默认LLM（claude/openai） |

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