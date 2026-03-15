# 长视频自动化生产系统设计文档

**日期**: 2026-03-16
**版本**: 1.2
**状态**: 最终版

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

**用户审核拒绝处理**

当用户在脚本审核环节拒绝通过时，系统提供以下选项：

**脚本大纲被拒绝:**
- **重新生成**: 调整prompt参数（修改风格、调整角度、改变结构）重新生成
- **手动编辑**: 用户直接在编辑器中修改大纲
- **跳过大纲**: 直接进入详细脚本生成（不推荐）

**详细脚本被拒绝:**
- **重新生成指定段落**: 选择不满意的段落重新生成
- **调整参数重新生成**: 修改风格、语气、详细程度等参数
- **手动编辑**: 在线编辑器直接修改
- **回退到大纲**: 重新调整大纲结构

**交互界面实现:**
- 拒绝按钮弹出选项菜单
- 参数调整滑块/下拉框
- 实时预览修改效果
- 版本对比功能（对比修改前后）

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

**边缘情况处理**

**场景1: 无合适素材找到**
- **降级策略**:
  1. 扩大关键词范围（使用同义词、相关词）
  2. 降低相似度阈值（从0.8降至0.6）
  3. 使用通用素材（背景图、抽象图）
  4. 使用纯文字动画代替
- **用户通知**: 明确提示"未找到高质量素材，已使用备选方案"

**场景2: 所有素材评分过低**
- **质量阈值**:
  - 最低可接受分数: 0.5（满分1.0）
  - 分辨率: 图片≥720p，视频≥480p
  - 清晰度: 自动检测模糊度
- **处理流程**:
  1. 标记低质量素材（黄色警告标签）
  2. 优先使用AI生成素材替代
  3. 提示用户上传高质量素材
  4. 允许强制使用低质量素材（用户确认）

**场景3: 素材下载失败**
- **重试机制**:
  - 自动重试3次（指数退避：1s, 2s, 4s）
  - 切换CDN节点或备用URL
- **降级方案**:
  - 标记素材为不可用
  - 从候选列表移除
  - 使用列表中下一个候选素材
- **失败率阈值**:
  - 单个项目失败率>50%: 触发告警
  - 连续多个项目失败率>30%: 检查素材源可用性

**场景4: 素材版权风险**
- **检测机制**:
  - 水印检测（自动标记）
  - 版权信息抓取（元数据）
  - 新闻素材合理性评估
- **处理策略**:
  - 高风险素材: 自动过滤
  - 中风险素材: 标记警告，用户可选
  - 低风险素材: 正常使用，记录来源

**素材库备选方案:**
- 维护一组通用高质量素材（风景、城市、科技等）
- AI生成占位符（根据场景快速生成）
- 文字卡片模板（关键时刻使用）

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

## 用户审核工作流总结

本系统采用**半自动分步控制**模式，在关键节点设置用户审核环节：

### 审核节点一览

| 审核节点 | 审核内容 | 拒绝选项 | 影响范围 |
|---------|---------|---------|---------|
| 热点选题 | 选择合适的热点 | 浏览其他热点、手动输入选题 | 项目初始化 |
| 脚本大纲 | 整体结构和方向 | 重新生成、手动编辑、调整参数 | 后续所有环节 |
| 详细脚本 | 文案质量和准确性 | 重新生成段落、手动编辑、回退大纲 | 配音、字幕、素材选择 |
| 素材选择 | 素材相关性和质量 | 替换素材、重新采集、上传素材 | 视频合成 |
| 配音效果 | 配音质量和情感 | 重新生成、调整参数、真人配音 | 视频合成 |
| 视频预览 | 整体效果 | 调整脚本、素材、配音、音乐 | 后期处理 |

### 审核拒绝处理原则

1. **可回退性**: 任何环节都可以回退到之前的步骤重新开始
2. **版本保存**: 每次修改都保存新版本，可对比历史版本
3. **参数可调**: 提供直观的参数调整界面
4. **智能建议**: AI分析拒绝原因，给出改进建议
5. **最小影响**: 优先局部调整，避免全盘重来

### 审核界面设计

**统一审核组件**:
- 左侧: 待审核内容（脚本/素材/预览）
- 右侧: 操作面板
  - ✅ 通过按钮
  - ❌ 拒绝按钮（展开选项菜单）
  - 🔄 重新生成按钮
  - ✏️ 手动编辑按钮
  - 💾 保存草稿按钮
- 底部: 修改历史时间轴

---

## 质量标准定义

为确保"高质量"视频产出，制定以下可测量标准：

### 脚本质量标准

| 指标 | 标准值 | 检测方法 |
|-----|--------|---------|
| 原创度 | ≥80% | 文本查重检测 |
| 信息密度 | 每分钟≥150字 | 字数统计 |
| 逻辑连贯性 | 段落过渡自然 | AI评分（1-10分，≥7分） |
| 观点明确性 | 有清晰立场 | AI评估（Yes/No） |
| 事实准确性 | 无明显错误 | 基础事实核查 |
| 情绪丰富度 | 包含≥3种情绪标签 | 情绪分析 |

### 素材质量标准

| 指标 | 最低标准 | 推荐标准 | 检测方法 |
|-----|---------|---------|---------|
| 分辨率（图片） | 720p | 1080p+ | 文件元数据 |
| 分辨率（视频） | 480p | 720p+ | 文件元数据 |
| 清晰度 | 无明显模糊 | 高清 | Laplacian方差检测 |
| 相关度 | ≥0.5 | ≥0.7 | CLIP模型评分 |
| 版权风险 | 低风险 | 无风险 | 版权检测API |
| 时效性 | 近30天 | 近7天 | 发布时间 |

### 配音质量标准

| 指标 | 标准值 | 检测方法 |
|-----|--------|---------|
| 音量一致性 | 波动≤±3dB | 音频分析 |
| 语速适中 | 120-180字/分钟 | 时长统计 |
| 发音准确率 | ≥95% | 语音识别校验 |
| 情感匹配度 | 情绪标签一致 | AI情感分析 |
| 信噪比 | ≥30dB | 音频分析 |
| 无爆音失真 | 是 | 波形检测 |

### 视频质量标准

| 指标 | 标准值 | 检测方法 |
|-----|--------|---------|
| 输出分辨率 | 1080p | 文件属性 |
| 码率 | ≥5Mbps | FFmpeg检测 |
| 帧率 | 30fps | FFmpeg检测 |
| 音画同步 | 偏差≤100ms | FFmpeg检测 |
| 字幕准确率 | 100% | 人工抽检 |
| 字幕可读性 | 字号≥36px | 自动检测 |

### 整体视频质量评分

**综合评分公式**:
```
总分 = 脚本质量(30%) + 素材质量(25%) + 配音质量(20%) + 剪辑质量(15%) + 创意度(10%)
```

**质量等级**:
- A级 (90-100分): 优秀，可直接发布
- B级 (80-89分): 良好，建议小修后发布
- C级 (70-79分): 合格，建议修改后发布
- D级 (60-69分): 待改进，需要重大修改
- E级 (<60分): 不合格，建议重新制作

**自动质量检测**:
- 每个项目完成后自动生成质量报告
- 标注不达标的指标项
- 提供改进建议

---

## 故障恢复与容错策略

### 长时间任务故障恢复

#### 视频合成任务

**任务阶段划分**:
1. 素材预处理（10%）
2. 时间轴构建（20%）
3. 视频片段合成（40%）
4. 音频混合（10%）
5. 字幕添加（10%）
6. 渲染输出（10%）

**故障恢复机制**:

**方案A: 检查点恢复（推荐）**
- 每个阶段完成时保存检查点
- 记录已处理的数据和中间结果
- 故障后从最近的检查点恢复
- 实现示例:
```python
def synthesize_video(project_id):
    checkpoint = load_checkpoint(project_id)
    if checkpoint:
        start_stage = checkpoint['stage']
        resume_data = checkpoint['data']
    else:
        start_stage = 1

    if start_stage <= 1:
        materials = preprocess_materials()
        save_checkpoint(project_id, stage=1, data=materials)

    if start_stage <= 2:
        timeline = build_timeline(materials)
        save_checkpoint(project_id, stage=2, data=timeline)

    # ... 继续后续阶段
```

**方案B: 幂等性设计**
- 每个操作可重复执行
- 检查是否已完成，避免重复工作
- 实现示例:
```python
def process_material(material_id):
    output_path = f"cache/{material_id}_processed.mp4"
    if os.path.exists(output_path):
        return output_path  # 已处理，直接返回

    # 执行处理
    result = ffmpeg_process(material_id)
    return output_path
```

**故障处理流程**:
1. **检测故障**: Celery任务失败捕获异常
2. **分类错误**:
   - 可恢复错误: 超时、网络问题、临时资源不足
   - 不可恢复错误: 数据损坏、配置错误、代码bug
3. **可恢复错误**:
   - 等待5分钟后自动重试（最多3次）
   - 从检查点恢复
   - 通知用户进度
4. **不可恢复错误**:
   - 记录详细错误日志
   - 标记项目状态为"error"
   - 通知用户并提示可能的解决方案
5. **用户选择**:
   - 重试任务
   - 回退到上一个审核节点
   - 放弃项目

#### 视频导出任务

**多格式并行导出**:
- 横屏和竖屏版本独立导出
- 一个失败不影响另一个
- 实现示例:
```python
@celery.task
def export_video(project_id):
    results = {}
    tasks = [
        export_horizontal.delay(project_id),
        export_vertical.delay(project_id)
    ]

    for task in tasks:
        try:
            result = task.get(timeout=600)  # 10分钟超时
            results[task.id] = result
        except Exception as e:
            results[task.id] = {'error': str(e)}

    return results
```

**部分成功处理**:
- 横屏成功、竖屏失败: 提供横屏版本，允许单独重导出竖屏
- 两个都失败: 提供错误详情，允许重新导出

### 数据库事务一致性

**项目状态更新**:
```python
from sqlalchemy import transaction

def update_project_step(project_id, new_step):
    with transaction:
        project = db.query(Project).get(project_id)
        old_step = project.current_step
        project.current_step = new_step
        project.updated_at = datetime.now()
        db.commit()

        # 记录状态变更历史
        history = ProjectHistory(
            project_id=project_id,
            from_step=old_step,
            to_step=new_step,
            timestamp=datetime.now()
        )
        db.add(history)
        db.commit()
```

### 资源清理策略

**临时文件清理**:
- 定时任务: 每天凌晨2点清理超过7天的临时文件
- 项目完成时: 保留最终输出，清理中间文件
- 磁盘空间告警: 剩余空间<20%时触发清理

**任务超时控制**:
```python
@celery.task(time_limit=3600)  # 1小时硬限制
def long_running_task(project_id):
    try:
        # 任务执行
        pass
    except TimeLimitExceeded:
        # 保存当前进度
        save_checkpoint(project_id)
        raise
```

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

**quality_reports表**
```sql
CREATE TABLE quality_reports (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) REFERENCES projects(id),
    report_type VARCHAR(50), -- script, material, audio, video, overall
    overall_score DECIMAL(5,2),
    grade VARCHAR(1), -- A, B, C, D, E
    metrics JSON, -- 存储各项指标的详细评分
    issues JSON, -- 存储发现的问题列表
    recommendations JSON, -- 存储改进建议
    created_at TIMESTAMP
);
```

---

### API接口设计

**认证策略**

本系统采用**API Key认证**机制（初期版本）：

**认证方式**:
- 每个用户分配唯一的API Key
- 通过HTTP Header传递: `Authorization: Bearer <api_key>`
- 服务端验证API Key的有效性和权限

**实现示例**:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = credentials.credentials
    user = validate_api_key(api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return user
```

**权限控制**:
- Phase 1-3: 单用户模式，API Key用于基本认证
- Phase 4: 多用户模式，支持角色权限管理（admin, editor, viewer）

**API Key管理**:
- Web界面生成和管理API Key
- 支持重置和撤销
- 访问日志记录

---

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

## 测试策略

### 测试层级

**1. 单元测试**
- 覆盖范围: 核心业务逻辑、工具函数、数据处理
- 框架: pytest
- 目标覆盖率: ≥80%

**关键测试点**:
```python
# 素材质量检测
def test_material_quality_scoring():
    material = create_test_material(resolution='720p', clarity_score=0.8)
    score = calculate_quality_score(material)
    assert score >= 0.6

# 脚本生成
def test_script_generation():
    topic = create_test_topic()
    script = generate_script(topic)
    assert len(script.segments) > 0
    assert script.word_count >= 500

# 音频处理
def test_audio_normalization():
    audio = load_test_audio()
    normalized = normalize_audio(audio)
    assert abs(normalized.volume - target_volume) < 1.0
```

---

**2. 集成测试**
- 覆盖范围: 模块间交互、API端点、数据库操作
- 重点: 视频合成管道、素材采集流程、任务队列

**关键集成测试场景**:

**视频合成管道测试**:
```python
def test_video_synthesis_pipeline():
    # 准备测试数据
    project = create_test_project()
    script = create_test_script(project.id)
    materials = create_test_materials(project.id, count=5)

    # 执行视频合成
    result = synthesize_video(project.id)

    # 验证输出
    assert os.path.exists(result.output_path)
    assert result.duration > 0
    assert result.quality_score >= 60
```

**素材采集流程测试**:
```python
def test_material_collection_with_fallback():
    # 模拟素材源失败
    mock_pexels_failure()
    mock_pixabay_success()

    # 执行采集
    materials = collect_materials('test keyword')

    # 验证降级策略
    assert len(materials) > 0
    assert all(m.source != 'pexels' for m in materials)
```

**任务队列测试**:
```python
def test_celery_task_retry():
    # 模拟临时失败
    with mock.patch('tasks.generate_script', side_effect=Exception('API Error')):
        task = generate_script.delay(project_id)

    # 验证重试机制
    assert task.retry_count <= 3
    assert task.status in ['RETRY', 'FAILURE']
```

---

**3. 端到端测试 (E2E)**
- 覆盖范围: 完整用户工作流
- 工具: Playwright / Selenium
- 频率: 每日自动运行

**核心用户流程测试**:
```python
def test_complete_video_production_flow():
    # 1. 访问首页
    page.goto('/')
    assert page.title() == 'Video Automation'

    # 2. 选择热点
    topics = page.query_selector_all('.topic-card')
    assert len(topics) > 0
    topics[0].click()

    # 3. 确认选题
    page.fill('#title', 'Test Video')
    page.click('#confirm')

    # 4. 审核脚本
    page.wait_for_selector('.script-preview')
    page.click('#approve-script')

    # 5. 选择素材
    materials = page.query_selector_all('.material-item')
    for m in materials[:5]:
        m.click()
    page.click('#confirm-materials')

    # 6. 生成预览
    page.click('#generate-preview')
    page.wait_for_selector('.video-preview', timeout=60000)

    # 7. 导出视频
    page.click('#export-video')
    page.wait_for_selector('.download-link', timeout=300000)

    # 验证导出文件
    download_link = page.query_selector('.download-link')
    assert download_link is not None
```

---

**4. 性能测试**
- 工具: Locust / Apache Bench
- 目标: 支持并发处理10个项目

**负载测试场景**:
```python
from locust import HttpUser, task, between

class VideoProductionUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_project(self):
        self.client.post("/api/projects", json={
            "title": "Test Project",
            "topic_id": "test_topic"
        })

    @task
    def get_projects(self):
        self.client.get("/api/projects")
```

**性能基准**:
- API响应时间: P95 < 500ms
- 视频合成: 5分钟视频 < 10分钟处理时间
- 并发处理: 支持10个并发项目
- 内存使用: 单个视频合成 < 2GB

---

**5. 质量检测测试**
- 验证自动质量检测系统的准确性
- 对比人工评估和自动评分

**测试用例**:
```python
def test_script_quality_detection():
    # 准备测试脚本
    high_quality_script = create_script_from_template('excellent')
    low_quality_script = create_script_from_template('poor')

    # 执行质量检测
    high_score = detect_script_quality(high_quality_script)
    low_score = detect_script_quality(low_quality_script)

    # 验证评分合理性
    assert high_score >= 85
    assert low_score < 60
    assert high_score > low_score

def test_video_quality_accuracy():
    # 人工标注的视频质量
    ground_truth = load_human_rated_videos()

    # 自动评分
    predictions = []
    for video in ground_truth:
        score = detect_video_quality(video)
        predictions.append(score)

    # 验证相关性
    correlation = calculate_correlation(ground_truth, predictions)
    assert correlation >= 0.7  # 相关性阈值
```

---

### 测试数据管理

**测试数据集**:
- 样本脚本库: 100+不同风格的脚本
- 测试素材库: 图片、视频、音频样本
- Mock API响应: LLM、TTS、素材API的模拟响应

**数据生成**:
```python
# 自动生成测试数据
def generate_test_project():
    return Project(
        id=uuid.uuid4(),
        title=f"Test Project {random.randint(1000, 9999)}",
        topic_title=random.choice(TOPIC_SAMPLES),
        created_at=datetime.now()
    )
```

---

### CI/CD集成

**GitHub Actions配置**:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run unit tests
        run: pytest tests/unit --cov=app --cov-report=xml

      - name: Run integration tests
        run: pytest tests/integration

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

### 测试报告

**自动生成报告**:
- 测试覆盖率报告
- 性能测试报告
- 质量检测准确率报告

**报告格式**:
```json
{
  "test_run_id": "run_123",
  "timestamp": "2026-03-16T10:00:00Z",
  "summary": {
    "total_tests": 150,
    "passed": 148,
    "failed": 2,
    "coverage": "82%"
  },
  "performance": {
    "avg_api_response": "245ms",
    "video_synthesis_time": "8.5min"
  }
}
```

---

## 扩展性设计（Phase 4）

以下扩展功能计划在Phase 4实现，为系统提供更强的可扩展性：

### 插件系统

**自定义素材源插件**
```python
class MaterialSourcePlugin(ABC):
    @abstractmethod
    def search(self, keyword: str) -> List[Material]:
        """搜索素材"""
        pass

    @abstractmethod
    def download(self, material_id: str) -> str:
        """下载素材到本地"""
        pass

# 插件注册机制
plugin_registry = {}

def register_material_source(name: str, plugin: MaterialSourcePlugin):
    """注册自定义素材源"""
    plugin_registry[name] = plugin
    # 更新配置，可在Web界面选择使用
```

**自定义LLM Provider**
```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass

    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs):
        """流式生成（实时输出）"""
        pass

# 用户可实现自己的Provider
class CustomGLMProvider(LLMProvider):
    def __init__(self, model_path: str):
        self.model = load_local_model(model_path)

    def generate(self, prompt: str, **kwargs) -> str:
        return self.model.generate(prompt, **kwargs)
```

**插件管理界面**:
- 查看已注册插件列表
- 启用/禁用插件
- 配置插件参数
- 测试插件功能

### Webhook通知

**支持事件**:
- 视频合成完成
- 视频导出完成
- 任务失败告警
- 热点更新通知

**配置示例**:
```json
{
  "webhooks": [
    {
      "event": "video.export.completed",
      "url": "https://your-server.com/webhook",
      "method": "POST",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  ]
}
```

**通知数据格式**:
```json
{
  "event": "video.export.completed",
  "project_id": "proj_123",
  "timestamp": "2026-03-16T10:30:00Z",
  "data": {
    "horizontal_video": "/videos/proj_123_horizontal.mp4",
    "vertical_video": "/videos/proj_123_vertical.mp4",
    "duration": 320,
    "quality_score": 85
  }
}
```

**重试策略**:
- 失败后自动重试3次
- 指数退避: 1s, 5s, 30s
- 记录失败日志

### 其他扩展方向

**API开放平台**:
- 提供完整的RESTful API
- 支持第三方应用集成
- API密钥管理和限流

**模板市场**:
- 用户可分享视频模板
- 预设风格、转场、特效组合
- 一键应用模板

**协作功能**:
- 多人协作编辑
- 评论和批注
- 版本对比和合并

---

## 开发路线图

### 规划策略

本项目采用**分阶段增量开发**策略，每个Phase作为独立的开发周期，完成后进行验收和测试，确保质量后再进入下一阶段。

**实施计划策略**:
- 每个Phase创建独立的实施计划文档，避免单一庞大计划
- 每个Phase包含完整的开发、测试、文档工作
- Phase间有明确的验收标准和交付物
- 支持根据实际情况调整后续Phase的优先级

**阶段依赖关系**:
```
Phase 1 (MVP) → Phase 2 (完善) → Phase 3 (高级特性) → Phase 4 (优化扩展)
```

---

### Phase 1: MVP核心功能 (2-3周)

**目标**: 实现从选题到视频输出的完整最小可行产品

**核心功能**:
- [x] 项目基础设施（FastAPI后端 + React前端框架）
- [ ] 热点监控模块（单一数据源）
- [ ] 脚本生成模块（单LLM Provider）
- [ ] 基础素材采集（免费素材库）
- [ ] 简单视频合成（图片拼接 + 字幕）
- [ ] 基础Web界面（选题、脚本审核、预览）
- [ ] 用户审核拒绝处理流程（基础版）
- [ ] 故障检查点恢复机制（视频合成）
- [ ] **质量标准自动检测**（提前到Phase 1，便于验证MVP质量）

**交付物**:
- 可运行的本地Web应用
- 能完成完整的视频生产流程
- 自动生成质量报告
- 基础测试覆盖（单元测试 + 集成测试）

**验收标准**:
- 能在30分钟内生成一条5分钟的测试视频
- 视频质量评分达到C级以上
- 核心功能测试覆盖率≥70%

---

### Phase 2: 完善功能 (2-3周)

**目标**: 提升系统稳定性和用户体验

**核心功能**:
- [ ] 多LLM Provider支持（Claude、GPT-4、GLM-5）
- [ ] AI配音集成（Azure Speech、ElevenLabs）
- [ ] 素材管理优化（素材库、去重、标签）
- [ ] 视频编辑增强（转场、特效、画中画）
- [ ] 多平台导出（横屏 + 竖屏）
- [ ] 素材采集边缘情况处理（完整降级策略）
- [ ] **综合质量评分系统**（提前到Phase 2）

**交付物**:
- 多LLM Provider切换功能
- 高质量AI配音
- 多平台视频格式支持
- 完善的错误处理和降级机制
- 综合质量评分和改进建议

**验收标准**:
- 支持3种以上LLM Provider
- 配音质量评分≥80分
- 素材采集成功率≥90%
- 多平台导出正常工作

---

### Phase 3: 高级特性 (2-3周)

**目标**: 提升视频质量和生产效率

**核心功能**:
- [ ] AI生成素材（DALL-E 3、Midjourney集成）
- [ ] AI生成音乐（Suno AI集成）
- [ ] 高级视频特效（数据可视化、动态字幕）
- [ ] 批量处理（多个项目并发）
- [ ] 数据统计（制作效率、成本分析）

**交付物**:
- AI生成素材功能
- AI音乐生成功能
- 高级特效库
- 批量处理能力
- 数据统计看板

**验收标准**:
- AI生成素材可用率≥80%
- 音乐生成与视频情绪匹配度≥85%
- 支持同时处理5个项目

---

### Phase 4: 优化与扩展 (持续)

**目标**: 性能优化和生态扩展

**核心功能**:
- [ ] 性能优化（缓存、并发、渲染速度）
- [ ] 用户体验优化（界面优化、快捷操作）
- [ ] 插件系统（自定义素材源、LLM Provider）
- [ ] Webhook通知集成（第三方集成）
- [ ] 移动端适配（响应式设计）
- [ ] 多用户支持（用户管理、权限控制）

**交付物**:
- 性能优化报告和改进
- 插件系统和示例插件
- Webhook集成文档
- 移动端友好界面
- 多用户系统

**验收标准**:
- API响应时间P95 < 300ms
- 视频合成速度提升30%
- 插件系统可用性验证通过

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
