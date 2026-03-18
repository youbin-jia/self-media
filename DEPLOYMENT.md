# 自媒体视频自动化平台 - 部署指南

## 目录

- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [生产部署](#生产部署)
- [Docker部署](#docker部署)
- [配置说明](#配置说明)
- [常见问题](#常见问题)

## 环境要求

### 基础环境

| 组件 | 版本要求 | 用途 |
|------|---------|------|
| Python | 3.10+ | 后端运行环境 |
| Redis | 6.0+ | 缓存 + 消息队列 |
| FFmpeg | 4.0+ | 视频处理 |
| Node.js | 18+ | 前端构建（可选） |

### 外部服务（按需配置）

| 服务 | 用途 | 获取方式 |
|------|------|---------|
| Anthropic API | Claude LLM | https://console.anthropic.com |
| OpenAI API | GPT + DALL-E | https://platform.openai.com |
| Azure Speech | TTS语音合成 | https://azure.microsoft.com |
| ElevenLabs | TTS语音合成 | https://elevenlabs.io |
| Pexels API | 免费图片/视频 | https://www.pexels.com/api |

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd self-media
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate   # Windows
```

### 3. 安装依赖

```bash
pip install -r backend/requirements.txt
```

### 4. 安装系统依赖

**macOS:**
```bash
brew install ffmpeg redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg redis-server
sudo systemctl start redis
```

**Windows:**
```bash
# 使用 Chocolatey
choco install ffmpeg redis
# 或手动下载安装
```

### 5. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `.env` 文件：

```env
# 环境
ENVIRONMENT=development

# 数据库
DATABASE_URL=sqlite:///./data/video_automation.db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT密钥（生产环境必须修改）
JWT_SECRET_KEY=your-super-secret-jwt-key-change-me
SECRET_KEY=your-app-secret-key-change-me

# API Keys（按需配置）
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
AZURE_SPEECH_KEY=xxx
AZURE_SPEECH_REGION=eastasia

# LLM配置
DEFAULT_LLM_PROVIDER=claude
LLM_FALLBACK_ENABLED=true

# TTS配置
DEFAULT_TTS_PROVIDER=azure
```

### 6. 初始化数据库

```bash
cd backend
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

### 7. 启动服务

**启动后端API服务：**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**启动Celery Worker（新终端）：**
```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info -Q high,medium,low
```

**启动Celery Beat（定时任务，可选）：**
```bash
cd backend
celery -A app.tasks.celery_app beat --loglevel=info
```

### 8. 验证安装

```bash
# 检查API健康状态
curl http://localhost:8000/health

# 查看API文档
open http://localhost:8000/docs
```

## 生产部署

### 1. 使用 PostgreSQL

```env
DATABASE_URL=postgresql://user:password@localhost:5432/video_automation
```

安装 psycopg2：
```bash
pip install psycopg2-binary
```

### 2. 使用 Gunicorn + Uvicorn

```bash
pip install gunicorn

gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 5
```

### 3. 使用 Supervisor 管理进程

创建 `/etc/supervisor/conf.d/self-media.conf`：

```ini
[program:self-media-api]
command=/path/to/venv/bin/gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
directory=/path/to/self-media/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/self-media/api.err.log
stdout_logfile=/var/log/self-media/api.out.log

[program:self-media-celery]
command=/path/to/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info -Q high,medium,low
directory=/path/to/self-media/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/self-media/celery.err.log
stdout_logfile=/var/log/self-media/celery.out.log

[program:self-media-celery-beat]
command=/path/to/venv/bin/celery -A app.tasks.celery_app beat --loglevel=info
directory=/path/to/self-media/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/self-media/beat.err.log
stdout_logfile=/var/log/self-media/beat.out.log
```

启动服务：
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

### 4. Nginx 反向代理

创建 `/etc/nginx/sites-available/self-media`：

```nginx
upstream self_media_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # HTTPS重定向
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # API代理
    location /api/ {
        proxy_pass http://self_media_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_timeout 300s;
        proxy_read_timeout 300s;
    }

    # WebSocket支持（如需要）
    location /ws/ {
        proxy_pass http://self_media_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件
    location / {
        root /path/to/self-media/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 文件上传大小限制
    client_max_body_size 100M;
}
```

### 5. Redis 安全配置

编辑 `/etc/redis/redis.conf`：

```conf
# 绑定本地地址
bind 127.0.0.1

# 设置密码
requirepass your-redis-password

# 禁用危险命令
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
```

更新环境变量：
```env
REDIS_URL=redis://:your-redis-password@localhost:6379/0
```

## Docker部署

### Dockerfile

创建 `Dockerfile`：

```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 安装Python依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend/ ./backend/
COPY plugins/ ./plugins/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/video_automation
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
    depends_on:
      - db
      - redis

  worker:
    build: .
    command: celery -A backend.app.tasks.celery_app worker --loglevel=info -Q high,medium,low
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/video_automation
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
    depends_on:
      - db
      - redis

  beat:
    build: .
    command: celery -A backend.app.tasks.celery_app beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=video_automation
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  redis_data:
```

### 启动Docker服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 停止服务
docker-compose down
```

## 配置说明

### 环境变量完整列表

| 变量名 | 必填 | 默认值 | 描述 |
|--------|------|--------|------|
| `ENVIRONMENT` | 否 | development | 运行环境 (development/production) |
| `DATABASE_URL` | 否 | sqlite:///./data/video_automation.db | 数据库连接URL |
| `REDIS_URL` | 否 | redis://localhost:6379/0 | Redis连接URL |
| `JWT_SECRET_KEY` | **是** | - | JWT签名密钥 |
| `SECRET_KEY` | **是** | - | 应用密钥 |
| `JWT_ACCESS_TOKEN_EXPIRE_HOURS` | 否 | 168 | Token有效期(小时) |
| `ANTHROPIC_API_KEY` | 否 | - | Anthropic API密钥 |
| `OPENAI_API_KEY` | 否 | - | OpenAI API密钥 |
| `AZURE_SPEECH_KEY` | 否 | - | Azure语音服务密钥 |
| `AZURE_SPEECH_REGION` | 否 | - | Azure服务区域 |
| `ELEVENLABS_API_KEY` | 否 | - | ElevenLabs API密钥 |
| `PEXELS_API_KEY` | 否 | - | Pexels API密钥 |
| `DEFAULT_LLM_PROVIDER` | 否 | claude | 默认LLM提供商 |
| `DEFAULT_TTS_PROVIDER` | 否 | azure | 默认TTS提供商 |
| `DATA_DIR` | 否 | ./data | 数据存储目录 |

### 日志配置

```python
# 添加到 app/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

## 常见问题

### Q: FFmpeg找不到

```bash
# 检查FFmpeg是否安装
ffmpeg -version

# 添加到PATH（如果需要）
export PATH=$PATH:/usr/local/bin/ffmpeg
```

### Q: Redis连接失败

```bash
# 检查Redis状态
redis-cli ping

# 检查Redis配置
redis-cli config get bind
```

### Q: Celery任务不执行

```bash
# 检查Worker状态
celery -A app.tasks.celery_app inspect active

# 检查队列状态
celery -A app.tasks.celery_app inspect reserved
```

### Q: 数据库迁移

```bash
# 使用Alembic进行迁移
alembic revision --autogenerate -m "migration message"
alembic upgrade head
```

### Q: 内存不足

调整Celery Worker并发数：
```bash
celery -A app.tasks.celery_app worker --concurrency=2
```

或在配置中设置：
```env
CELERY_WORKER_CONCURRENCY=2
```