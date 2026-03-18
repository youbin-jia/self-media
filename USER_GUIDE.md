# 自媒体视频自动化平台 - 使用说明

## 目录

- [快速入门](#快速入门)
- [用户管理](#用户管理)
- [项目管理](#项目管理)
- [脚本生成](#脚本生成)
- [素材收集](#素材收集)
- [视频生成](#视频生成)
- [批量操作](#批量操作)
- [插件系统](#插件系统)
- [Webhook通知](#webhook通知)
- [移动端使用](#移动端使用)
- [API参考](#api参考)

## 快速入门

### 1. 注册账号

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myusername",
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

响应：
```json
{
  "id": "uuid-string",
  "username": "myusername",
  "email": "user@example.com",
  "role": "viewer"
}
```

### 2. 登录获取Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myusername",
    "password": "SecurePassword123!"
  }'
```

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

### 3. 使用Token访问API

```bash
export TOKEN="your-access-token"

curl http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN"
```

## 用户管理

### 用户角色

| 角色 | 权限 |
|------|------|
| `admin` | 用户管理、所有项目操作、系统配置 |
| `editor` | 创建项目、编辑内容、生成视频 |
| `viewer` | 查看项目、只读访问 |

### 修改用户角色（管理员）

```bash
curl -X PUT http://localhost:8000/api/users/{user_id}/role \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "editor"}'
```

### 获取用户列表（管理员）

```bash
curl http://localhost:8000/api/users \
  -H "Authorization: Bearer $TOKEN"
```

## 项目管理

### 创建项目

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "我的第一个视频",
    "topic_source": "weibo",
    "topic_title": "人工智能发展趋势",
    "topic_hot_score": 95000
  }'
```

### 项目状态流转

```
pending → topic_selected → script_generated → materials_collected → video_generating → completed
    │                                                        │
    └──────────────────────→ failed ←─────────────────────────┘
```

### 获取项目列表

```bash
# 基本列表
curl http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN"

# 带筛选
curl "http://localhost:8000/api/projects?status=active&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### 获取项目详情

```bash
curl http://localhost:8000/api/projects/{project_id} \
  -H "Authorization: Bearer $TOKEN"
```

### 更新项目

```bash
curl -X PUT http://localhost:8000/api/projects/{project_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "更新后的标题",
    "status": "active"
  }'
```

### 删除项目

```bash
curl -X DELETE http://localhost:8000/api/projects/{project_id} \
  -H "Authorization: Bearer $TOKEN"
```

## 脚本生成

### 生成脚本

```bash
curl -X POST http://localhost:8000/api/scripts/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "{project_id}",
    "topic": "人工智能发展趋势",
    "style": "informative",
    "duration": 60,
    "provider": "claude"
  }'
```

**style 可选值：**
- `informative` - 信息型（科普、新闻）
- `entertaining` - 娱乐型（轻松、幽默）
- `educational` - 教育型（教程、讲解）
- `storytelling` - 叙事型（故事、情感）

### 获取脚本

```bash
curl http://localhost:8000/api/scripts?project_id={project_id} \
  -H "Authorization: Bearer $TOKEN"
```

### 脚本结构

```json
{
  "id": "script-uuid",
  "project_id": "project-uuid",
  "segments": [
    {
      "type": "intro",
      "content": "大家好，今天我们来聊聊...",
      "duration": 5,
      "narration": "大家好，今天我们来聊聊人工智能的发展趋势。"
    },
    {
      "type": "main",
      "content": "人工智能正在改变...",
      "duration": 45,
      "narration": "人工智能正在改变我们生活的方方面面..."
    },
    {
      "type": "outro",
      "content": "感谢观看...",
      "duration": 10,
      "narration": "感谢观看，我们下期再见！"
    }
  ],
  "style": "informative",
  "total_duration": 60
}
```

## 素材收集

### 收集素材

```bash
curl -X POST http://localhost:8000/api/materials/collect \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "{project_id}",
    "keywords": ["人工智能", "科技", "未来"],
    "types": ["image", "video"],
    "count": 10
  }'
```

### 获取项目素材

```bash
curl http://localhost:8000/api/materials?project_id={project_id} \
  -H "Authorization: Bearer $TOKEN"
```

### 素材状态

| 状态 | 描述 |
|------|------|
| `pending` | 待下载 |
| `downloading` | 下载中 |
| `ready` | 已就绪 |
| `failed` | 下载失败 |

### 审核素材

```bash
# 标记素材为已审核
curl -X POST http://localhost:8000/api/materials/{material_id}/approve \
  -H "Authorization: Bearer $TOKEN"

# 拒绝素材
curl -X POST http://localhost:8000/api/materials/{material_id}/reject \
  -H "Authorization: Bearer $TOKEN"
```

## 视频生成

### 生成视频

```bash
curl -X POST http://localhost:8000/api/video/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "{project_id}",
    "resolution": "1080p",
    "fps": 30,
    "aspect_ratio": "16:9",
    "include_subtitles": true
  }'
```

**resolution 可选值：** `720p`, `1080p`, `4k`
**aspect_ratio 可选值：** `16:9`, `9:16`, `1:1`

### 查询生成状态

```bash
curl http://localhost:8000/api/video/status/{task_id} \
  -H "Authorization: Bearer $TOKEN"
```

响应：
```json
{
  "task_id": "task-uuid",
  "status": "processing",
  "progress": 45,
  "message": "正在合成视频片段..."
}
```

### 导出视频

```bash
curl -X POST http://localhost:8000/api/video/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "{project_id}",
    "platforms": ["douyin", "bilibili", "xiaohongshu"],
    "format": "mp4"
  }'
```

**支持的平台：**
- `douyin` - 抖音 (9:16)
- `bilibili` - B站 (16:9)
- `xiaohongshu` - 小红书 (3:4)
- `kuaishou` - 快手 (9:16)
- `weibo` - 微博 (16:9)

## 批量操作

### 批量删除项目

```bash
curl -X POST http://localhost:8000/api/projects/batch/delete \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_ids": ["id1", "id2", "id3"]
  }'
```

响应：
```json
{
  "deleted_count": 3
}
```

### 批量更新项目状态

```bash
curl -X POST http://localhost:8000/api/projects/batch/update-status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_ids": ["id1", "id2"],
    "status": "active"
  }'
```

## 插件系统

### 查看已安装插件

```bash
curl http://localhost:8000/api/plugins \
  -H "Authorization: Bearer $TOKEN"
```

### 启用/禁用插件

```bash
# 启用
curl -X POST http://localhost:8000/api/plugins/{plugin_id}/enable \
  -H "Authorization: Bearer $TOKEN"

# 禁用
curl -X POST http://localhost:8000/api/plugins/{plugin_id}/disable \
  -H "Authorization: Bearer $TOKEN"
```

### 配置插件

```bash
curl -X PUT http://localhost:8000/api/plugins/{plugin_id}/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configurations": {
      "api_key": "your-api-key",
      "timeout": "30"
    }
  }'
```

### 开发自定义插件

1. 创建插件文件 `plugins/material_sources/my_source.py`：

```python
from plugins.material_sources.base import MaterialSourcePlugin
from typing import List, Dict, Any

class MyMaterialSource(MaterialSourcePlugin):
    """自定义素材源"""

    name = "my_source"
    version = "1.0.0"
    description = "我的自定义素材源"
    author = "Developer"
    supported_types = ["image", "video"]

    async def collect(self, keyword: str, count: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """收集素材"""
        results = []
        # 实现你的素材收集逻辑
        for i in range(count):
            results.append({
                "url": f"https://example.com/{keyword}_{i}.jpg",
                "type": "image",
                "title": f"{keyword} image {i}",
                "description": f"Image for {keyword}",
                "thumbnail_url": f"https://example.com/thumb_{i}.jpg",
                "metadata": {
                    "width": 1920,
                    "height": 1080
                }
            })
        return results
```

2. 系统会自动发现并注册插件

## Webhook通知

### 创建Webhook

```bash
curl -X POST http://localhost:8000/api/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "项目完成通知",
    "url": "https://your-server.com/webhook",
    "events": ["project.completed", "project.failed"],
    "secret": "your-webhook-secret"
  }'
```

### 支持的事件

| 事件 | 触发时机 |
|------|---------|
| `project.created` | 项目创建 |
| `project.completed` | 项目完成 |
| `project.failed` | 项目失败 |
| `video.generated` | 视频生成完成 |
| `export.finished` | 导出完成 |

### Webhook载荷格式

```json
{
  "event": "project.completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "project_id": "uuid",
    "title": "项目标题",
    "status": "completed",
    "video_url": "https://..."
  }
}
```

### 签名验证

Webhook请求包含签名头：
```
X-Webhook-Signature: sha256=abc123...
X-Webhook-Event: project.completed
```

验证签名（Python示例）：

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### 查看投递记录

```bash
curl http://localhost:8000/api/webhooks/{webhook_id}/deliveries \
  -H "Authorization: Bearer $TOKEN"
```

## 移动端使用

### 获取移动端项目列表（分页）

```bash
curl "http://localhost:8000/api/mobile/projects?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

响应：
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "项目标题",
      "status": "active",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 10
}
```

### 获取仪表盘摘要

```bash
curl http://localhost:8000/api/mobile/dashboard \
  -H "Authorization: Bearer $TOKEN"
```

响应：
```json
{
  "total_projects": 25,
  "active_projects": 5,
  "completed_projects": 18,
  "draft_projects": 2
}
```

### 快速启动项目

```bash
curl -X POST http://localhost:8000/api/mobile/projects/{project_id}/quick-start \
  -H "Authorization: Bearer $TOKEN"
```

## API参考

### 认证头

所有需要认证的API都需要在请求头中携带Token：

```
Authorization: Bearer <access_token>
```

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见HTTP状态码

| 状态码 | 描述 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无内容） |
| 400 | 请求参数错误 |
| 401 | 未认证/Token无效 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 422 | 参数验证失败 |
| 500 | 服务器内部错误 |

### API文档

启动服务后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 推荐功能

### 获取话题推荐

```bash
curl http://localhost:8000/api/recommendations/topics \
  -H "Authorization: Bearer $TOKEN"
```

响应：
```json
[
  {
    "topic_source": "tech",
    "topic_title": "人工智能最新突破",
    "relevance_score": 0.85
  }
]
```

### 获取相似项目

```bash
curl http://localhost:8000/api/recommendations/similar/{project_id} \
  -H "Authorization: Bearer $TOKEN"
```

## 最佳实践

### 1. 项目创建流程

```
1. 创建项目 → 2. 生成脚本 → 3. 收集素材 → 4. 审核素材 → 5. 生成视频 → 6. 导出
```

### 2. 错误处理

```python
import httpx

async def call_api():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/projects",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 401:
            # Token过期，重新登录
            token = await refresh_token()
        elif response.status_code == 403:
            # 权限不足
            raise PermissionError("Insufficient permissions")
        return response.json()
```

### 3. 批量操作建议

- 每次批量操作不超过100个项目
- 使用异步任务处理大批量操作
- 操作前先确认项目状态

### 4. Webhook最佳实践

- 使用HTTPS URL
- 验证签名确保请求来源
- 实现幂等性处理重复通知
- 快速返回200响应，异步处理业务逻辑