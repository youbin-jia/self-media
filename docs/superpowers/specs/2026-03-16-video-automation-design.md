# 长视频自动化生产系统设计文档

**日期**: 2026-03-16
**版本**: 1.0
**状态**: 待审批

---

## 概述

### 项目背景

构建一个面向自媒体创作者的长视频自动化生产系统，支持从选题到成片的全流程自动化。用户只需确认选题，系统即可自动生成具备完整字幕、配音、背景音乐的高质量长视频，同时支持多平台发布格式。

### 核心目标

- **高效**: 30分钟内完成一条5分钟长视频的生产
- **质量**: 视频具备感染力和吸引力，支持人工把控关键节点
- **灵活**: 支持多种内容类型、发布平台和自定义配置
- **可扩展**: 模块化设计，易于扩展新功能

### 目标平台

- 横屏: B站、YouTube (16:9, 1920x1080)
- 竖屏: 抖音、快手、视频号 (9:16, 1080x1920)

### 内容定位

- **主要类型**: 时事评论类视频
- **更新频率**: 每日1-3条
- **视频时长**: 5-15分钟

---

## 系统架构

### 整体架构

采用**模块化流水线架构**，核心流程：

```
热点监控 → 选题确认 → 脚本生成 → 素材采集 → 配音制作 → 视频合成 → 后期处理 → 多平台导出
```

### 技术栈

**后端**
- 框架: FastAPI (Python)
- 任务队列: Celery + Redis
- 数据库: SQLite (开发) / PostgreSQL (生产)
- ORM: SQLAlchemy
- 缓存: Redis
- 视频处理: FFmpeg + MoviePy

**前端**
- 框架: React 18 + TypeScript
- UI库: Ant Design
- 状态管理: Zustand
- HTTP客户端: Axios

**AI服务**
- LLM: 支持多Provider (Claude, GPT-4, GLM-5, 本地模型)
- TTS: Azure Speech, ElevenLabs, 支持自定义TTS
- 图像生成: DALL-E 3, Midjourney
- 音乐生成: Suno AI, Stable Audio

**素材来源**
- 免费素材库: Pexels, Pixabay, Unsplash
- 网络抓取: 新闻网站、社交媒体
- AI生成: 图像、视频片段

---

## 核心功能模块

### 1. 热点监控模块

**功能目标**
自动监控热点事件，为选题提供候选列表

**数据源**
- 微博热搜、知乎热榜、抖音热榜
- 百度热搜、今日头条热点
- 支持自定义RSS源

**技术实现**
- 爬虫层: RSS API、公开API或爬虫抓取
- 去重算法: 标题相似度 + 时间窗口
- 分类标签: AI自动分析热点类型
- 优先级排序: 热度指数、时效性、相似度

**更新频率**
- 定时任务: 每30分钟自动更新
- 手动刷新: Web界面支持

**Web界面**
- 热点卡片列表展示
- 筛选和搜索功能
- 一键选题按钮

---

### 2. 选题确认与脚本生成模块

**选题确认流程**
1. 用户点击"选用"热点
2. 编辑标题、选择风格、时长
3. 可选上传参考素材

**脚本生成流程**
```
选题信息 → LLM生成大纲 → 用户审核 → LLM详细脚本 → 用户审核
```

**脚本结构**
- 开场Hook (5-10秒)
- 事件背景
- 核心观点 (主体)
- 多角度分析
- 结尾升华

**脚本增强**
- 素材标记: 标注适合插入素材的位置
- 情绪标签: 标记情绪(激动、冷静、幽默)
- 时间轴: 预估时长

**交互设计**
- 左右分栏: 脚本 + 时间轴预览
- 在线编辑
- 一键重新生成

---

### 3. 素材采集与管理模块

**采集流程**

**步骤1: 关键词提取**
- 自动提取关键词和实体
- 理解视觉化需求

**步骤2: 并行采集**

**来源A: 免费素材库**
- Pexels API, Pixabay API, Unsplash API
- 按相关度排序，下载Top 20

**来源B: 网络抓取**
- 新闻网站抓取
- 版权过滤、水印检测

**来源C: AI生成**
- DALL-E 3 / Midjourney生成图片
- 未来接入Sora/Runway生成视频

**步骤3: 智能匹配**
- CLIP模型计算相似度
- 时效性权重
- 质量评分

**步骤4: 素材库管理**
- 按项目分类存储
- 元数据管理(标签、来源、版权)
- 复用机制

**Web界面**
- 素材网格展示
- 预览功能
- 手动选择/替换
- 上传功能

---

### 4. 配音与音频处理模块

**混合配音模式**

**模式A: AI配音**
- 服务商: Azure Speech (性价比), ElevenLabs (高端)
- 支持自定义TTS服务
- 声音克隆: 训练专属音色
- 多角色配音
- 情绪匹配: 语速、音调调整

**模式B: 真人配音**
- Web内置录音功能
- 脚本提示逐句显示
- 波形编辑
- 自动降噪

**音频后期**
- 音量归一化
- 背景音乐自动混音
- 格式转换

---

### 5. 背景音乐模块

**音乐来源**

**免费音乐库**
- YouTube Audio Library
- Pixabay Music
- 预设分类: 激昂、轻快、悲伤、悬疑

**AI生成音乐**
- Suno API / Stable Audio
- 根据情绪和节奏生成

**音乐选择策略**
- 情绪匹配
- 节奏匹配
- 音量控制: 人声优先 (-20dB)

---

### 6. 视频合成模块

**时间轴对齐**
1. 脚本 → 时间轴
2. 素材分配
3. 时长计算
   - 图片: 3-5秒 + Ken Burns效果
   - 视频: 自动裁剪
   - 动画: 数据图表动画模板

**视频编辑引擎**
- 核心: MoviePy + FFmpeg
- 功能:
  - 素材拼接(淡入淡出、硬切)
  - 转场效果
  - 画中画
  - 图片动画

**字幕生成**
- 样式: 底部居中、动态字幕
- 模板: 多种预设
- 同步: 配音时间轴对齐
- 双语字幕: 可选(LLM翻译)

**视频渲染**
- 横屏: 1920x1080 (16:9)
- 竖屏: 1080x1920 (9:16)
- 竖屏适配:
  - 模糊背景
  - 裁剪放大
  - 动态布局

**预览功能**
- 低分辨率预览
- 时间轴可视化编辑

---

### 7. 后期处理与优化模块

**色彩校正**
- 自动调整亮度、对比度、饱和度
- 色彩一致性
- 风格滤镜

**转场优化**
- 自动检测场景切换
- 智能转场效果
- 时长自适应

**特效增强**
- 关键时刻强调
- 数据可视化动画
- 动态字幕

**音频优化**
- 人声增强
- 背景降噪
- 音频均衡

**质量检查**
- 分辨率检查
- 音频质量检测
- 时长检查
- 格式验证

---

### 8. 多平台导出模块

**平台适配**

**横屏版本 (16:9)**
- 分辨率: 1920x1080
- 时长: 5-15分钟
- 字幕: 底部居中
- 封面: 自动生成
- 元数据: 标题、描述、标签

**竖屏版本 (9:16)**
- 分辨率: 1080x1920
- 适配方案:
  - 模糊背景
  - 裁剪放大
  - 动态调整
- 字幕: 放大、上移
- 时长: 完整版或精简版

**平台特定优化**
- B站: 片头片尾、弹幕引导
- 抖音: 快节奏、热门特效
- YouTube: SEO标签、订阅引导
- 视频号: 公众号引导

**批量导出**
- 一键生成所有版本
- 自动命名
- 后台异步渲染
- 进度显示

---

### 9. 项目管理模块

**项目列表**
- 所有项目概览
- 状态标识: 进行中、待审核、已完成、已发布
- 快速操作

**版本控制**
- 多版本保存
- 回退功能
- 对比功能

**数据统计**
- 制作效率统计
- 成本统计
- 质量评估

**素材库管理**
- 分类管理
- 标签系统
- 搜索功能
- 版权管理

---

## 技术实现

### 数据流设计

**完整生产流程**
```
热点监控 → 用户确认选题 → 创建项目
→ 生成脚本大纲 → 用户审核 → 生成详细脚本 → 用户审核
→ 提取关键词 → 并行采集素材 → 素材去重排序 → 用户选择
→ 生成配音 → 选择背景音乐 → 视频合成 → 预览
→ 用户审核 → 后期处理 → 多平台导出 → 项目完成
```

**关键数据对象**
- 项目对象 (project)
- 脚本对象 (script)
- 素材对象 (material)
- 音频对象 (audio)
- 视频对象 (video)

---

### 数据库设计

**核心表结构**

**projects表**
```sql
CREATE TABLE projects (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50),
    current_step VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    topic_source VARCHAR(50),
    topic_title TEXT,
    topic_hot_score INTEGER,
    metadata JSON
);
```

**scripts表**
```sql
CREATE TABLE scripts (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) REFERENCES projects(id),
    version INTEGER,
    outline TEXT,
    full_script TEXT,
    segments JSON,
    created_at TIMESTAMP,
    is_approved BOOLEAN
);
```

**materials表**
```sql
CREATE TABLE materials (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) REFERENCES projects(id),
    type VARCHAR(20),
    source VARCHAR(50),
    source_url TEXT,
    local_path TEXT,
    metadata JSON,
    created_at TIMESTAMP
);
```

**tasks表**
```sql
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) REFERENCES projects(id),
    task_type VARCHAR(50),
    status VARCHAR(50),
    progress INTEGER,
    result JSON,
    error_message TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**configurations表**
```sql
CREATE TABLE configurations (
    key VARCHAR(100) PRIMARY KEY,
    value JSON,
    description TEXT,
    updated_at TIMESTAMP
);
```

---

### API接口设计

**热点相关**
```
GET  /api/topics/list          # 获取热点列表
POST /api/topics/refresh       # 手动刷新热点
POST /api/topics/select        # 确认选题
```

**项目相关**
```
GET  /api/projects             # 获取项目列表
GET  /api/projects/{id}        # 获取项目详情
DELETE /api/projects/{id}      # 删除项目
```

**脚本相关**
```
POST /api/scripts/generate-outline    # 生成大纲
POST /api/scripts/generate-full       # 生成完整脚本
PUT  /api/scripts/{id}                # 更新脚本
POST /api/scripts/{id}/approve        # 批准脚本
```

**素材相关**
```
POST /api/materials/collect           # 采集素材
GET  /api/materials/project/{id}      # 获取项目素材
POST /api/materials/upload            # 上传素材
PUT  /api/materials/{id}/select       # 选择素材
```

**配音相关**
```
POST /api/audio/generate-tts          # 生成AI配音
POST /api/audio/upload                # 上传录音
GET  /api/audio/preview/{id}          # 预览音频
```

**视频相关**
```
POST /api/video/synthesize            # 合成视频预览
POST /api/video/export                # 导出最终视频
GET  /api/video/status/{task_id}      # 查询导出进度
```

**配置相关**
```
GET  /api/config/llm-providers        # 获取LLM配置
POST /api/config/llm-providers        # 添加LLM配置
PUT  /api/config/llm-providers/{id}   # 更新LLM配置
```

---

### 异步任务设计

**Celery任务类型**
```python
@celery.task
def refresh_topics():
    # 抓取热点、去重、排序、存储

@celery.task
def generate_script(project_id, topic_info):
    # 调用LLM生成脚本

@celery.task
def collect_materials(project_id, keywords):
    # 并行采集素材

@celery.task(bind=True)
def synthesize_video(self, project_id):
    # 合成视频，更新进度

@celery.task(bind=True)
def export_video(self, project_id, formats):
    # 导出多个版本
```

**定时任务**
```python
CELERYBEAT_SCHEDULE = {
    'refresh-topics': {
        'task': 'refresh_topics',
        'schedule': 1800.0,  # 每30分钟
    },
}
```

---

### 错误处理与容错

**错误分类**
1. API错误: 重试机制(指数退避)
2. 网络错误: 自动重试、降级
3. 资源错误: 定期清理、限制并发
4. 用户输入错误: 参数验证、友好提示

**重试策略**
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_llm_api(prompt):
    # 调用LLM API
```

**降级策略**
- 素材源降级
- LLM降级
- 功能降级

---

## 安全与性能

### 安全设计

**API密钥管理**
- 环境变量存储
- .env文件不提交git
- 敏感配置加密

**文件上传安全**
- 类型白名单验证
- 大小限制
- 文件名随机化

**输入验证**
- Pydantic模型验证
- 参数校验

**版权合规**
- 素材来源标记
- 版权声明生成
- 合理使用检测

---

### 性能优化

**前端优化**
- 懒加载
- 虚拟滚动
- API缓存
- CDN缓存

**后端优化**
- 数据库索引
- 查询优化
- 异步处理
- Redis缓存

**视频处理优化**
- 并行处理
- 分块处理
- 内存优化
- 限制并发

---

## 部署方案

### 开发环境

**Docker Compose部署**
```yaml
version: '3.8'
services:
  web:
    build: .
    ports: ["8000:8000"]
    depends_on: [db, redis]

  worker:
    build: .
    command: celery -A tasks worker --loglevel=info
    depends_on: [db, redis]

  db:
    image: postgres:14
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:alpine
    volumes: [redisdata:/data]
```

---

### 生产环境

**云服务器配置**
- CPU: 8核
- 内存: 16GB
- 存储: 100GB SSD
- 系统: Ubuntu 22.04

**部署步骤**
1. 安装Docker和Docker Compose
2. 配置环境变量(.env)
3. 启动服务
4. 配置Nginx反向代理
5. 配置HTTPS (Let's Encrypt)

---

### 监控与运维

**日志管理**
- 应用日志: RotatingFileHandler
- 任务日志: Celery日志
- 性能监控: Prometheus

**健康检查**
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": check_database(),
        "redis": check_redis(),
        "disk_space": check_disk_space()
    }
```

**备份策略**
- 数据库每日备份
- 项目文件定期备份
- 配置文件版本控制

---

## 扩展性设计

### 插件系统

**自定义素材源插件**
```python
class MaterialSourcePlugin(ABC):
    @abstractmethod
    def search(self, keyword: str) -> List[Material]:
        pass
```

**自定义LLM Provider**
```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass
```

**Webhook通知**
- 视频完成通知
- 自定义集成

---

## 开发路线图

### Phase 1: MVP核心功能 (2-3周)
- [x] 项目基础设施
- [ ] 热点监控模块
- [ ] 脚本生成模块(单LLM)
- [ ] 基础素材采集
- [ ] 简单视频合成
- [ ] 基础Web界面

### Phase 2: 完善功能 (2-3周)
- [ ] 多LLM Provider支持
- [ ] AI配音集成
- [ ] 素材管理优化
- [ ] 视频编辑增强
- [ ] 多平台导出

### Phase 3: 高级特性 (2-3周)
- [ ] AI生成素材
- [ ] AI生成音乐
- [ ] 高级视频特效
- [ ] 批量处理
- [ ] 数据统计

### Phase 4: 优化与扩展 (持续)
- [ ] 性能优化
- [ ] 用户体验优化
- [ ] 插件系统
- [ ] 移动端适配
- [ ] 多用户支持

---

## 风险与限制

### 技术风险
- AI服务稳定性: 使用备用服务商
- 素材版权: 优先免费库、AI生成
- 视频渲染耗时: 异步队列、进度反馈

### 成本控制
- LLM API成本: 使用性价比高的模型
- 存储成本: 定期清理临时文件
- API调用: 缓存、复用素材

### 法律合规
- 版权声明
- 内容审核
- 平台规则遵守

---

## 总结

本系统通过模块化设计和半自动分步控制，实现了长视频生产的高效与质量平衡。关键特性包括：

1. **灵活的LLM集成**: 支持多种云端和本地模型
2. **多源素材采集**: 免费、抓取、AI生成三管齐下
3. **混合配音模式**: AI配音与真人配音灵活切换
4. **多平台适配**: 一键生成横竖屏版本
5. **可视化工作流**: Web界面直观操作每个环节

系统设计注重可扩展性和容错性，为后续功能迭代和性能优化预留了空间。
