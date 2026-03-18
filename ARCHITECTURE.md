# 自媒体视频自动化平台 - 架构文档

## 系统概述

本平台是一个完整的自媒体视频自动化生成系统，支持从话题发现到视频导出的全流程自动化。

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 后端框架 | FastAPI | REST API 服务 |
| 数据库 | SQLite / PostgreSQL | 数据持久化 |
| 缓存 | Redis | 缓存 + Celery消息队列 |
| 任务队列 | Celery | 异步任务处理 |
| LLM | Claude / OpenAI / GLM | 脚本生成 |
| TTS | Azure / ElevenLabs | 语音合成 |
| 视频处理 | MoviePy | 视频剪辑合成 |

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           客户端层 (Client Layer)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │  Web App    │  │  Mobile PWA │  │  API Client │                      │
│  │  (Vue/React)│  │             │  │  (CLI/SDK)  │                      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                      │
└─────────┼────────────────┼────────────────┼─────────────────────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          API 网关层 (API Gateway)                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │   │
│  │  │  Auth    │ │ Projects │ │ Webhooks │ │ Mobile   │            │   │
│  │  │  Router  │ │  Router  │ │  Router  │ │  Router  │            │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                           │                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Middleware Layer                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                         │   │
│  │  │   JWT    │ │   RBAC   │ │   CORS   │                         │   │
│  │  │   Auth   │ │  Check   │ │          │                         │   │
│  │  └──────────┘ └──────────┘ └──────────┘                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          服务层 (Service Layer)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Script     │  │  Material   │  │   Video     │  │     LLM     │    │
│  │  Generator  │  │  Collector  │  │ Synthesizer │  │  Provider   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    TTS      │  │   Cache     │  │  Webhook    │  │Recommendation│   │
│  │  Provider   │  │  Service    │  │  Handler    │  │   Engine    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         任务队列层 (Task Queue)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                       Celery Workers                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │   │
│  │  │ High Priority│  │ Med Priority │  │ Low Priority │           │   │
│  │  │   Queue      │  │    Queue     │  │    Queue     │           │   │
│  │  │ (Video Tasks)│  │(Batch Tasks) │  │ (Cleanup)    │           │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                    ┌─────────┴─────────┐                               │
│                    │       Redis       │                               │
│                    │  (Broker + Cache) │                               │
│                    └───────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          数据层 (Data Layer)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │  Database   │  │ File Storage│  │   Plugins   │                      │
│  │  (SQLite/   │  │   (Local/   │  │   System    │                      │
│  │  PostgreSQL)│  │    S3)      │  │             │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. 用户管理模块 (User Management)

```
backend/app/
├── models/user.py          # User模型
├── schemas/user.py         # 用户数据模式
├── middleware/auth.py      # JWT认证 + RBAC
├── services/auth/
│   └── jwt_handler.py      # JWT令牌处理
└── api/
    ├── auth.py             # 登录/注册API
    └── users.py            # 用户管理API
```

**功能特性：**
- JWT Token认证（7天有效期）
- 角色权限控制（admin/editor/viewer）
- 项目级数据隔离（owner_id + team_members）

### 2. 视频生成流水线

```
Pipeline: 话题发现 → 脚本生成 → 素材收集 → 视频合成 → 质量检测 → 导出

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Topic   │───▶│  Script  │───▶│ Material │───▶│  Video   │
│ Monitor  │    │Generator │    │Collector │    │Synthesize│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │              │               │               │
     ▼              ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  热榜API  │    │    LLM   │    │ 图片/视频 │    │ MoviePy  │
│ (微博等)  │    │Provider  │    │   API    │    │  FFMPEG  │ 
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 3. 插件系统

```
plugins/
├── __init__.py
└── material_sources/
    ├── __init__.py
    ├── base.py              # MaterialSourcePlugin基类
    └── example_source.py    # 示例插件

backend/app/services/plugins/
├── __init__.py
├── discovery.py             # 自动发现
└── loader.py                # 动态加载
```

**插件开发：**

```python
from plugins.material_sources.base import MaterialSourcePlugin

class MyMaterialSource(MaterialSourcePlugin):
    name = "my_source"
    version = "1.0.0"
    description = "My custom material source"
    supported_types = ["image", "video"]

    async def collect(self, keyword: str, count: int = 10, **kwargs):
        # 实现素材收集逻辑
        return [{"url": "...", "type": "image", ...}]
```

### 4. Webhook通知系统

```
事件类型:
├── project.created
├── project.completed
├── project.failed
├── video.generated
└── export.finished

投递流程:
Event → WebhookHandler → HTTP POST → Retry (exp. backoff)
                                    └── HMAC-SHA256签名验证
```

### 5. 缓存系统

```python
# 缓存装饰器使用
from app.services.cache.redis_cache import cache_result, invalidate_cache

@cache_result("project:{project_id}", ttl=1800)
async def get_project(project_id: str):
    ...

@invalidate_cache("project:{project_id}")
async def update_project(project_id: str, data: dict):
    ...
```

### 6. 任务队列

```
优先级队列:
┌────────────────┬────────────────┬────────────────┐
│   high queue   │  medium queue  │   low queue    │
│   (实时任务)     │  (批处理任务)   │  (清理任务)     │
│   视频生成       │  批量导出       │  缓存清理       │
│   即时处理       │  数据分析       │  日志归档       │
└────────────────┴────────────────┴────────────────┘
```

## 数据模型

### ER图

```
┌─────────────┐       ┌─────────────┐
│    User     │       │   Project   │
├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ owner_id(FK)│
│ username    │       │ id (PK)     │
│ email       │       │ title       │
│ hashed_pwd  │       │ status      │
│ role        │       │ team_members│
└─────────────┘       └──────┬──────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌─────────────┐┌─────────────┐┌─────────────┐
       │   Script    ││  Material   ││    Task     │
       ├─────────────┤├─────────────┤├─────────────┤
       │ project_id  ││ project_id  ││ project_id  │
       │ segments    ││ type        ││ type        │
       │ style       ││ file_path   ││ status      │
       └─────────────┘└─────────────┘└─────────────┘

┌─────────────┐       ┌─────────────┐
│   Plugin    │       │   Webhook   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ name        │       │ name        │
│ type        │       │ url         │
│ version     │       │ events      │
│ enabled     │       │ secret      │
│ metadata    │       │ enabled     │
└──────┬──────┘       └──────┬──────┘
       │                     │
       ▼                     ▼
┌─────────────┐       ┌─────────────┐
│PluginConfig │       │WebhookDeliver│
├─────────────┤       ├─────────────┤
│ plugin_id   │       │ webhook_id  │
│ key         │       │ event_type  │
│ value       │       │ payload     │
└─────────────┘       │ status      │
                      └─────────────┘
```

## API端点

| 模块 | 端点 | 方法 | 描述 |
|------|------|------|------|
| **认证** | `/api/auth/register` | POST | 用户注册 |
| | `/api/auth/login` | POST | 用户登录 |
| | `/api/auth/refresh` | POST | 刷新令牌 |
| **项目** | `/api/projects` | GET/POST | 项目列表/创建 |
| | `/api/projects/{id}` | GET/PUT/DELETE | 项目详情 |
| | `/api/projects/batch/delete` | POST | 批量删除 |
| | `/api/projects/batch/update-status` | POST | 批量更新状态 |
| **脚本** | `/api/scripts` | GET/POST | 脚本管理 |
| | `/api/scripts/generate` | POST | AI生成脚本 |
| **素材** | `/api/materials` | GET/POST | 素材管理 |
| | `/api/materials/collect` | POST | 收集素材 |
| **视频** | `/api/video/generate` | POST | 生成视频 |
| | `/api/video/export` | POST | 导出视频 |
| **插件** | `/api/plugins` | GET | 插件列表 |
| | `/api/plugins/{id}/enable` | POST | 启用插件 |
| | `/api/plugins/{id}/config` | PUT | 更新配置 |
| **Webhook** | `/api/webhooks` | GET/POST | Webhook管理 |
| | `/api/webhooks/{id}/deliveries` | GET | 投递记录 |
| **推荐** | `/api/recommendations/topics` | GET | 话题推荐 |
| | `/api/recommendations/similar/{id}` | GET | 相似项目 |
| **移动端** | `/api/mobile/projects` | GET | 项目列表(分页) |
| | `/api/mobile/dashboard` | GET | 仪表盘摘要 |
| | `/api/mobile/projects/{id}/quick-start` | POST | 快速启动 |

## 安全设计

### 认证流程

```
1. 用户登录 → 验证凭证
2. 生成 JWT Token (HS256, 7天有效)
3. 后续请求携带 Authorization: Bearer <token>
4. 中间件验证 Token → 解析用户信息 → RBAC权限检查
```

### RBAC权限模型

| 角色 | 权限 |
|------|------|
| admin | 所有操作，用户管理 |
| editor | 创建/编辑项目，素材管理，视频生成 |
| viewer | 只读访问 |

### 数据隔离

```sql
-- 项目查询自动过滤
SELECT * FROM projects
WHERE owner_id = current_user_id
   OR current_user_id IN (team_members);
```

## 性能优化

### 缓存策略

| 数据类型 | TTL | 缓存键模式 |
|----------|-----|------------|
| 用户信息 | 1小时 | `user:{user_id}` |
| 项目详情 | 30分钟 | `project:{project_id}` |
| 项目列表 | 10分钟 | `projects:user:{user_id}:page:{page}` |
| 热门话题 | 5分钟 | `hot_topics:{source}` |
| 仪表盘 | 15分钟 | `dashboard:{user_id}` |

### 数据库索引

```sql
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created ON projects(created_at);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

## 扩展性设计

### 水平扩展

```
                    ┌─────────────┐
                    │Load Balancer│
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  FastAPI 1  │ │  FastAPI 2  │ │  FastAPI 3  │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
    ┌─────────────────────────────────────────────┐
    │              Shared Services                │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
    │  │PostgreSQL│  │  Redis  │  │ Celery  │     │
    │  └─────────┘  └─────────┘  └─────────┘     │
    └─────────────────────────────────────────────┘
```

### 插件扩展

系统支持通过插件扩展：
- 素材源（图片、视频、音频）
- LLM提供商
- TTS服务
- 视频特效
- 导出格式