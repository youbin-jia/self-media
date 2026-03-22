# 工作流 UI 插件（前端）

与后端 `plugins/material_sources`（素材源）不同，此处为 **React 工作流步骤扩展组件**。

| 组件 | 用途 |
|------|------|
| `FinalVideoPreviewPlugin` | 视频步骤：内嵌 HTML5 播放成片（同源 `/api/projects/.../video/download`） |
| `VideoPipelineEnvPlugin` | 调用 `GET /api/video/pipeline-env` 展示 LTX-2 / Wan I2V 等管线配置 |
| `VideoGenerationMonitorPlugin` | 视频步骤：LTX 分镜看板、活动日志、本机 CPU/GPU（`/api/video/host-metrics`） |

在 `ProjectWorkflow.jsx` 中按需引入即可。
