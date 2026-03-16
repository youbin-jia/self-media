# Phase 3 高级特性设计文档

**日期**: 2026-03-17
**版本**: 1.0
**状态**: 设计阶段

---

## 概述

### 项目背景

在 Phase 1（核心功能）和 Phase 2（完善功能）的基础上，Phase 3 将进一步提升系统的内容创作能力、生产效率和数据分析能力，引入 AI 生成素材、AI 音乐生成、高级视频特效、批量处理和数据统计等高级特性。

### 核心目标

- **内容创作能力提升**: AI 生成素材和音乐，降低对外部素材库的依赖
- **视频质量增强**: 数据可视化和动态字幕提升内容表现力
- **生产效率优化**: 批量处理和智能调度提升产能
- **运营决策支持**: 数据统计提供成本和效率洞察

### 目标用户

- 自媒体创作者：需要高效批量生产视频内容
- 内容运营团队：需要数据驱动的生产优化
- 成本敏感用户：需要控制 API 调用成本

---

## 系统架构

### 整体架构

在现有架构基础上扩展：

```
现有架构（Phase 1 & 2）:
├── 热点监控 → 选题确认 → 脚本生成 → 素材采集 → 配音制作 → 视频合成 → 多平台导出
└── Provider 模式: LLM Provider, TTS Provider, Video Effects

Phase 3 新增模块:
├── AI 生成服务 (AIGenerationProvider)
│   ├── ImageGenerator (DALL-E 3, Midjourney)
│   └── MusicGenerator (Suno AI)
├── 高级特效服务 (AdvancedEffects)
│   ├── DataVisualization (数据可视化)
│   └── DynamicSubtitle (动态字幕)
├── 批量处理服务 (BatchProcessing)
│   └── SmartScheduler (智能队列调度)
└── 数据统计服务 (Analytics)
    ├── MetricsCollector (指标收集)
    └── DashboardAPI (仪表板 API)
```

### 技术栈

**新增依赖：**
- DALL-E 3: OpenAI API
- Midjourney: 第三方 API 服务
- Suno AI: Suno API
- 数据可视化: matplotlib, plotly
- 系统监控: psutil
- 图表渲染: Pillow, cairosvg

**现有依赖复用：**
- FastAPI, Celery, Redis
- SQLAlchemy, SQLite
- MoviePy, FFmpeg

---

## 核心功能模块

### 1. AI 生成服务

#### 1.1 AI 生成 Provider 架构

遵循现有 Provider 模式，创建统一的 AI 生成接口：

```python
# backend/app/services/ai_generation/__init__.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

class AIGenerationProvider(ABC):
    """AI 生成服务基类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        style: str = "realistic",
        size: tuple = (1920, 1080),
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图像

        Args:
            prompt: 图像描述
            style: 风格 (realistic, artistic, cinematic)
            size: 尺寸 (width, height)

        Returns:
            {
                "success": bool,
                "image_path": str,
                "provider": str,
                "metadata": dict
            }
        """
        pass

    @abstractmethod
    async def generate_music(
        self,
        script_context: dict,
        duration: float,
        mood: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成音乐

        Args:
            script_context: 脚本上下文信息
            duration: 时长（秒）
            mood: 情绪 (auto, tense, relaxed, inspiring, sad)

        Returns:
            {
                "success": bool,
                "music_path": str,
                "duration": float,
                "provider": str,
                "metadata": dict
            }
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """支持的能力列表"""
        pass
```

#### 1.2 DALL-E 3 Provider（默认）

```python
# backend/app/services/ai_generation/dalle_provider.py

from openai import AsyncOpenAI
from typing import Dict, Any, Optional
import httpx
from pathlib import Path
from .base import AIGenerationProvider

class DALLEProvider(AIGenerationProvider):
    """DALL-E 3 图像生成（默认选项）"""

    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "dalle"

    @property
    def capabilities(self) -> List[str]:
        return ["image_generation"]

    async def generate_image(
        self,
        prompt: str,
        style: str = "realistic",
        size: tuple = (1920, 1080),
        **kwargs
    ) -> Dict[str, Any]:
        """使用 DALL-E 3 生成图像"""

        # 转换尺寸到 DALL-E 支持的格式
        dalle_size = self._map_size(size)

        # 增强提示词
        enhanced_prompt = self._enhance_prompt(prompt, style)

        try:
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=dalle_size,
                quality="standard",
                n=1
            )

            image_url = response.data[0].url

            # 下载图像
            image_path = await self._download_image(image_url)

            return {
                "success": True,
                "image_path": image_path,
                "provider": self.provider_name,
                "metadata": {
                    "prompt": enhanced_prompt,
                    "size": size,
                    "style": style
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider_name
            }

    async def generate_music(self, *args, **kwargs) -> Dict[str, Any]:
        """DALL-E 不支持音乐生成"""
        raise NotImplementedError("DALL-E does not support music generation")

    def _map_size(self, target_size: tuple) -> str:
        """映射到 DALL-E 支持的尺寸"""
        width, height = target_size

        # DALL-E 3 支持: 1024x1024, 1792x1024, 1024x1792
        if width > height:
            return "1792x1024"  # 横屏
        elif height > width:
            return "1024x1792"  # 竖屏
        else:
            return "1024x1024"  # 方形

    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """增强提示词"""
        style_modifiers = {
            "realistic": "photorealistic, high detail, professional photography",
            "artistic": "artistic style, creative interpretation",
            "cinematic": "cinematic lighting, dramatic composition, movie scene"
        }

        modifier = style_modifiers.get(style, "")
        return f"{prompt}, {modifier}" if modifier else prompt

    async def _download_image(self, url: str) -> str:
        """下载生成的图像"""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            # 保存到临时文件
            image_path = f"data/ai_generated/{uuid.uuid4()}.png"
            Path(image_path).parent.mkdir(parents=True, exist_ok=True)
            Path(image_path).write_bytes(response.content)

            return image_path
```

#### 1.3 Midjourney Provider（高级选项）

```python
# backend/app/services/ai_generation/midjourney_provider.py

import httpx
from typing import Dict, Any, Optional
from .base import AIGenerationProvider

class MidjourneyProvider(AIGenerationProvider):
    """Midjourney 图像生成（高级选项）"""

    def __init__(self, api_key: str, endpoint: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = api_key
        self.endpoint = endpoint

    @property
    def provider_name(self) -> str:
        return "midjourney"

    @property
    def capabilities(self) -> List[str]:
        return ["image_generation", "artistic_styles"]

    async def generate_image(
        self,
        prompt: str,
        style: str = "artistic",
        size: tuple = (1920, 1080),
        **kwargs
    ) -> Dict[str, Any]:
        """使用 Midjourney 生成图像"""

        # Midjourney 特定的提示词格式
        mj_prompt = self._format_prompt(prompt, style, size)

        try:
            async with httpx.AsyncClient() as client:
                # 提交生成任务
                response = await client.post(
                    f"{self.endpoint}/generate",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"prompt": mj_prompt},
                    timeout=30.0
                )
                response.raise_for_status()
                task_id = response.json()["task_id"]

                # 轮询等待结果
                image_url = await self._wait_for_result(task_id)

                # 下载图像
                image_path = await self._download_image(image_url)

                return {
                    "success": True,
                    "image_path": image_path,
                    "provider": self.provider_name,
                    "metadata": {
                        "prompt": mj_prompt,
                        "size": size,
                        "style": style
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider_name
            }

    async def generate_music(self, *args, **kwargs) -> Dict[str, Any]:
        """Midjourney 不支持音乐生成"""
        raise NotImplementedError("Midjourney does not support music generation")

    def _format_prompt(self, prompt: str, style: str, size: tuple) -> str:
        """格式化为 Midjourney 提示词格式"""
        aspect_ratio = f"--ar {size[0]}:{size[1]}"

        style_params = {
            "realistic": "--v 5.2 --style raw",
            "artistic": "--v 5.2 --stylize 750",
            "cinematic": "--v 5.2 --style cinematic"
        }

        style_flag = style_params.get(style, "--v 5.2")

        return f"{prompt} {aspect_ratio} {style_flag}"

    async def _wait_for_result(self, task_id: str, timeout: int = 300) -> str:
        """等待生成完成"""
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.endpoint}/task/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                data = response.json()

                if data["status"] == "completed":
                    return data["image_url"]
                elif data["status"] == "failed":
                    raise RuntimeError(f"Midjourney task failed: {data.get('error')}")

                await asyncio.sleep(5)  # 等待 5 秒后重试

        raise TimeoutError("Midjourney generation timed out")
```

#### 1.4 Suno AI Provider

```python
# backend/app/services/ai_generation/suno_provider.py

import httpx
from typing import Dict, Any, Optional, List
from .base import AIGenerationProvider

class SunoProvider(AIGenerationProvider):
    """Suno AI 音乐生成"""

    def __init__(self, api_key: str, endpoint: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = api_key
        self.endpoint = endpoint

    @property
    def provider_name(self) -> str:
        return "suno"

    @property
    def capabilities(self) -> List[str]:
        return ["music_generation", "mood_analysis"]

    async def generate_image(self, *args, **kwargs) -> Dict[str, Any]:
        """Suno 不支持图像生成"""
        raise NotImplementedError("Suno does not support image generation")

    async def generate_music(
        self,
        script_context: dict,
        duration: float,
        mood: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """使用 Suno AI 生成音乐"""

        # 自动分析情绪
        if mood == "auto":
            mood = await self._analyze_mood(script_context)

        # 生成音乐描述
        music_prompt = self._create_music_prompt(script_context, mood, duration)

        try:
            async with httpx.AsyncClient() as client:
                # 提交生成任务
                response = await client.post(
                    f"{self.endpoint}/generate",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "prompt": music_prompt,
                        "duration": duration,
                        "mood": mood,
                        "instrumental": True  # 纯音乐，无歌词
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                task_id = response.json()["task_id"]

                # 等待生成完成
                music_url = await self._wait_for_result(task_id)

                # 下载音乐
                music_path = await self._download_music(music_url)

                return {
                    "success": True,
                    "music_path": music_path,
                    "duration": duration,
                    "provider": self.provider_name,
                    "metadata": {
                        "mood": mood,
                        "prompt": music_prompt
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider_name
            }

    async def _analyze_mood(self, script_context: dict) -> str:
        """分析脚本情绪"""
        from app.services.llm import llm_manager

        llm = llm_manager.get_provider("claude")

        prompt = f"""
        分析以下脚本内容的情绪基调，从以下选项中选择最匹配的情绪：
        - tense: 紧张、悬疑、危机
        - relaxed: 轻松、愉悦、日常
        - inspiring: 激昂、励志、正能量
        - sad: 悲伤、沉重、反思

        脚本摘要: {script_context.get('summary', '')}
        关键词: {', '.join(script_context.get('keywords', []))}

        只返回情绪类型，不要解释。
        """

        mood = await llm.generate(prompt, temperature=0.3)
        return mood.strip().lower()

    def _create_music_prompt(self, script_context: dict, mood: str, duration: float) -> str:
        """创建音乐生成提示"""
        topic = script_context.get('topic', '')
        keywords = script_context.get('keywords', [])

        prompt = f"Background music for a video about {topic}"

        if keywords:
            prompt += f" with themes of {', '.join(keywords[:3])}"

        prompt += f". {mood} mood, suitable for {duration:.0f} seconds duration"

        return prompt

    async def _wait_for_result(self, task_id: str, timeout: int = 180) -> str:
        """等待音乐生成完成"""
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.endpoint}/task/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                data = response.json()

                if data["status"] == "completed":
                    return data["music_url"]
                elif data["status"] == "failed":
                    raise RuntimeError(f"Suno task failed: {data.get('error')}")

                await asyncio.sleep(3)

        raise TimeoutError("Suno music generation timed out")
```

#### 1.5 AI 生成 Provider Manager

```python
# backend/app/services/ai_generation/__init__.py

from typing import Dict, Any
from .base import AIGenerationProvider
from .dalle_provider import DALLEProvider
from .midjourney_provider import MidjourneyProvider
from .suno_provider import SunoProvider
from app.config import settings
import threading

class AIGenerationManager:
    """AI 生成服务管理器"""

    _instance = None
    _lock = threading.Lock()
    _providers: Dict[str, AIGenerationProvider] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._providers = {}
                    cls._instance._initialize_providers()
        return cls._instance

    def _initialize_providers(self):
        """初始化所有配置的 provider"""

        # DALL-E 3 (OpenAI)
        if settings.OPENAI_API_KEY:
            self._providers["dalle"] = DALLEProvider(
                api_key=settings.OPENAI_API_KEY
            )

        # Midjourney
        if settings.MIDJOURNEY_API_KEY and settings.MIDJOURNEY_ENDPOINT:
            self._providers["midjourney"] = MidjourneyProvider(
                api_key=settings.MIDJOURNEY_API_KEY,
                endpoint=settings.MIDJOURNEY_ENDPOINT
            )

        # Suno AI
        if settings.SUNO_API_KEY and settings.SUNO_ENDPOINT:
            self._providers["suno"] = SunoProvider(
                api_key=settings.SUNO_API_KEY,
                endpoint=settings.SUNO_ENDPOINT
            )

    def get_image_provider(self, name: str = None) -> AIGenerationProvider:
        """获取图像生成 provider"""
        name = name or settings.DEFAULT_IMAGE_PROVIDER

        if name not in self._providers:
            raise ValueError(f"Image provider '{name}' not available")

        provider = self._providers[name]
        if "image_generation" not in provider.capabilities:
            raise ValueError(f"Provider '{name}' does not support image generation")

        return provider

    def get_music_provider(self) -> AIGenerationProvider:
        """获取音乐生成 provider"""
        if "suno" not in self._providers:
            raise ValueError("Music provider not available")

        return self._providers["suno"]

    def list_providers(self) -> Dict[str, Any]:
        """列出所有可用的 provider"""
        return {
            name: {
                "name": provider.provider_name,
                "capabilities": provider.capabilities
            }
            for name, provider in self._providers.items()
        }


# 全局管理器实例
ai_generation_manager = AIGenerationManager()
```

#### 1.6 集成到素材采集流程

```python
# backend/app/services/material_collector.py 修改

from app.services.ai_generation import ai_generation_manager

class MaterialCollector:

    async def collect_materials(
        self,
        query: str,
        project_id: int,
        count: int = 10,
        sources: List[str] = ["pexels", "pixabay", "unsplash", "ai_generated", "fallback"]
    ) -> List[Material]:
        """采集素材（包含 AI 生成）"""

        collected = []

        for source in sources:
            try:
                if source == "pexels":
                    materials = await self._collect_from_pexels(query, project_id, count - len(collected))
                elif source == "pixabay":
                    materials = await self._collect_from_pixabay(query, project_id, count - len(collected))
                elif source == "unsplash":
                    materials = await self._collect_from_unsplash(query, project_id, count - len(collected))
                elif source == "ai_generated":
                    materials = await self._generate_ai_materials(query, project_id, count - len(collected))
                else:
                    continue

                collected.extend(materials)

                if len(collected) >= count:
                    break

            except Exception as e:
                logger.warning(f"Failed to collect from {source}: {str(e)}")
                continue

        # Fallback
        if len(collected) < count:
            collected.extend(self._get_fallback_materials(project_id, count - len(collected)))

        return collected[:count]

    async def _generate_ai_materials(
        self,
        query: str,
        project_id: int,
        count: int
    ) -> List[Material]:
        """AI 生成素材"""

        materials = []
        provider = ai_generation_manager.get_image_provider()

        for i in range(count):
            try:
                result = await provider.generate_image(
                    prompt=query,
                    style="cinematic",
                    size=(1920, 1080)
                )

                if result["success"]:
                    material = Material(
                        project_id=project_id,
                        material_type="image",
                        source="ai_generated",
                        source_id=f"ai_{uuid.uuid4()}",
                        local_path=result["image_path"],
                        tags=[query, "ai_generated"],
                        material_metadata=result["metadata"]
                    )

                    self.db.add(material)
                    materials.append(material)

            except Exception as e:
                logger.error(f"AI material generation failed: {str(e)}")
                continue

        self.db.commit()
        return materials
```

---

### 2. 高级视频特效服务

#### 2.1 数据可视化特效

```python
# backend/app/services/effects/data_visualization.py

from typing import Dict, Any, List
from moviepy.editor import VideoClip, ImageClip, CompositeVideoClip
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import numpy as np
from pathlib import Path

class DataVisualizationEffect:
    """数据可视化特效"""

    def __init__(self):
        self.style_presets = {
            "modern": {
                "colors": ["#3498db", "#e74c3c", "#2ecc71", "#f39c12"],
                "background": "#2c3e50",
                "font_family": "Arial",
                "font_size": 48
            },
            "classic": {
                "colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
                "background": "white",
                "font_family": "Times New Roman",
                "font_size": 42
            }
        }

    async def create_chart(
        self,
        data: dict,
        chart_type: str,
        style: str = "modern",
        duration: float = 5.0
    ) -> VideoClip:
        """
        生成数据图表动画

        Args:
            data: {
                "labels": ["2020", "2021", "2022", "2023"],
                "values": [100, 150, 200, 250],
                "title": "增长趋势"
            }
            chart_type: "bar", "line", "pie", "number"
            style: "modern", "classic"
            duration: 时长（秒）

        Returns:
            VideoClip 对象
        """

        if chart_type == "bar":
            return await self._create_bar_chart(data, style, duration)
        elif chart_type == "line":
            return await self._create_line_chart(data, style, duration)
        elif chart_type == "pie":
            return await self._create_pie_chart(data, style, duration)
        elif chart_type == "number":
            return await self._create_number_animation(data, style, duration)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

    async def _create_bar_chart(
        self,
        data: dict,
        style: str,
        duration: float
    ) -> VideoClip:
        """创建柱状图动画"""

        style_config = self.style_presets[style]

        # 创建图表
        fig, ax = plt.subplots(figsize=(16, 9), facecolor=style_config["background"])
        ax.set_facecolor(style_config["background"])

        labels = data["labels"]
        values = data["values"]

        bars = ax.bar(range(len(labels)), values, color=style_config["colors"])

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=style_config["font_size"])
        ax.set_title(data.get("title", ""), fontsize=style_config["font_size"] * 1.5, color="white")

        # 设置颜色
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("white")

        # 保存图表
        chart_path = f"data/temp/chart_{uuid.uuid4()}.png"
        Path(chart_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(chart_path, bbox_inches="tight", dpi=100)
        plt.close()

        # 创建动画
        clip = ImageClip(chart_path).set_duration(duration)

        return clip

    async def _create_line_chart(self, data: dict, style: str, duration: float) -> VideoClip:
        """创建折线图动画"""
        # 类似柱状图的实现
        pass

    async def _create_pie_chart(self, data: dict, style: str, duration: float) -> VideoClip:
        """创建饼图动画"""
        # 实现饼图
        pass

    async def _create_number_animation(self, data: dict, style: str, duration: float) -> VideoClip:
        """创建数字动画"""
        # 实现数字增长动画
        pass

    async def extract_data_from_script(
        self,
        script: str
    ) -> List[dict]:
        """
        从脚本中提取数据和关键数字

        Returns:
            [
                {
                    "type": "bar",
                    "data": {"labels": [...], "values": [...], "title": "..."},
                    "position": 30.5,  # 在视频中的位置（秒）
                    "duration": 5.0
                }
            ]
        """

        from app.services.llm import llm_manager

        llm = llm_manager.get_provider("claude")

        prompt = f"""
        从以下脚本中提取数据和关键数字，用于数据可视化。

        脚本内容:
        {script}

        请识别：
        1. 百分比数据（例如：增长了15%）
        2. 对比数据（例如：从100万增长到200万）
        3. 时间序列数据（例如：2020年100，2021年150）
        4. 关键统计数字

        对每个提取的数据，返回：
        - type: 图表类型 (bar, line, pie, number)
        - labels: 标签列表
        - values: 数值列表
        - title: 图表标题
        - position: 在脚本中的大致位置（秒）

        以 JSON 数组格式返回。
        """

        result = await llm.generate(prompt, temperature=0.3)

        # 解析 JSON
        import json
        data_list = json.loads(result)

        return data_list
```

#### 2.2 动态字幕特效

```python
# backend/app/services/effects/dynamic_subtitle.py

from typing import List, Dict, Any
from moviepy.editor import VideoClip, TextClip, CompositeVideoClip
from moviepy.video.fx.all import fadein, fadeout

class DynamicSubtitleEffect:
    """动态字幕特效"""

    def __init__(self):
        self.styles = {
            "modern": {
                "font": "Arial-Unicode-MS",
                "fontsize": 60,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 2
            },
            "cinematic": {
                "font": "Arial-Unicode-MS",
                "fontsize": 70,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 3,
                "bg_color": "rgba(0,0,0,0.5)"
            }
        }

    async def create_highlight_subtitle(
        self,
        text: str,
        highlight_words: List[str],
        style: str = "modern",
        duration: float = 3.0
    ) -> VideoClip:
        """
        创建高亮字幕

        Args:
            text: 字幕文本
            highlight_words: 需要高亮的关键词
            style: 样式
            duration: 时长
        """

        style_config = self.styles[style]

        # 创建基础字幕
        base_clip = TextClip(
            text,
            font=style_config["font"],
            fontsize=style_config["fontsize"],
            color=style_config["color"],
            stroke_color=style_config["stroke_color"],
            stroke_width=style_config["stroke_width"]
        ).set_duration(duration)

        # 为高亮词创建单独的片段
        highlight_clips = []
        for word in highlight_words:
            if word in text:
                # 高亮版本（不同颜色或大小）
                highlight_clip = TextClip(
                    word,
                    font=style_config["font"],
                    fontsize=style_config["fontsize"] * 1.2,
                    color="#FFD700",  # 金色
                    stroke_color=style_config["stroke_color"],
                    stroke_width=style_config["stroke_width"]
                ).set_duration(duration)

                highlight_clips.append(highlight_clip)

        return base_clip

    async def create_typing_effect(
        self,
        text: str,
        duration: float
    ) -> VideoClip:
        """打字机效果"""

        # 创建逐字显示的动画
        clips = []
        chars = len(text)
        char_duration = duration / chars

        for i in range(chars):
            partial_text = text[:i+1]
            clip = TextClip(
                partial_text,
                font="Arial-Unicode-MS",
                fontsize=60,
                color="white"
            ).set_duration(char_duration).set_start(i * char_duration)

            clips.append(clip)

        return CompositeVideoClip(clips)

    async def create_emphasis_animation(
        self,
        text: str,
        emphasis_level: str = "medium"
    ) -> VideoClip:
        """强调动画效果"""

        # 根据强调级别设置动画参数
        if emphasis_level == "light":
            scale_factor = 1.1
            duration = 0.5
        elif emphasis_level == "medium":
            scale_factor = 1.3
            duration = 0.8
        else:  # strong
            scale_factor = 1.5
            duration = 1.0

        # 创建缩放动画
        clip = TextClip(
            text,
            font="Arial-Unicode-MS",
            fontsize=60,
            color="white"
        )

        # 应用缩放效果
        def scale_effect(get_frame, t):
            frame = get_frame(t)
            progress = t / clip.duration
            scale = 1 + (scale_factor - 1) * progress
            # 应用缩放（这里需要实际的图像处理）
            return frame

        return clip.fl(scale_effect)
```

#### 2.3 集成到视频合成

```python
# backend/app/services/video_synthesizer.py 增强

from app.services.effects.data_visualization import DataVisualizationEffect
from app.services.effects.dynamic_subtitle import DynamicSubtitleEffect

class VideoSynthesizer:

    def __init__(self):
        self.video_processor = VideoProcessor()
        self.data_viz = DataVisualizationEffect()
        self.subtitle_effects = DynamicSubtitleEffect()

    def synthesize_video(
        self,
        project_id: int,
        enable_effects: bool = True,
        **kwargs
    ) -> str:
        """合成视频（支持高级特效）"""

        # 现有流程...
        base_clips = self._load_materials(project_id)
        audio_clip = self._load_audio(project_id)
        script = self._load_script(project_id)

        # 新增：高级特效
        if enable_effects:
            # 1. 提取数据
            data_visualizations = await self.data_viz.extract_data_from_script(
                script.full_script
            )

            # 2. 生成数据可视化片段
            chart_clips = []
            for viz_data in data_visualizations:
                chart_clip = await self.data_viz.create_chart(
                    data=viz_data["data"],
                    chart_type=viz_data["type"],
                    duration=viz_data.get("duration", 5.0)
                )
                chart_clip = chart_clip.set_start(viz_data["position"])
                chart_clips.append(chart_clip)

            # 3. 创建动态字幕
            subtitle_clips = []
            for segment in script.segments:
                # 提取关键词
                keywords = self._extract_keywords(segment["text"])

                subtitle_clip = await self.subtitle_effects.create_highlight_subtitle(
                    text=segment["text"],
                    highlight_words=keywords,
                    duration=segment["duration"]
                )
                subtitle_clip = subtitle_clip.set_start(segment["start_time"])
                subtitle_clips.append(subtitle_clip)

            # 4. 合成所有内容
            final_video = CompositeVideoClip([
                *base_clips,
                *chart_clips,
                *subtitle_clips
            ])
        else:
            final_video = self._merge_clips(base_clips)

        # 添加音频
        if audio_clip:
            final_video = final_video.set_audio(audio_clip)

        # 导出
        output_path = self._get_output_path(project_id, kwargs.get("platform", "horizontal"))
        final_video.write_videofile(output_path, fps=30, codec="libx264")

        return output_path

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单实现：提取数字、百分比、专有名词
        import re

        keywords = []

        # 提取数字
        keywords.extend(re.findall(r'\d+(?:\.\d+)?%?', text))

        # 提取关键短语（这里可以用 NLP）
        # TODO: 使用更复杂的关键词提取

        return keywords
```

---

### 3. 批量处理服务

#### 3.1 智能调度器

```python
# backend/app/services/scheduler/smart_scheduler.py

import psutil
import redis
from typing import List, Dict, Any
import uuid
from datetime import datetime
from app.config import settings

class SmartScheduler:
    """智能任务调度器"""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0
        )
        self.max_concurrent = 5
        self.min_concurrent = 1
        self.monitor_interval = 300  # 5分钟

    async def get_optimal_concurrency(self) -> int:
        """根据系统资源计算最优并发数"""

        # 监控指标
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        queue_length = self._get_queue_length()
        active_tasks = self._get_active_tasks()

        # 智能调整策略
        if cpu_usage > 80 or memory_usage > 85:
            # 高负载：减少并发
            optimal = self.min_concurrent
        elif cpu_usage < 50 and memory_usage < 70:
            # 低负载：增加并发
            optimal = self.max_concurrent
        else:
            # 中等负载：适度并发
            optimal = max(2, min(4, queue_length // 2))

        # 考虑队列长度
        if queue_length > 10:
            optimal = min(optimal + 1, self.max_concurrent)
        elif queue_length < 3:
            optimal = max(optimal - 1, self.min_concurrent)

        return optimal

    async def schedule_batch(
        self,
        project_ids: List[int],
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """调度批量任务"""

        optimal_concurrency = await self.get_optimal_concurrency()

        batch_id = str(uuid.uuid4())

        # 创建批量任务记录
        batch_job = {
            "id": batch_id,
            "project_ids": project_ids,
            "total_projects": len(project_ids),
            "completed_projects": 0,
            "failed_projects": 0,
            "concurrency": optimal_concurrency,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "priority": priority
        }

        # 存储到 Redis
        self.redis_client.hset(
            f"batch:{batch_id}",
            mapping={k: str(v) for k, v in batch_job.items()}
        )

        # 提交任务到 Celery
        from app.tasks.video_tasks import process_video_task

        priority_value = self._get_priority_value(priority)

        for i, project_id in enumerate(project_ids):
            # 添加延迟以控制并发
            delay = (i // optimal_concurrency) * 60  # 每批延迟60秒

            task = process_video_task.apply_async(
                args=[project_id, batch_id],
                priority=priority_value,
                countdown=delay
            )

            # 记录任务 ID
            self.redis_client.lpush(f"batch:{batch_id}:tasks", task.id)

        return batch_job

    def _get_queue_length(self) -> int:
        """获取队列长度"""
        from app.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect()
        active = inspector.active()
        reserved = inspector.reserved()

        total_active = sum(len(tasks) for tasks in active.values()) if active else 0
        total_reserved = sum(len(tasks) for tasks in reserved.values()) if reserved else 0

        return total_active + total_reserved

    def _get_active_tasks(self) -> int:
        """获取活跃任务数"""
        from app.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect()
        active = inspector.active()

        return sum(len(tasks) for tasks in active.values()) if active else 0

    def _get_priority_value(self, priority: str) -> int:
        """获取 Celery 优先级值"""
        priority_map = {
            "high": 9,
            "normal": 5,
            "low": 1
        }
        return priority_map.get(priority, 5)

    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """获取批量任务状态"""

        batch_data = self.redis_client.hgetall(f"batch:{batch_id}")

        if not batch_data:
            raise ValueError(f"Batch {batch_id} not found")

        # 解析数据
        batch = {k.decode(): v.decode() for k, v in batch_data.items()}

        # 计算进度
        completed = int(batch.get("completed_projects", 0))
        failed = int(batch.get("failed_projects", 0))
        total = int(batch.get("total_projects", 0))

        progress = ((completed + failed) / total * 100) if total > 0 else 0

        return {
            **batch,
            "progress": progress,
            "success_rate": (completed / total * 100) if total > 0 else 0
        }
```

#### 3.2 批量任务模型

```python
# backend/app/models/batch_job.py

from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from app.database import Base

class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id = Column(String(36), primary_key=True)
    project_ids = Column(JSON)  # [1, 2, 3, ...]
    task_ids = Column(JSON)  # ["task-uuid-1", "task-uuid-2", ...]
    concurrency = Column(Integer, default=3)
    status = Column(String(20))  # "queued", "running", "completed", "failed"
    priority = Column(String(10), default="normal")

    # 统计信息
    total_projects = Column(Integer)
    completed_projects = Column(Integer, default=0)
    failed_projects = Column(Integer, default=0)

    # 时间信息
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 错误信息
    error_messages = Column(JSON)  # [{project_id: 1, error: "..."}]
```

#### 3.3 批量处理 API

```python
# backend/app/api/batch.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.services.scheduler.smart_scheduler import SmartScheduler
from app.models.batch_job import BatchJob
from pydantic import BaseModel

router = APIRouter()


class BatchCreateRequest(BaseModel):
    project_ids: List[int]
    priority: str = "normal"  # "high", "normal", "low"


@router.post("/create")
async def create_batch(
    request: BatchCreateRequest,
    db: Session = Depends(get_db)
):
    """创建批量处理任务"""

    scheduler = SmartScheduler()
    batch_data = await scheduler.schedule_batch(
        request.project_ids,
        request.priority
    )

    # 创建数据库记录
    batch_job = BatchJob(
        id=batch_data["id"],
        project_ids=request.project_ids,
        total_projects=len(request.project_ids),
        concurrency=batch_data["concurrency"],
        status="queued",
        priority=request.priority
    )

    db.add(batch_job)
    db.commit()
    db.refresh(batch_job)

    return {
        "batch_id": batch_job.id,
        "total_projects": batch_job.total_projects,
        "concurrency": batch_job.concurrency,
        "status": batch_job.status,
        "message": "Batch job created successfully"
    }


@router.get("/status/{batch_id}")
async def get_batch_status(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """查询批量任务状态"""

    batch = db.query(BatchJob).filter(BatchJob.id == batch_id).first()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch job not found")

    # 计算进度
    total = batch.total_projects
    completed = batch.completed_projects
    failed = batch.failed_projects

    progress = ((completed + failed) / total * 100) if total > 0 else 0
    success_rate = (completed / total * 100) if total > 0 else 0

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "progress": f"{progress:.1f}%",
        "completed": completed,
        "failed": failed,
        "total": total,
        "success_rate": f"{success_rate:.1f}%",
        "concurrency": batch.concurrency,
        "created_at": batch.created_at,
        "started_at": batch.started_at,
        "completed_at": batch.completed_at
    }


@router.get("/list")
async def list_batches(
    status: str = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """列出批量任务"""

    query = db.query(BatchJob)

    if status:
        query = query.filter(BatchJob.status == status)

    batches = query.order_by(BatchJob.created_at.desc()).limit(limit).all()

    return {
        "batches": [
            {
                "batch_id": batch.id,
                "status": batch.status,
                "total": batch.total_projects,
                "completed": batch.completed_projects,
                "created_at": batch.created_at
            }
            for batch in batches
        ]
    }


@router.post("/cancel/{batch_id}")
async def cancel_batch(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """取消批量任务"""

    batch = db.query(BatchJob).filter(BatchJob.id == batch_id).first()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch job not found")

    if batch.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel completed batch")

    # 撤销 Celery 任务
    from app.tasks.celery_app import celery_app

    if batch.task_ids:
        for task_id in batch.task_ids:
            celery_app.control.revoke(task_id, terminate=True)

    # 更新状态
    batch.status = "cancelled"
    db.commit()

    return {
        "batch_id": batch_id,
        "status": "cancelled",
        "message": "Batch job cancelled successfully"
    }
```

---

### 4. 数据统计服务

#### 4.1 指标收集器

```python
# backend/app/services/analytics/metrics_collector.py

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.models.project import Project
from app.models.material import Material
from app.models.quality_report import QualityReport

class MetricsCollector:
    """指标收集器"""

    def __init__(self, db: Session):
        self.db = db

    async def collect_project_metrics(
        self,
        project_id: int
    ) -> Dict[str, Any]:
        """收集单个项目的指标"""

        project = self.db.query(Project).filter(Project.id == project_id).first()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # 时间指标
        total_duration = None
        if project.created_at and hasattr(project, 'completed_at') and project.completed_at:
            total_duration = (project.completed_at - project.created_at).total_seconds()

        # 成本指标（从项目 metadata 中提取）
        metadata = project.project_metadata or {}

        return {
            "project_id": project_id,
            "timing": {
                "total_duration": total_duration,
                "script_generation_time": metadata.get("script_generation_time"),
                "material_collection_time": metadata.get("material_collection_time"),
                "video_synthesis_time": metadata.get("video_synthesis_time")
            },
            "costs": {
                "llm_cost": metadata.get("llm_cost", 0.0),
                "tts_cost": metadata.get("tts_cost", 0.0),
                "image_cost": metadata.get("image_cost", 0.0),
                "music_cost": metadata.get("music_cost", 0.0),
                "total_cost": metadata.get("total_cost", 0.0)
            },
            "quality": {
                "score": metadata.get("quality_score"),
                "grade": metadata.get("quality_grade")
            },
            "resources": {
                "materials_used": len(project.materials) if project.materials else 0,
                "video_duration": metadata.get("video_duration"),
                "file_size": metadata.get("file_size")
            }
        }

    async def collect_system_metrics(
        self,
        time_range: str = "7d"
    ) -> Dict[str, Any]:
        """收集系统级指标"""

        # 计算时间范围
        now = datetime.now()
        if time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = None

        # 基础查询
        query = self.db.query(Project)
        if start_time:
            query = query.filter(Project.created_at >= start_time)

        # 生产力指标
        total_projects = query.count()
        completed_projects = query.filter(Project.current_step == "completed").count()
        success_rate = (completed_projects / total_projects * 100) if total_projects > 0 else 0

        # 效率指标
        completed_with_time = query.filter(
            Project.current_step == "completed",
            Project.created_at.isnot(None)
        ).all()

        avg_production_time = 0
        if completed_with_time:
            total_times = []
            for p in completed_with_time:
                if hasattr(p, 'completed_at') and p.completed_at:
                    duration = (p.completed_at - p.created_at).total_seconds()
                    total_times.append(duration)

            avg_production_time = sum(total_times) / len(total_times) if total_times else 0

        # 成本指标
        total_cost = 0
        for p in completed_with_time:
            metadata = p.project_metadata or {}
            total_cost += metadata.get("total_cost", 0.0)

        avg_cost = total_cost / completed_projects if completed_projects > 0 else 0

        return {
            "time_range": time_range,
            "productivity": {
                "total_projects": total_projects,
                "completed_projects": completed_projects,
                "success_rate": round(success_rate, 1)
            },
            "efficiency": {
                "avg_production_time": round(avg_production_time, 1),
                "avg_production_time_minutes": round(avg_production_time / 60, 1)
            },
            "costs": {
                "total_cost": round(total_cost, 2),
                "avg_cost_per_project": round(avg_cost, 2)
            }
        }

    async def get_trend_data(
        self,
        metric: str,
        time_range: str = "30d"
    ) -> Dict[str, Any]:
        """获取趋势数据"""

        # 计算时间范围
        now = datetime.now()
        if time_range == "7d":
            start_time = now - timedelta(days=7)
            interval = "day"
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
            interval = "day"
        else:
            start_time = now - timedelta(days=90)
            interval = "week"

        # 根据指标类型查询数据
        if metric == "production_count":
            # 每日/每周生产数量
            projects = self.db.query(Project).filter(
                Project.created_at >= start_time
            ).all()

            # 按日期分组
            date_counts = {}
            for p in projects:
                date_key = p.created_at.strftime("%Y-%m-%d")
                date_counts[date_key] = date_counts.get(date_key, 0) + 1

            return {
                "labels": sorted(date_counts.keys()),
                "data": [date_counts[k] for k in sorted(date_counts.keys())]
            }

        elif metric == "cost":
            # 成本趋势
            pass

        elif metric == "success_rate":
            # 成功率趋势
            pass

        return {}
```

#### 4.2 数据模型

```python
# backend/app/models/analytics.py

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base

class ProjectMetrics(Base):
    __tablename__ = "project_metrics"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, index=True)

    # 时间指标（秒）
    total_duration = Column(Float)
    script_generation_time = Column(Float)
    material_collection_time = Column(Float)
    video_synthesis_time = Column(Float)

    # 成本指标（美元）
    llm_cost = Column(Float, default=0.0)
    tts_cost = Column(Float, default=0.0)
    image_cost = Column(Float, default=0.0)
    music_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    # 质量指标
    quality_score = Column(Float)
    quality_grade = Column(String(1))

    # 资源指标
    materials_count = Column(Integer)
    video_duration = Column(Float)  # 秒
    file_size = Column(Integer)  # 字节

    created_at = Column(DateTime, server_default=func.now())


class SystemMetrics(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True)

    # 生产力指标
    total_projects = Column(Integer)
    completed_projects = Column(Integer)
    success_rate = Column(Float)

    # 效率指标
    avg_production_time = Column(Float)
    avg_script_time = Column(Float)
    avg_synthesis_time = Column(Float)

    # 成本指标
    total_api_cost = Column(Float)
    avg_cost_per_project = Column(Float)

    # 资源使用
    storage_used = Column(Integer)  # 字节
    queue_length = Column(Integer)

    recorded_at = Column(DateTime, server_default=func.now())
```

#### 4.3 分析仪表板 API

```python
# backend/app/api/analytics.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.analytics.metrics_collector import MetricsCollector
from typing import Optional

router = APIRouter()


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    time_range: str = Query("7d", regex="^(24h|7d|30d|all)$"),
    db: Session = Depends(get_db)
):
    """获取仪表板概览数据"""

    collector = MetricsCollector(db)
    metrics = await collector.collect_system_metrics(time_range)

    return {
        "summary": {
            "total_projects": metrics["productivity"]["total_projects"],
            "completed_projects": metrics["productivity"]["completed_projects"],
            "success_rate": f"{metrics['productivity']['success_rate']:.1f}%",
            "avg_production_time": f"{metrics['efficiency']['avg_production_time_minutes']:.1f}分钟"
        },
        "costs": {
            "total_cost": f"${metrics['costs']['total_cost']:.2f}",
            "avg_cost_per_project": f"${metrics['costs']['avg_cost_per_project']:.2f}"
        },
        "efficiency": {
            "avg_production_time": f"{metrics['efficiency']['avg_production_time_minutes']:.1f}分钟"
        }
    }


@router.get("/dashboard/trends")
async def get_trend_data(
    metric: str = Query(..., regex="^(production_count|cost|success_rate|quality)$"),
    time_range: str = Query("30d", regex="^(7d|30d|90d)$"),
    db: Session = Depends(get_db)
):
    """获取趋势数据（用于图表）"""

    collector = MetricsCollector(db)
    trend_data = await collector.get_trend_data(metric, time_range)

    return trend_data


@router.get("/dashboard/comparison")
async def get_comparison_data(
    dimension: str = Query(..., regex="^(provider|content_type|platform)$"),
    db: Session = Depends(get_db)
):
    """获取对比数据"""

    collector = MetricsCollector(db)

    # 根据维度返回对比数据
    if dimension == "provider":
        # 按 LLM Provider 对比
        return {
            "dimension": "provider",
            "data": {
                "claude": {
                    "avg_cost": 0.15,
                    "avg_quality": 85,
                    "avg_time": 120
                },
                "openai": {
                    "avg_cost": 0.12,
                    "avg_quality": 82,
                    "avg_time": 115
                },
                "glm": {
                    "avg_cost": 0.05,
                    "avg_quality": 78,
                    "avg_time": 130
                }
            }
        }

    return {}


@router.get("/projects/{project_id}/metrics")
async def get_project_metrics(
    project_id: int,
    db: Session = Depends(get_db)
):
    """获取单个项目的详细指标"""

    collector = MetricsCollector(db)
    metrics = await collector.collect_project_metrics(project_id)

    return metrics


@router.get("/dashboard/bottleneck")
async def identify_bottleneck(
    db: Session = Depends(get_db)
):
    """识别生产瓶颈"""

    collector = MetricsCollector(db)
    metrics = await collector.collect_system_metrics("7d")

    # 分析各环节耗时
    avg_script_time = metrics.get("avg_script_time", 0)
    avg_synthesis_time = metrics.get("avg_synthesis_time", 0)

    # 识别瓶颈
    if avg_script_time > avg_synthesis_time * 2:
        bottleneck = "script_generation"
        recommendation = "建议优化 LLM 提示词或切换到更快的模型"
    elif avg_synthesis_time > avg_script_time * 2:
        bottleneck = "video_synthesis"
        recommendation = "建议增加视频合成并发数或优化视频处理流程"
    else:
        bottleneck = "balanced"
        recommendation = "各环节耗时均衡，整体流程良好"

    return {
        "bottleneck": bottleneck,
        "recommendation": recommendation,
        "metrics": {
            "avg_script_time": avg_script_time,
            "avg_synthesis_time": avg_synthesis_time
        }
    }
```

---

## 配置管理

### 新增配置项

```python
# backend/app/config.py 新增

class Settings(BaseSettings):
    # ... 现有配置 ...

    # DALL-E 3 (复用 OpenAI API Key)
    # OPENAI_API_KEY 已存在

    # Midjourney
    MIDJOURNEY_API_KEY: Optional[str] = None
    MIDJOURNEY_ENDPOINT: Optional[str] = None

    # Suno AI
    SUNO_API_KEY: Optional[str] = None
    SUNO_ENDPOINT: Optional[str] = None

    # AI 生成配置
    DEFAULT_IMAGE_PROVIDER: str = "dalle"  # dalle 或 midjourney
    ENABLE_AI_MUSIC: bool = True

    # 批量处理配置
    MAX_CONCURRENT_PROJECTS: int = 5
    MIN_CONCURRENT_PROJECTS: int = 1
    BATCH_MONITOR_INTERVAL: int = 300  # 秒
```

---

## 数据库迁移

### 新增表

```sql
-- 批量任务表
CREATE TABLE batch_jobs (
    id VARCHAR(36) PRIMARY KEY,
    project_ids JSON,
    task_ids JSON,
    concurrency INTEGER DEFAULT 3,
    status VARCHAR(20),
    priority VARCHAR(10) DEFAULT 'normal',
    total_projects INTEGER,
    completed_projects INTEGER DEFAULT 0,
    failed_projects INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_messages JSON
);

-- 项目指标表
CREATE TABLE project_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    total_duration FLOAT,
    script_generation_time FLOAT,
    material_collection_time FLOAT,
    video_synthesis_time FLOAT,
    llm_cost FLOAT DEFAULT 0.0,
    tts_cost FLOAT DEFAULT 0.0,
    image_cost FLOAT DEFAULT 0.0,
    music_cost FLOAT DEFAULT 0.0,
    total_cost FLOAT DEFAULT 0.0,
    quality_score FLOAT,
    quality_grade VARCHAR(1),
    materials_count INTEGER,
    video_duration FLOAT,
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- 系统指标表
CREATE TABLE system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_projects INTEGER,
    completed_projects INTEGER,
    success_rate FLOAT,
    avg_production_time FLOAT,
    avg_script_time FLOAT,
    avg_synthesis_time FLOAT,
    total_api_cost FLOAT,
    avg_cost_per_project FLOAT,
    storage_used INTEGER,
    queue_length INTEGER,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API 端点汇总

### AI 生成相关

- `POST /api/ai-generation/image` - 生成图像
- `POST /api/ai-generation/music` - 生成音乐
- `GET /api/ai-generation/providers` - 列出可用 provider

### 批量处理相关

- `POST /api/batch/create` - 创建批量任务
- `GET /api/batch/status/{batch_id}` - 查询批量任务状态
- `GET /api/batch/list` - 列出批量任务
- `POST /api/batch/cancel/{batch_id}` - 取消批量任务

### 数据统计相关

- `GET /api/analytics/dashboard/overview` - 仪表板概览
- `GET /api/analytics/dashboard/trends` - 趋势数据
- `GET /api/analytics/dashboard/comparison` - 对比数据
- `GET /api/analytics/projects/{project_id}/metrics` - 项目指标
- `GET /api/analytics/dashboard/bottleneck` - 瓶颈识别

---

## 验收标准

### AI 生成素材

- ✅ DALL-E 3 集成完成，支持多种风格
- ✅ Midjourney 集成完成，作为高级选项
- ✅ AI 生成素材成功率 ≥ 80%
- ✅ 生成图像质量满足视频制作需求

### AI 生成音乐

- ✅ Suno AI 集成完成
- ✅ 自动分析脚本情绪准确率 ≥ 85%
- ✅ 音乐与视频情绪匹配度 ≥ 85%
- ✅ 支持自定义时长

### 高级视频特效

- ✅ 支持 4 种以上图表类型
- ✅ 数据提取准确率 ≥ 90%
- ✅ 动态字幕支持高亮和动画效果
- ✅ 特效不影响视频合成性能

### 批量处理

- ✅ 支持创建批量任务
- ✅ 智能调度自动调整并发数
- ✅ 支持同时处理 5 个项目
- ✅ 提供实时进度反馈

### 数据统计

- ✅ 仪表板展示所有关键指标
- ✅ 支持多时间范围查看
- ✅ 趋势图表可视化
- ✅ 瓶颈识别准确

---

## 风险与限制

### 技术风险

- **AI API 稳定性**: DALL-E、Midjourney、Suno AI 可能出现服务中断
  - 缓解措施：保留现有素材库作为备用源

- **音乐生成质量**: AI 生成的音乐可能不符合预期
  - 缓解措施：提供重新生成选项，允许手动调整

- **数据可视化准确性**: 自动提取数据可能出错
  - 缓解措施：提供手动编辑选项

### 成本控制

- **AI 生成成本**: DALL-E、Midjourney、Suno AI 调用成本较高
  - 控制措施：缓存生成结果，复用相似素材

- **存储成本**: 大量 AI 生成内容占用存储空间
  - 控制措施：定期清理未使用的生成内容

### 性能影响

- **批量处理负载**: 多项目并发可能占用大量系统资源
  - 缓解措施：智能调度根据资源情况调整并发数

- **特效渲染时间**: 复杂特效增加视频合成时间
  - 缓解措施：提供特效开关，允许跳过特效

---

## 后续优化方向

- **AI 生成优化**: 支持更多 AI 模型，提升生成质量
- **特效库扩展**: 增加更多预设模板和自定义选项
- **性能优化**: 优化并发处理和资源调度算法
- **用户反馈**: 收集用户使用数据，持续改进功能
