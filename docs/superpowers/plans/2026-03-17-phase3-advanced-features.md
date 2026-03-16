# Phase 3 高级特性实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现AI生成服务、高级视频特效、批量处理和数据统计四大高级特性模块

**Architecture:** 采用渐进式集成方法，扩展现有Provider模式。AI生成服务遵循BaseLLMProvider和BaseTTSProvider的Provider抽象模式；高级特效集成到视频合成流程；批量处理基于Celery任务队列；数据统计通过独立的Collector和Dashboard API实现

**Tech Stack:** OpenAI API (DALL-E 3), matplotlib/plotly (数据可视化), psutil (系统监控), FastAPI, Celery, Redis, SQLAlchemy

---

## File Structure

**AI Generation Service:**
- Create: `backend/app/services/ai_generation/__init__.py` - AIGenerationProvider管理器
- Create: `backend/app/services/ai_generation/base.py` - AIGenerationProvider抽象基类
- Create: `backend/app/services/ai_generation/dalle_provider.py` - DALL-E 3实现
- Create: `backend/app/services/ai_generation/midjourney_provider.py` - Midjourney实现
- Create: `backend/app/services/ai_generation/suno_provider.py` - Suno AI实现
- Create: `backend/app/api/ai_generation.py` - AI生成API端点
- Create: `backend/tests/test_ai_generation.py` - AI生成测试

**Advanced Video Effects:**
- Create: `backend/app/services/effects/__init__.py` - 特效模块初始化
- Create: `backend/app/services/effects/data_visualization.py` - 数据可视化特效
- Create: `backend/app/services/effects/dynamic_subtitle.py` - 动态字幕特效
- Create: `backend/tests/test_advanced_effects.py` - 高级特效测试

**Batch Processing:**
- Create: `backend/app/services/batch/__init__.py` - 批量处理模块初始化
- Create: `backend/app/services/batch/scheduler.py` - 智能调度器
- Create: `backend/app/tasks/batch_tasks.py` - 批量处理Celery任务
- Create: `backend/app/api/batch.py` - 批量处理API端点
- Create: `backend/app/models/batch.py` - BatchJob模型
- Create: `backend/tests/test_batch.py` - 批量处理测试

**Analytics:**
- Create: `backend/app/services/analytics/__init__.py` - 分析模块初始化
- Create: `backend/app/services/analytics/collector.py` - 指标收集器
- Create: `backend/app/services/analytics/dashboard.py` - Dashboard API
- Create: `backend/app/api/analytics.py` - 分析API端点
- Create: `backend/app/models/analytics.py` - ProjectMetric和SystemMetric模型
- Create: `backend/tests/test_analytics.py` - 分析测试

**Configuration Updates:**
- Modify: `backend/app/config.py` - 添加DALL-E、Midjourney、Suno API配置

**Database:**
- Modify: `backend/app/models/__init__.py` - 导入新模型

---

## Chunk 1: AI Generation Service (基础架构和DALL-E 3)

### Task 1: 创建AIGenerationProvider抽象基类

**Files:**
- Create: `backend/app/services/ai_generation/base.py`
- Create: `backend/tests/test_ai_generation.py`

- [ ] **Step 1: Write the failing test for base class**

```python
# backend/tests/test_ai_generation.py
import pytest
from app.services.ai_generation.base import BaseAIGenerationProvider


class TestBaseAIGenerationProvider:
    """测试AI生成Provider抽象基类"""

    def test_base_provider_is_abstract(self):
        """基类不能直接实例化"""
        with pytest.raises(TypeError):
            BaseAIGenerationProvider()

    def test_base_provider_requires_generate_image_method(self):
        """子类必须实现generate_image方法"""
        class IncompleteProvider(BaseAIGenerationProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_base_provider_requires_all_abstract_methods(self):
        """子类必须实现所有抽象方法"""
        class IncompleteProvider(BaseAIGenerationProvider):
            async def generate_image(self, prompt, output_path, **kwargs):
                pass

        with pytest.raises(TypeError):
            IncompleteProvider()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ai_generation.py::TestBaseAIGenerationProvider -v`
Expected: FAIL with "cannot instantiate abstract class"

- [ ] **Step 3: Implement BaseAIGenerationProvider class**

```python
# backend/app/services/ai_generation/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


class BaseAIGenerationProvider(ABC):
    """AI生成Provider抽象基类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图像
        Args:
            prompt: 生成提示词
            output_path: 输出文件路径
            size: 图像尺寸 (e.g., "1024x1024", "1792x1024")
            quality: 图像质量 ("standard" or "hd")
        Returns:
            包含图像信息的字典 {"path": str, "size": tuple, "format": str}
        """
        pass

    @abstractmethod
    async def generate_music(
        self,
        prompt: str,
        output_path: str,
        duration: int = 30,
        style: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成音乐
        Args:
            prompt: 生成提示词
            output_path: 输出文件路径
            duration: 音乐时长（秒）
            style: 音乐风格
        Returns:
            包含音频信息的字典 {"path": str, "duration": float, "format": str}
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass

    @property
    @abstractmethod
    def supported_features(self) -> List[str]:
        """支持的功能列表 ["image", "music"]"""
        pass

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ai_generation.py::TestBaseAIGenerationProvider -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai_generation/base.py backend/tests/test_ai_generation.py
git commit -m "feat(ai-gen): add BaseAIGenerationProvider abstract class

- Define abstract methods for image and music generation
- Follow existing Provider pattern from LLM/TTS
- Add validation method for configuration

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: 实现DALLEProvider

**Files:**
- Create: `backend/app/services/ai_generation/dalle_provider.py`
- Modify: `backend/tests/test_ai_generation.py`

- [ ] **Step 1: Write the failing test for DALL-E provider**

```python
# Add to backend/tests/test_ai_generation.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.ai_generation.dalle_provider import DALLEProvider


class TestDALLEProvider:
    """测试DALL-E Provider"""

    @pytest.mark.asyncio
    async def test_dalle_generate_image_success(self, tmp_path):
        """测试DALL-E生成图像成功"""
        with patch('openai.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            # Mock the image generation response
            mock_response = Mock()
            mock_response.data = [Mock(url="https://example.com/image.png")]
            mock_instance.images.generate = AsyncMock(return_value=mock_response)

            # Mock the image download
            with patch('httpx.AsyncClient.get') as mock_get:
                mock_response_get = AsyncMock()
                mock_response_get.content = b"fake_image_data"
                mock_response_get.raise_for_status = Mock()
                mock_get.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response_get
                )

                provider = DALLEProvider(api_key="test_key")
                output_path = str(tmp_path / "test_image.png")
                result = await provider.generate_image(
                    "A beautiful sunset",
                    output_path
                )

                assert result["path"] == output_path
                assert result["format"] == "png"
                mock_instance.images.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_dalle_generate_image_with_custom_size(self, tmp_path):
        """测试自定义尺寸生成"""
        with patch('openai.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            mock_response = Mock()
            mock_response.data = [Mock(url="https://example.com/image.png")]
            mock_instance.images.generate = AsyncMock(return_value=mock_response)

            with patch('httpx.AsyncClient.get') as mock_get:
                mock_response_get = AsyncMock()
                mock_response_get.content = b"fake_image_data"
                mock_response_get.raise_for_status = Mock()
                mock_get.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response_get
                )

                provider = DALLEProvider(api_key="test_key")
                output_path = str(tmp_path / "test_image.png")
                await provider.generate_image(
                    "Test",
                    output_path,
                    size="1792x1024"
                )

                call_args = mock_instance.images.generate.call_args
                assert call_args.kwargs["size"] == "1792x1024"

    @pytest.mark.asyncio
    async def test_dalle_generate_image_api_error(self, tmp_path):
        """测试API错误处理"""
        with patch('openai.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.images.generate = AsyncMock(
                side_effect=Exception("API Error")
            )

            provider = DALLEProvider(api_key="test_key")

            with pytest.raises(RuntimeError, match="DALL-E API error"):
                await provider.generate_image("Test", str(tmp_path / "test.png"))

    def test_dalle_provider_name(self):
        """测试provider名称"""
        provider = DALLEProvider(api_key="test_key")
        assert provider.provider_name == "dalle"

    def test_dalle_supported_features(self):
        """测试支持的功能"""
        provider = DALLEProvider(api_key="test_key")
        assert "image" in provider.supported_features
        assert "music" not in provider.supported_features

    def test_dalle_available_models(self):
        """测试可用模型"""
        provider = DALLEProvider(api_key="test_key")
        assert "dall-e-3" in provider.available_models
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ai_generation.py::TestDALLEProvider -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

- [ ] **Step 3: Implement DALLEProvider class**

```python
# backend/app/services/ai_generation/dalle_provider.py
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import httpx
from openai import AsyncOpenAI

from .base import BaseAIGenerationProvider


class DALLEProvider(BaseAIGenerationProvider):
    """DALL-E 3图像生成Provider"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "dall-e-3",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用DALL-E生成图像
        """
        if not self.client:
            raise RuntimeError("OpenAI API key not configured")

        try:
            # 调用DALL-E API
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
                response_format="url"
            )

            image_url = response.data[0].url

            # 下载图像到本地
            async with httpx.AsyncClient() as client:
                img_response = await client.get(image_url)
                img_response.raise_for_status()

                # 确保输出目录存在
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                # 保存图像
                with open(output_path, "wb") as f:
                    f.write(img_response.content)

            return {
                "path": output_path,
                "size": tuple(map(int, size.split("x"))),
                "format": "png",
                "provider": self.provider_name
            }

        except Exception as e:
            raise RuntimeError(f"DALL-E API error: {e}")

    async def generate_music(
        self,
        prompt: str,
        output_path: str,
        duration: int = 30,
        style: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """DALL-E不支持音乐生成"""
        raise NotImplementedError("DALL-E does not support music generation")

    @property
    def provider_name(self) -> str:
        return "dalle"

    @property
    def supported_features(self) -> List[str]:
        return ["image"]

    @property
    def available_models(self) -> List[str]:
        return ["dall-e-3"]

    def validate_config(self) -> bool:
        return self.api_key is not None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ai_generation.py::TestDALLEProvider -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai_generation/dalle_provider.py backend/tests/test_ai_generation.py
git commit -m "feat(ai-gen): implement DALLEProvider for image generation

- Implement generate_image using OpenAI DALL-E 3 API
- Download generated images to local storage
- Support custom size and quality parameters
- Add comprehensive error handling

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: 创建AIGenerationProvider Manager

**Files:**
- Create: `backend/app/services/ai_generation/__init__.py`
- Modify: `backend/tests/test_ai_generation.py`

- [ ] **Step 1: Write the failing test for manager**

```python
# Add to backend/tests/test_ai_generation.py

from app.services.ai_generation import AIGenerationManager


class TestAIGenerationManager:
    """测试AI生成管理器"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = AIGenerationManager()
        assert manager.providers == {}

    def test_register_provider(self):
        """测试注册provider"""
        manager = AIGenerationManager()
        provider = DALLEProvider(api_key="test_key")
        manager.register_provider("dalle", provider)

        assert "dalle" in manager.providers
        assert manager.providers["dalle"] == provider

    def test_get_provider_success(self):
        """测试获取provider"""
        manager = AIGenerationManager()
        provider = DALLEProvider(api_key="test_key")
        manager.register_provider("dalle", provider)

        retrieved = manager.get_provider("dalle")
        assert retrieved == provider

    def test_get_provider_not_found(self):
        """测试获取不存在的provider"""
        manager = AIGenerationManager()

        with pytest.raises(ValueError, match="Provider 'unknown' not found"):
            manager.get_provider("unknown")

    @pytest.mark.asyncio
    async def test_generate_image_with_provider(self, tmp_path):
        """测试通过管理器生成图像"""
        manager = AIGenerationManager()

        with patch('openai.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            mock_response = Mock()
            mock_response.data = [Mock(url="https://example.com/image.png")]
            mock_instance.images.generate = AsyncMock(return_value=mock_response)

            with patch('httpx.AsyncClient.get') as mock_get:
                mock_response_get = AsyncMock()
                mock_response_get.content = b"fake_image_data"
                mock_response_get.raise_for_status = Mock()
                mock_get.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response_get
                )

                provider = DALLEProvider(api_key="test_key")
                manager.register_provider("dalle", provider)

                output_path = str(tmp_path / "test.png")
                result = await manager.generate_image(
                    "dalle",
                    "A sunset",
                    output_path
                )

                assert result["path"] == output_path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ai_generation.py::TestAIGenerationManager -v`
Expected: FAIL with "ImportError"

- [ ] **Step 3: Implement AIGenerationManager**

```python
# backend/app/services/ai_generation/__init__.py
from typing import Dict, Optional, Any
from .base import BaseAIGenerationProvider
from .dalle_provider import DALLEProvider


class AIGenerationManager:
    """AI生成Provider管理器"""

    def __init__(self):
        self.providers: Dict[str, BaseAIGenerationProvider] = {}

    def register_provider(self, name: str, provider: BaseAIGenerationProvider):
        """注册Provider"""
        self.providers[name] = provider

    def get_provider(self, name: str) -> BaseAIGenerationProvider:
        """获取Provider"""
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not found")
        return self.providers[name]

    async def generate_image(
        self,
        provider_name: str,
        prompt: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """生成图像"""
        provider = self.get_provider(provider_name)
        return await provider.generate_image(prompt, output_path, **kwargs)

    async def generate_music(
        self,
        provider_name: str,
        prompt: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """生成音乐"""
        provider = self.get_provider(provider_name)
        return await provider.generate_music(prompt, output_path, **kwargs)

    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """列出所有Provider及其功能"""
        return {
            name: {
                "provider": provider.provider_name,
                "features": provider.supported_features,
                "models": provider.available_models
            }
            for name, provider in self.providers.items()
        }


__all__ = [
    "BaseAIGenerationProvider",
    "DALLEProvider",
    "AIGenerationManager"
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ai_generation.py::TestAIGenerationManager -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai_generation/__init__.py backend/tests/test_ai_generation.py
git commit -m "feat(ai-gen): add AIGenerationManager for provider coordination

- Implement provider registration and retrieval
- Add convenience methods for image and music generation
- List all providers with their capabilities

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: 更新配置以支持AI生成API

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add AI generation configuration**

```python
# Modify backend/app/config.py
# Add after line 36 (after ELEVENLABS_API_KEY):

    # DALL-E
    DALLE_API_KEY: Optional[str] = None  # Defaults to OPENAI_API_KEY

    # Midjourney
    MIDJOURNEY_API_KEY: Optional[str] = None
    MIDJOURNEY_ENDPOINT: Optional[str] = None

    # Suno AI
    SUNO_API_KEY: Optional[str] = None
    SUNO_ENDPOINT: Optional[str] = None

    # AI Generation配置
    DEFAULT_AI_GENERATION_PROVIDER: str = "dalle"
```

- [ ] **Step 2: Commit configuration changes**

```bash
git add backend/app/config.py
git commit -m "feat(config): add AI generation API configuration

- Add DALL-E, Midjourney, and Suno API keys
- Add default AI generation provider setting

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: 创建AI生成API端点

**Files:**
- Create: `backend/app/api/ai_generation.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the failing test for API endpoints**

```python
# Add to backend/tests/test_ai_generation.py

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestAIGenerationAPI:
    """测试AI生成API端点"""

    def test_list_providers(self):
        """测试列出所有providers"""
        response = client.get("/api/ai-generation/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data

    @pytest.mark.asyncio
    async def test_generate_image_endpoint(self, tmp_path):
        """测试图像生成端点"""
        with patch('openai.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            mock_response = Mock()
            mock_response.data = [Mock(url="https://example.com/image.png")]
            mock_instance.images.generate = AsyncMock(return_value=mock_response)

            with patch('httpx.AsyncClient.get') as mock_get:
                mock_response_get = AsyncMock()
                mock_response_get.content = b"fake_image_data"
                mock_response_get.raise_for_status = Mock()
                mock_get.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response_get
                )

                response = client.post(
                    "/api/ai-generation/generate-image",
                    json={
                        "prompt": "A beautiful sunset",
                        "provider": "dalle",
                        "size": "1024x1024"
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert "image_path" in data
                assert "provider" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ai_generation.py::TestAIGenerationAPI -v`
Expected: FAIL with "404 Not Found"

- [ ] **Step 3: Implement API endpoints**

```python
# backend/app/api/ai_generation.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.ai_generation import AIGenerationManager, DALLEProvider
from app.config import settings

router = APIRouter(prefix="/api/ai-generation", tags=["AI Generation"])

# Initialize manager
manager = AIGenerationManager()

# Register DALL-E provider if API key is available
if settings.DALLE_API_KEY or settings.OPENAI_API_KEY:
    dalle_provider = DALLEProvider(
        api_key=settings.DALLE_API_KEY or settings.OPENAI_API_KEY
    )
    manager.register_provider("dalle", dalle_provider)


class GenerateImageRequest(BaseModel):
    prompt: str
    provider: str = "dalle"
    size: str = "1024x1024"
    quality: str = "standard"
    output_filename: Optional[str] = None


class GenerateMusicRequest(BaseModel):
    prompt: str
    provider: str
    duration: int = 30
    style: Optional[str] = None
    output_filename: Optional[str] = None


@router.get("/providers")
async def list_providers():
    """列出所有可用的AI生成Provider"""
    return {
        "providers": manager.list_providers()
    }


@router.post("/generate-image")
async def generate_image(request: GenerateImageRequest):
    """生成图像"""
    try:
        import uuid
        from pathlib import Path

        # Generate output path
        filename = request.output_filename or f"{uuid.uuid4()}.png"
        output_dir = Path(settings.DATA_DIR) / "generated" / "images"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        result = await manager.generate_image(
            request.provider,
            request.prompt,
            str(output_path),
            size=request.size,
            quality=request.quality
        )

        return {
            "image_path": result["path"],
            "size": result["size"],
            "format": result["format"],
            "provider": result["provider"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-music")
async def generate_music(request: GenerateMusicRequest):
    """生成音乐"""
    try:
        import uuid
        from pathlib import Path

        # Generate output path
        filename = request.output_filename or f"{uuid.uuid4()}.mp3"
        output_dir = Path(settings.DATA_DIR) / "generated" / "music"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        result = await manager.generate_music(
            request.provider,
            request.prompt,
            str(output_path),
            duration=request.duration,
            style=request.style
        )

        return {
            "music_path": result["path"],
            "duration": result["duration"],
            "format": result["format"],
            "provider": result["provider"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Register router in main.py**

```python
# Modify backend/app/main.py
# Add after other router imports:

from app.api import ai_generation

# Add after other router registrations:
app.include_router(ai_generation.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_ai_generation.py::TestAIGenerationAPI -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/ai_generation.py backend/app/main.py backend/tests/test_ai_generation.py
git commit -m "feat(api): add AI generation API endpoints

- Add /api/ai-generation/providers endpoint
- Add /api/ai-generation/generate-image endpoint
- Add /api/ai-generation/generate-music endpoint
- Register DALL-E provider on startup

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Chunk 2: Advanced Video Effects

### Task 6: 创建数据可视化特效

**Files:**
- Create: `backend/app/services/effects/__init__.py`
- Create: `backend/app/services/effects/data_visualization.py`
- Create: `backend/tests/test_advanced_effects.py`

- [ ] **Step 1: Write the failing test for data visualization**

```python
# backend/tests/test_advanced_effects.py
import pytest
from pathlib import Path
from app.services.effects.data_visualization import DataVisualizationEffect


class TestDataVisualizationEffect:
    """测试数据可视化特效"""

    def test_create_bar_chart(self, tmp_path):
        """测试创建柱状图"""
        effect = DataVisualizationEffect()
        data = [
            {"label": "A", "value": 100},
            {"label": "B", "value": 150},
            {"label": "C", "value": 120}
        ]

        output_path = str(tmp_path / "bar_chart.png")
        result = effect.create_chart(
            chart_type="bar",
            data=data,
            title="Test Bar Chart",
            output_path=output_path
        )

        assert Path(result["path"]).exists()
        assert result["chart_type"] == "bar"

    def test_create_line_chart(self, tmp_path):
        """测试创建折线图"""
        effect = DataVisualizationEffect()
        data = [
            {"x": 1, "y": 10},
            {"x": 2, "y": 15},
            {"x": 3, "y": 12}
        ]

        output_path = str(tmp_path / "line_chart.png")
        result = effect.create_chart(
            chart_type="line",
            data=data,
            title="Test Line Chart",
            output_path=output_path
        )

        assert Path(result["path"]).exists()
        assert result["chart_type"] == "line"

    def test_create_pie_chart(self, tmp_path):
        """测试创建饼图"""
        effect = DataVisualizationEffect()
        data = [
            {"label": "Category A", "value": 40},
            {"label": "Category B", "value": 30},
            {"label": "Category C", "value": 30}
        ]

        output_path = str(tmp_path / "pie_chart.png")
        result = effect.create_chart(
            chart_type="pie",
            data=data,
            title="Test Pie Chart",
            output_path=output_path
        )

        assert Path(result["path"]).exists()
        assert result["chart_type"] == "pie"

    def test_create_number_display(self, tmp_path):
        """测试创建数字展示"""
        effect = DataVisualizationEffect()

        output_path = str(tmp_path / "number.png")
        result = effect.create_number_display(
            value=12345,
            label="Total Views",
            output_path=output_path
        )

        assert Path(result["path"]).exists()
        assert result["value"] == 12345

    def test_invalid_chart_type(self, tmp_path):
        """测试无效图表类型"""
        effect = DataVisualizationEffect()

        with pytest.raises(ValueError, match="Unsupported chart type"):
            effect.create_chart(
                chart_type="invalid",
                data=[],
                output_path=str(tmp_path / "test.png")
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_advanced_effects.py::TestDataVisualizationEffect -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement DataVisualizationEffect**

```python
# backend/app/services/effects/data_visualization.py
import matplotlib.pyplot as plt
import matplotlib
from typing import List, Dict, Any
from pathlib import Path

# Use non-interactive backend
matplotlib.use('Agg')


class DataVisualizationEffect:
    """数据可视化特效生成器"""

    def __init__(self, style: str = "default"):
        self.style = style
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    def create_chart(
        self,
        chart_type: str,
        data: List[Dict[str, Any]],
        title: str = "",
        output_path: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建图表
        Args:
            chart_type: 图表类型 (bar, line, pie)
            data: 数据列表
            title: 图表标题
            output_path: 输出路径
        Returns:
            包含图表信息的字典
        """
        if chart_type == "bar":
            return self._create_bar_chart(data, title, output_path, **kwargs)
        elif chart_type == "line":
            return self._create_line_chart(data, title, output_path, **kwargs)
        elif chart_type == "pie":
            return self._create_pie_chart(data, title, output_path, **kwargs)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

    def _create_bar_chart(
        self,
        data: List[Dict[str, Any]],
        title: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """创建柱状图"""
        fig, ax = plt.subplots(figsize=kwargs.get("figsize", (10, 6)))

        labels = [item["label"] for item in data]
        values = [item["value"] for item in data]

        ax.bar(labels, values, color=kwargs.get("color", "#3498db"))
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel(kwargs.get("xlabel", ""))
        ax.set_ylabel(kwargs.get("ylabel", ""))

        # 添加数值标签
        for i, v in enumerate(values):
            ax.text(i, v, str(v), ha='center', va='bottom')

        plt.tight_layout()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=kwargs.get("dpi", 150), bbox_inches='tight')
        plt.close()

        return {
            "path": output_path,
            "chart_type": "bar",
            "data_points": len(data)
        }

    def _create_line_chart(
        self,
        data: List[Dict[str, Any]],
        title: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """创建折线图"""
        fig, ax = plt.subplots(figsize=kwargs.get("figsize", (10, 6)))

        x_values = [item["x"] for item in data]
        y_values = [item["y"] for item in data]

        ax.plot(x_values, y_values, marker='o', color=kwargs.get("color", "#e74c3c"))
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel(kwargs.get("xlabel", ""))
        ax.set_ylabel(kwargs.get("ylabel", ""))
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=kwargs.get("dpi", 150), bbox_inches='tight')
        plt.close()

        return {
            "path": output_path,
            "chart_type": "line",
            "data_points": len(data)
        }

    def _create_pie_chart(
        self,
        data: List[Dict[str, Any]],
        title: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """创建饼图"""
        fig, ax = plt.subplots(figsize=kwargs.get("figsize", (10, 8)))

        labels = [item["label"] for item in data]
        values = [item["value"] for item in data]

        colors = kwargs.get("colors", plt.cm.Set3.colors[:len(data)])

        ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors
        )
        ax.set_title(title, fontsize=16, fontweight='bold')

        plt.tight_layout()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=kwargs.get("dpi", 150), bbox_inches='tight')
        plt.close()

        return {
            "path": output_path,
            "chart_type": "pie",
            "data_points": len(data)
        }

    def create_number_display(
        self,
        value: Any,
        label: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """创建数字展示"""
        fig, ax = plt.subplots(figsize=kwargs.get("figsize", (8, 4)))
        ax.axis('off')

        # 格式化数字
        if isinstance(value, (int, float)):
            if value >= 1000000:
                formatted_value = f"{value/1000000:.1f}M"
            elif value >= 1000:
                formatted_value = f"{value/1000:.1f}K"
            else:
                formatted_value = str(value)
        else:
            formatted_value = str(value)

        # 显示数字和标签
        ax.text(
            0.5, 0.6, formatted_value,
            ha='center', va='center',
            fontsize=kwargs.get("value_size", 48),
            fontweight='bold',
            color=kwargs.get("value_color", "#2c3e50")
        )

        ax.text(
            0.5, 0.3, label,
            ha='center', va='center',
            fontsize=kwargs.get("label_size", 24),
            color=kwargs.get("label_color", "#7f8c8d")
        )

        plt.tight_layout()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=kwargs.get("dpi", 150), bbox_inches='tight')
        plt.close()

        return {
            "path": output_path,
            "value": value,
            "label": label
        }
```

- [ ] **Step 4: Create effects module init**

```python
# backend/app/services/effects/__init__.py
from .data_visualization import DataVisualizationEffect

__all__ = ["DataVisualizationEffect"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_advanced_effects.py::TestDataVisualizationEffect -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/effects/ backend/tests/test_advanced_effects.py
git commit -m "feat(effects): add DataVisualizationEffect

- Support bar, line, and pie charts
- Support number display
- Use matplotlib with Chinese font support
- Auto-save to specified output path

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: 创建动态字幕特效

**Files:**
- Create: `backend/app/services/effects/dynamic_subtitle.py`
- Modify: `backend/tests/test_advanced_effects.py`

- [ ] **Step 1: Write the failing test for dynamic subtitle**

```python
# Add to backend/tests/test_advanced_effects.py

from app.services.effects.dynamic_subtitle import DynamicSubtitleEffect


class TestDynamicSubtitleEffect:
    """测试动态字幕特效"""

    def test_create_highlight_subtitle(self, tmp_path):
        """测试创建高亮字幕"""
        effect = DynamicSubtitleEffect()
        text = "This is a test subtitle"

        output_path = str(tmp_path / "subtitle.png")
        result = effect.create_subtitle(
            text=text,
            mode="highlight",
            output_path=output_path,
            highlight_word="test"
        )

        assert Path(result["path"]).exists()
        assert result["mode"] == "highlight"

    def test_create_typing_subtitle(self, tmp_path):
        """测试创建打字机效果字幕"""
        effect = DynamicSubtitleEffect()
        text = "Typing effect"

        frames = effect.create_typing_frames(
            text=text,
            output_dir=str(tmp_path / "frames"),
            fps=24
        )

        assert len(frames) > 0
        assert all(Path(f).exists() for f in frames)

    def test_create_emphasis_subtitle(self, tmp_path):
        """测试创建强调效果字幕"""
        effect = DynamicSubtitleEffect()
        text = "Important message"

        output_path = str(tmp_path / "emphasis.png")
        result = effect.create_subtitle(
            text=text,
            mode="emphasis",
            output_path=output_path
        )

        assert Path(result["path"]).exists()
        assert result["mode"] == "emphasis"

    def test_invalid_subtitle_mode(self, tmp_path):
        """测试无效模式"""
        effect = DynamicSubtitleEffect()

        with pytest.raises(ValueError, match="Unsupported subtitle mode"):
            effect.create_subtitle(
                text="Test",
                mode="invalid",
                output_path=str(tmp_path / "test.png")
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_advanced_effects.py::TestDynamicSubtitleEffect -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement DynamicSubtitleEffect**

```python
# backend/app/services/effects/dynamic_subtitle.py
from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional
from pathlib import Path
import os


class DynamicSubtitleEffect:
    """动态字幕特效生成器"""

    def __init__(self):
        self.default_font_size = 32
        self.default_font_color = "#FFFFFF"
        self.default_bg_color = "#00000088"

    def create_subtitle(
        self,
        text: str,
        mode: str,
        output_path: str,
        **kwargs
    ) -> dict:
        """
        创建字幕图像
        Args:
            text: 字幕文本
            mode: 模式 (highlight, typing, emphasis)
            output_path: 输出路径
        Returns:
            包含字幕信息的字典
        """
        if mode == "highlight":
            return self._create_highlight_subtitle(text, output_path, **kwargs)
        elif mode == "emphasis":
            return self._create_emphasis_subtitle(text, output_path, **kwargs)
        else:
            raise ValueError(f"Unsupported subtitle mode: {mode}")

    def _create_highlight_subtitle(
        self,
        text: str,
        output_path: str,
        highlight_word: str = "",
        **kwargs
    ) -> dict:
        """创建高亮字幕"""
        font_size = kwargs.get("font_size", self.default_font_size)
        font_color = kwargs.get("font_color", self.default_font_color)
        highlight_color = kwargs.get("highlight_color", "#FFD700")

        # 创建图像
        width = kwargs.get("width", 800)
        height = kwargs.get("height", 100)

        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 使用系统字体
        try:
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
        except:
            font = ImageFont.load_default()

        # 计算文本位置（居中）
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        # 绘制背景
        padding = 10
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(0, 0, 0, 180)
        )

        # 绘制文本
        if highlight_word and highlight_word in text:
            # 分段绘制，高亮关键词
            parts = text.split(highlight_word)
            current_x = x

            for i, part in enumerate(parts):
                # 绘制普通文本
                draw.text((current_x, y), part, font=font, fill=font_color)
                current_x += draw.textbbox((0, 0), part, font=font)[2]

                # 绘制高亮文本
                if i < len(parts) - 1:
                    draw.text((current_x, y), highlight_word, font=font, fill=highlight_color)
                    current_x += draw.textbbox((0, 0), highlight_word, font=font)[2]
        else:
            draw.text((x, y), text, font=font, fill=font_color)

        # 保存图像
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)

        return {
            "path": output_path,
            "mode": "highlight",
            "text": text
        }

    def _create_emphasis_subtitle(
        self,
        text: str,
        output_path: str,
        **kwargs
    ) -> dict:
        """创建强调效果字幕"""
        font_size = kwargs.get("font_size", 48)
        font_color = kwargs.get("font_color", self.default_font_color)

        width = kwargs.get("width", 800)
        height = kwargs.get("height", 120)

        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
        except:
            font = ImageFont.load_default()

        # 计算文本位置
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        # 绘制背景
        padding = 15
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(0, 0, 0, 200)
        )

        # 绘制描边（强调效果）
        outline_color = kwargs.get("outline_color", "#FFD700")
        for adj_x in range(-2, 3):
            for adj_y in range(-2, 3):
                draw.text((x + adj_x, y + adj_y), text, font=font, fill=outline_color)

        # 绘制主文本
        draw.text((x, y), text, font=font, fill=font_color)

        # 保存
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)

        return {
            "path": output_path,
            "mode": "emphasis",
            "text": text
        }

    def create_typing_frames(
        self,
        text: str,
        output_dir: str,
        fps: int = 24,
        **kwargs
    ) -> List[str]:
        """
        创建打字机效果的帧序列
        Args:
            text: 字幕文本
            output_dir: 输出目录
            fps: 帧率
        Returns:
            帧文件路径列表
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        frames = []
        total_frames = len(text) * 2  # 每个字符2帧

        for i in range(total_frames):
            # 计算当前显示的字符数
            char_count = min((i + 1) // 2, len(text))
            current_text = text[:char_count]

            # 创建帧
            frame_path = os.path.join(output_dir, f"frame_{i:04d}.png")
            self._create_typing_frame(current_text, frame_path, **kwargs)
            frames.append(frame_path)

        return frames

    def _create_typing_frame(
        self,
        text: str,
        output_path: str,
        **kwargs
    ):
        """创建单帧打字机效果"""
        font_size = kwargs.get("font_size", self.default_font_size)
        font_color = kwargs.get("font_color", self.default_font_color)

        width = kwargs.get("width", 800)
        height = kwargs.get("height", 100)

        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
        except:
            font = ImageFont.load_default()

        # 计算位置
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = 30

        # 绘制背景
        padding = 10
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + font_size + padding],
            fill=(0, 0, 0, 180)
        )

        # 绘制文本
        draw.text((x, y), text, font=font, fill=font_color)

        # 保存
        img.save(output_path)
```

- [ ] **Step 4: Update effects module init**

```python
# Modify backend/app/services/effects/__init__.py
from .data_visualization import DataVisualizationEffect
from .dynamic_subtitle import DynamicSubtitleEffect

__all__ = ["DataVisualizationEffect", "DynamicSubtitleEffect"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_advanced_effects.py::TestDynamicSubtitleEffect -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/effects/ backend/tests/test_advanced_effects.py
git commit -m "feat(effects): add DynamicSubtitleEffect

- Support highlight mode with keyword highlighting
- Support emphasis mode with outline effect
- Support typing mode with frame sequence generation
- Use PIL for image generation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Chunk 3: Batch Processing

### Task 8: 创建BatchJob数据模型

**Files:**
- Create: `backend/app/models/batch.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write the failing test for BatchJob model**

```python
# Add to backend/tests/test_batch.py (create new file)
import pytest
from app.models.batch import BatchJob, BatchJobStatus
from datetime import datetime


class TestBatchJob:
    """测试BatchJob模型"""

    def test_create_batch_job(self):
        """测试创建批量任务"""
        job = BatchJob(
            name="Test Batch",
            project_ids=[1, 2, 3],
            status=BatchJobStatus.PENDING
        )

        assert job.name == "Test Batch"
        assert len(job.project_ids) == 3
        assert job.status == BatchJobStatus.PENDING

    def test_batch_job_status_enum(self):
        """测试状态枚举"""
        assert BatchJobStatus.PENDING.value == "pending"
        assert BatchJobStatus.RUNNING.value == "running"
        assert BatchJobStatus.COMPLETED.value == "completed"
        assert BatchJobStatus.FAILED.value == "failed"

    def test_batch_job_progress(self):
        """测试进度计算"""
        job = BatchJob(
            name="Test",
            project_ids=[1, 2, 3, 4, 5],
            completed_count=2
        )

        assert job.progress == 40.0  # 2/5 = 40%
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_batch.py::TestBatchJob -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement BatchJob model**

```python
# backend/app/models/batch.py
from sqlalchemy import Column, Integer, String, JSON, DateTime, Float, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum


class BatchJobStatus(enum.Enum):
    """批量任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchJob(Base):
    """批量任务模型"""
    __tablename__ = "batch_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    project_ids = Column(JSON, nullable=False)  # List[int]
    status = Column(String, default=BatchJobStatus.PENDING.value)
    
    # 进度跟踪
    total_count = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # 调度信息
    priority = Column(Integer, default=5)  # 1-10, 10最高
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 结果
    results = Column(JSON, nullable=True)  # List[dict]
    error_message = Column(String, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def progress(self) -> float:
        """计算完成进度百分比"""
        if self.total_count == 0:
            return 0.0
        return (self.completed_count / self.total_count) * 100.0
```

- [ ] **Step 4: Export model in __init__.py**

```python
# Modify backend/app/models/__init__.py
# Add to imports:
from .batch import BatchJob, BatchJobStatus

# Add to __all__ list
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_batch.py::TestBatchJob -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/batch.py backend/app/models/__init__.py backend/tests/test_batch.py
git commit -m "feat(models): add BatchJob model for batch processing

- Define BatchJobStatus enum
- Track progress with completed/failed counts
- Support priority-based scheduling
- Store results and error messages

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 9: 实现SmartScheduler智能调度器

**Files:**
- Create: `backend/app/services/batch/__init__.py`
- Create: `backend/app/services/batch/scheduler.py`
- Modify: `backend/tests/test_batch.py`

- [ ] **Step 1: Write the failing test for SmartScheduler**

```python
# Add to backend/tests/test_batch.py

from app.services.batch.scheduler import SmartScheduler
import psutil


class TestSmartScheduler:
    """测试智能调度器"""

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        scheduler = SmartScheduler()
        assert scheduler.max_concurrent > 0

    def test_get_optimal_concurrency(self):
        """测试获取最优并发数"""
        scheduler = SmartScheduler()
        concurrency = scheduler.get_optimal_concurrency()

        assert concurrency > 0
        assert concurrency <= scheduler.max_concurrent

    def test_get_optimal_concurrency_with_high_load(self):
        """测试高负载时的并发数"""
        scheduler = SmartScheduler()
        
        # Mock high CPU usage
        with patch('psutil.cpu_percent', return_value=90.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 85.0
                
                concurrency = scheduler.get_optimal_concurrency()
                # 高负载时应该减少并发
                assert concurrency <= scheduler.max_concurrent // 2

    def test_calculate_job_priority(self):
        """测试任务优先级计算"""
        scheduler = SmartScheduler()
        
        job1 = BatchJob(name="High", project_ids=[1], priority=10)
        job2 = BatchJob(name="Low", project_ids=[2], priority=1)
        
        jobs = [job2, job1]
        sorted_jobs = scheduler.prioritize_jobs(jobs)
        
        assert sorted_jobs[0].priority == 10
        assert sorted_jobs[1].priority == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_batch.py::TestSmartScheduler -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement SmartScheduler**

```python
# backend/app/services/batch/scheduler.py
import psutil
from typing import List
from app.models.batch import BatchJob


class SmartScheduler:
    """智能任务调度器"""

    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self.cpu_threshold = 80.0  # CPU使用率阈值
        self.memory_threshold = 80.0  # 内存使用率阈值

    def get_optimal_concurrency(self) -> int:
        """
        根据系统资源动态计算最优并发数
        Returns:
            建议的并发任务数
        """
        # 获取当前系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # 基础并发数
        base_concurrency = self.max_concurrent

        # CPU负载调整
        if cpu_percent > self.cpu_threshold:
            # CPU使用率过高，减少并发
            cpu_factor = (100.0 - cpu_percent) / (100.0 - self.cpu_threshold)
            base_concurrency = int(base_concurrency * cpu_factor)
        elif cpu_percent < self.cpu_threshold * 0.5:
            # CPU使用率低，可以增加并发
            cpu_factor = 1.5
            base_concurrency = min(
                int(base_concurrency * cpu_factor),
                self.max_concurrent
            )

        # 内存负载调整
        if memory_percent > self.memory_threshold:
            # 内存使用率过高，减少并发
            memory_factor = (100.0 - memory_percent) / (100.0 - self.memory_threshold)
            base_concurrency = int(base_concurrency * memory_factor)

        # 确保至少有1个并发
        return max(1, min(base_concurrency, self.max_concurrent))

    def prioritize_jobs(self, jobs: List[BatchJob]) -> List[BatchJob]:
        """
        根据优先级排序任务
        Args:
            jobs: 任务列表
        Returns:
            排序后的任务列表
        """
        return sorted(jobs, key=lambda j: j.priority, reverse=True)

    def should_start_new_job(self) -> bool:
        """
        判断是否应该启动新任务
        Returns:
            True 如果系统资源充足
        """
        optimal = self.get_optimal_concurrency()
        # 如果最优并发数大于等于当前并发数，可以启动新任务
        return optimal >= 1

    def get_system_status(self) -> dict:
        """获取系统状态摘要"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024 ** 3),
            "optimal_concurrency": self.get_optimal_concurrency()
        }
```

- [ ] **Step 4: Create batch module init**

```python
# backend/app/services/batch/__init__.py
from .scheduler import SmartScheduler

__all__ = ["SmartScheduler"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_batch.py::TestSmartScheduler -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/batch/ backend/tests/test_batch.py
git commit -m "feat(batch): add SmartScheduler for dynamic concurrency

- Calculate optimal concurrency based on CPU/memory
- Support priority-based job scheduling
- Monitor system resources in real-time
- Adjust concurrency dynamically

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 10: 创建批量处理Celery任务

**Files:**
- Create: `backend/app/tasks/batch_tasks.py`
- Modify: `backend/tests/test_batch.py`

- [ ] **Step 1: Write the failing test for batch tasks**

```python
# Add to backend/tests/test_batch.py

from app.tasks.batch_tasks import process_batch_job


class TestBatchTasks:
    """测试批量处理任务"""

    @pytest.mark.celery
    def test_process_batch_job_success(self, db_session):
        """测试批量任务处理成功"""
        # 创建批量任务
        job = BatchJob(
            name="Test Batch",
            project_ids=[1, 2],
            status=BatchJobStatus.PENDING.value
        )
        db_session.add(job)
        db_session.commit()

        # 执行任务
        result = process_batch_job.delay(job.id)

        # 验证结果
        assert result.successful()

    @pytest.mark.celery
    def test_process_batch_job_updates_status(self, db_session):
        """测试批量任务更新状态"""
        job = BatchJob(
            name="Test",
            project_ids=[1],
            status=BatchJobStatus.PENDING.value
        )
        db_session.add(job)
        db_session.commit()

        process_batch_job.delay(job.id)

        db_session.refresh(job)
        assert job.status == BatchJobStatus.COMPLETED.value
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_batch.py::TestBatchTasks -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement batch tasks**

```python
# backend/app/tasks/batch_tasks.py
from celery import shared_task
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.batch import BatchJob, BatchJobStatus
from app.services.batch.scheduler import SmartScheduler
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_batch_job(job_id: int):
    """
    处理批量任务
    Args:
        job_id: 批量任务ID
    """
    db: Session = SessionLocal()
    scheduler = SmartScheduler()

    try:
        # 获取任务
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        if not job:
            raise ValueError(f"BatchJob {job_id} not found")

        # 更新状态为运行中
        job.status = BatchJobStatus.RUNNING.value
        job.started_at = func.now()
        db.commit()

        logger.info(f"Starting batch job {job_id}: {job.name}")

        # 处理每个项目
        results = []
        for project_id in job.project_ids:
            try:
                # 检查系统资源，动态调整
                if not scheduler.should_start_new_job():
                    logger.warning("System resources low, waiting...")
                    import time
                    time.sleep(10)

                # 处理单个项目（这里可以调用视频生成任务）
                result = process_single_project(project_id)
                results.append({
                    "project_id": project_id,
                    "status": "success",
                    "result": result
                })
                job.completed_count += 1

            except Exception as e:
                logger.error(f"Error processing project {project_id}: {e}")
                results.append({
                    "project_id": project_id,
                    "status": "failed",
                    "error": str(e)
                })
                job.failed_count += 1

            db.commit()

        # 完成任务
        job.status = BatchJobStatus.COMPLETED.value
        job.completed_at = func.now()
        job.results = results
        db.commit()

        logger.info(f"Batch job {job_id} completed: {job.completed_count}/{job.total_count}")

    except Exception as e:
        logger.error(f"Batch job {job_id} failed: {e}")
        job.status = BatchJobStatus.FAILED.value
        job.error_message = str(e)
        db.commit()
        raise

    finally:
        db.close()


def process_single_project(project_id: int) -> dict:
    """
    处理单个项目
    Args:
        project_id: 项目ID
    Returns:
        处理结果
    """
    # 这里可以调用现有的视频生成流程
    # 暂时返回模拟结果
    return {
        "project_id": project_id,
        "message": "Processed successfully"
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_batch.py::TestBatchTasks -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/batch_tasks.py backend/tests/test_batch.py
git commit -m "feat(tasks): add batch processing Celery tasks

- Implement process_batch_job task
- Integrate with SmartScheduler for resource management
- Track progress and update job status
- Handle individual project processing errors

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 11: 创建批量处理API端点

**Files:**
- Create: `backend/app/api/batch.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_batch.py`

- [ ] **Step 1: Write the failing test for batch API**

```python
# Add to backend/tests/test_batch.py

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestBatchAPI:
    """测试批量处理API"""

    def test_create_batch_job(self):
        """测试创建批量任务"""
        response = client.post(
            "/api/batch/jobs",
            json={
                "name": "Test Batch",
                "project_ids": [1, 2, 3],
                "priority": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Batch"
        assert data["status"] == "pending"

    def test_get_batch_job(self):
        """测试获取批量任务"""
        # 先创建
        create_response = client.post(
            "/api/batch/jobs",
            json={
                "name": "Test",
                "project_ids": [1]
            }
        )
        job_id = create_response.json()["id"]

        # 再获取
        response = client.get(f"/api/batch/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["id"] == job_id

    def test_list_batch_jobs(self):
        """测试列出批量任务"""
        response = client.get("/api/batch/jobs")
        assert response.status_code == 200
        assert "jobs" in response.json()

    def test_get_system_status(self):
        """测试获取系统状态"""
        response = client.get("/api/batch/system-status")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "optimal_concurrency" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_batch.py::TestBatchAPI -v`
Expected: FAIL with "404 Not Found"

- [ ] **Step 3: Implement batch API endpoints**

```python
# backend/app/api/batch.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.models.batch import BatchJob, BatchJobStatus
from app.services.batch.scheduler import SmartScheduler
from app.tasks.batch_tasks import process_batch_job

router = APIRouter(prefix="/api/batch", tags=["Batch Processing"])


class CreateBatchJobRequest(BaseModel):
    name: str
    project_ids: List[int]
    priority: int = 5
    scheduled_at: Optional[str] = None


@router.post("/jobs")
async def create_batch_job(
    request: CreateBatchJobRequest,
    db: Session = Depends(get_db)
):
    """创建批量任务"""
    job = BatchJob(
        name=request.name,
        project_ids=request.project_ids,
        priority=request.priority,
        total_count=len(request.project_ids),
        status=BatchJobStatus.PENDING.value
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # 异步启动任务
    process_batch_job.delay(job.id)

    return {
        "id": job.id,
        "name": job.name,
        "status": job.status,
        "total_count": job.total_count,
        "created_at": job.created_at
    }


@router.get("/jobs/{job_id}")
async def get_batch_job(job_id: int, db: Session = Depends(get_db)):
    """获取批量任务详情"""
    job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")

    return {
        "id": job.id,
        "name": job.name,
        "status": job.status,
        "total_count": job.total_count,
        "completed_count": job.completed_count,
        "failed_count": job.failed_count,
        "progress": job.progress,
        "results": job.results,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }


@router.get("/jobs")
async def list_batch_jobs(
    status: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """列出批量任务"""
    query = db.query(BatchJob)

    if status:
        query = query.filter(BatchJob.status == status)

    jobs = query.order_by(BatchJob.created_at.desc()).limit(limit).all()

    return {
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at
            }
            for job in jobs
        ]
    }


@router.get("/system-status")
async def get_system_status():
    """获取系统资源状态"""
    scheduler = SmartScheduler()
    return scheduler.get_system_status()
```

- [ ] **Step 4: Register router in main.py**

```python
# Modify backend/app/main.py
# Add import:
from app.api import batch

# Add router registration:
app.include_router(batch.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_batch.py::TestBatchAPI -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/batch.py backend/app/main.py backend/tests/test_batch.py
git commit -m "feat(api): add batch processing API endpoints

- Add POST /api/batch/jobs for creating batch jobs
- Add GET /api/batch/jobs/{id} for job details
- Add GET /api/batch/jobs for listing jobs
- Add GET /api/batch/system-status for resource monitoring

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Chunk 4: Analytics & Dashboard

### Task 12: 创建Analytics数据模型

**Files:**
- Create: `backend/app/models/analytics.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_analytics.py`

- [ ] **Step 1: Write the failing test for analytics models**

```python
# backend/tests/test_analytics.py
import pytest
from app.models.analytics import ProjectMetric, SystemMetric


class TestAnalyticsModels:
    """测试分析数据模型"""

    def test_create_project_metric(self):
        """测试创建项目指标"""
        metric = ProjectMetric(
            project_id=1,
            metric_type="cost",
            metric_value=12.5,
            metadata={"provider": "dalle"}
        )

        assert metric.project_id == 1
        assert metric.metric_type == "cost"
        assert metric.metric_value == 12.5

    def test_create_system_metric(self):
        """测试创建系统指标"""
        metric = SystemMetric(
            metric_name="cpu_usage",
            metric_value=75.5,
            tags={"server": "main"}
        )

        assert metric.metric_name == "cpu_usage"
        assert metric.metric_value == 75.5
        assert metric.tags["server"] == "main"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_analytics.py::TestAnalyticsModels -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement analytics models**

```python
# backend/app/models/analytics.py
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ProjectMetric(Base):
    """项目指标模型"""
    __tablename__ = "project_metrics"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    metric_type = Column(String, nullable=False)  # cost, duration, api_calls, etc.
    metric_value = Column(Float, nullable=False)
    metadata = Column(JSON, nullable=True)  # 额外元数据
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemMetric(Base):
    """系统指标模型"""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, nullable=False)  # cpu_usage, memory_usage, etc.
    metric_value = Column(Float, nullable=False)
    tags = Column(JSON, nullable=True)  # 标签，如server, region等
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Export models in __init__.py**

```python
# Modify backend/app/models/__init__.py
# Add to imports:
from .analytics import ProjectMetric, SystemMetric

# Add to __all__ list
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_analytics.py::TestAnalyticsModels -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/analytics.py backend/app/models/__init__.py backend/tests/test_analytics.py
git commit -m "feat(models): add ProjectMetric and SystemMetric models

- Track project-level metrics (cost, duration, API calls)
- Track system-level metrics (CPU, memory usage)
- Support metadata and tags for flexible querying

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 13: 实现MetricsCollector指标收集器

**Files:**
- Create: `backend/app/services/analytics/__init__.py`
- Create: `backend/app/services/analytics/collector.py`
- Modify: `backend/tests/test_analytics.py`

- [ ] **Step 1: Write the failing test for MetricsCollector**

```python
# Add to backend/tests/test_analytics.py

from app.services.analytics.collector import MetricsCollector
from datetime import datetime, timedelta


class TestMetricsCollector:
    """测试指标收集器"""

    def test_record_project_metric(self, db_session):
        """测试记录项目指标"""
        collector = MetricsCollector(db_session)
        
        collector.record_project_metric(
            project_id=1,
            metric_type="cost",
            metric_value=15.5,
            metadata={"provider": "dalle"}
        )

        # 验证记录
        from app.models.analytics import ProjectMetric
        metric = db_session.query(ProjectMetric).first()
        assert metric is not None
        assert metric.metric_value == 15.5

    def test_record_system_metric(self, db_session):
        """测试记录系统指标"""
        collector = MetricsCollector(db_session)
        
        collector.record_system_metric(
            metric_name="cpu_usage",
            metric_value=65.3,
            tags={"server": "main"}
        )

        from app.models.analytics import SystemMetric
        metric = db_session.query(SystemMetric).first()
        assert metric is not None
        assert metric.metric_value == 65.3

    def test_get_project_metrics(self, db_session):
        """测试获取项目指标"""
        collector = MetricsCollector(db_session)
        
        # 记录多个指标
        collector.record_project_metric(1, "cost", 10.0)
        collector.record_project_metric(1, "cost", 20.0)
        collector.record_project_metric(1, "duration", 120.0)

        metrics = collector.get_project_metrics(1, metric_type="cost")
        assert len(metrics) == 2

    def test_aggregate_metrics(self, db_session):
        """测试指标聚合"""
        collector = MetricsCollector(db_session)
        
        # 记录指标
        collector.record_project_metric(1, "cost", 10.0)
        collector.record_project_metric(1, "cost", 20.0)

        # 聚合计算
        total_cost = collector.aggregate_project_metrics(
            project_id=1,
            metric_type="cost",
            aggregation="sum"
        )
        assert total_cost == 30.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_analytics.py::TestMetricsCollector -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement MetricsCollector**

```python
# backend/app/services/analytics/collector.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.analytics import ProjectMetric, SystemMetric
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class MetricsCollector:
    """指标收集器"""

    def __init__(self, db: Session):
        self.db = db

    def record_project_metric(
        self,
        project_id: int,
        metric_type: str,
        metric_value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProjectMetric:
        """
        记录项目指标
        Args:
            project_id: 项目ID
            metric_type: 指标类型
            metric_value: 指标值
            metadata: 元数据
        Returns:
            创建的指标记录
        """
        metric = ProjectMetric(
            project_id=project_id,
            metric_type=metric_type,
            metric_value=metric_value,
            metadata=metadata or {}
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def record_system_metric(
        self,
        metric_name: str,
        metric_value: float,
        tags: Optional[Dict[str, Any]] = None
    ) -> SystemMetric:
        """
        记录系统指标
        Args:
            metric_name: 指标名称
            metric_value: 指标值
            tags: 标签
        Returns:
            创建的指标记录
        """
        metric = SystemMetric(
            metric_name=metric_name,
            metric_value=metric_value,
            tags=tags or {}
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def get_project_metrics(
        self,
        project_id: int,
        metric_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ProjectMetric]:
        """
        获取项目指标列表
        """
        query = self.db.query(ProjectMetric).filter(
            ProjectMetric.project_id == project_id
        )

        if metric_type:
            query = query.filter(ProjectMetric.metric_type == metric_type)

        if start_time:
            query = query.filter(ProjectMetric.recorded_at >= start_time)

        if end_time:
            query = query.filter(ProjectMetric.recorded_at <= end_time)

        return query.order_by(ProjectMetric.recorded_at.desc()).limit(limit).all()

    def aggregate_project_metrics(
        self,
        project_id: int,
        metric_type: str,
        aggregation: str = "sum",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        """
        聚合项目指标
        Args:
            project_id: 项目ID
            metric_type: 指标类型
            aggregation: 聚合方式 (sum, avg, min, max)
            start_time: 开始时间
            end_time: 结束时间
        Returns:
            聚合结果
        """
        query = self.db.query(ProjectMetric).filter(
            ProjectMetric.project_id == project_id,
            ProjectMetric.metric_type == metric_type
        )

        if start_time:
            query = query.filter(ProjectMetric.recorded_at >= start_time)

        if end_time:
            query = query.filter(ProjectMetric.recorded_at <= end_time)

        if aggregation == "sum":
            result = query.with_entities(
                func.sum(ProjectMetric.metric_value)
            ).scalar()
        elif aggregation == "avg":
            result = query.with_entities(
                func.avg(ProjectMetric.metric_value)
            ).scalar()
        elif aggregation == "min":
            result = query.with_entities(
                func.min(ProjectMetric.metric_value)
            ).scalar()
        elif aggregation == "max":
            result = query.with_entities(
                func.max(ProjectMetric.metric_value)
            ).scalar()
        else:
            raise ValueError(f"Unsupported aggregation: {aggregation}")

        return result or 0.0

    def get_system_metrics(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SystemMetric]:
        """获取系统指标列表"""
        query = self.db.query(SystemMetric).filter(
            SystemMetric.metric_name == metric_name
        )

        if start_time:
            query = query.filter(SystemMetric.recorded_at >= start_time)

        if end_time:
            query = query.filter(SystemMetric.recorded_at <= end_time)

        return query.order_by(SystemMetric.recorded_at.desc()).limit(limit).all()
```

- [ ] **Step 4: Create analytics module init**

```python
# backend/app/services/analytics/__init__.py
from .collector import MetricsCollector

__all__ = ["MetricsCollector"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_analytics.py::TestMetricsCollector -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/analytics/ backend/tests/test_analytics.py
git commit -m "feat(analytics): add MetricsCollector for tracking metrics

- Record project-level and system-level metrics
- Support metric querying with time filters
- Support aggregation operations (sum, avg, min, max)
- Flexible metadata and tags support

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 14: 创建Analytics API和Dashboard端点

**Files:**
- Create: `backend/app/api/analytics.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_analytics.py`

- [ ] **Step 1: Write the failing test for analytics API**

```python
# Add to backend/tests/test_analytics.py

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestAnalyticsAPI:
    """测试分析API"""

    def test_record_project_metric(self):
        """测试记录项目指标API"""
        response = client.post(
            "/api/analytics/project/1/metrics",
            json={
                "metric_type": "cost",
                "metric_value": 12.5,
                "metadata": {"provider": "dalle"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metric_value"] == 12.5

    def test_get_project_metrics(self):
        """测试获取项目指标API"""
        # 先记录
        client.post(
            "/api/analytics/project/1/metrics",
            json={
                "metric_type": "cost",
                "metric_value": 15.0
            }
        )

        # 再获取
        response = client.get("/api/analytics/project/1/metrics?metric_type=cost")
        assert response.status_code == 200
        assert "metrics" in response.json()

    def test_get_project_cost_summary(self):
        """测试获取项目成本汇总"""
        # 记录多个成本
        client.post(
            "/api/analytics/project/1/metrics",
            json={"metric_type": "cost", "metric_value": 10.0}
        )
        client.post(
            "/api/analytics/project/1/metrics",
            json={"metric_type": "cost", "metric_value": 20.0}
        )

        response = client.get("/api/analytics/project/1/cost-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_cost"] == 30.0

    def test_get_dashboard_data(self):
        """测试获取Dashboard数据"""
        response = client.get("/api/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_projects" in data
        assert "total_cost" in data
        assert "recent_metrics" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_analytics.py::TestAnalyticsAPI -v`
Expected: FAIL with "404 Not Found"

- [ ] **Step 3: Implement analytics API endpoints**

```python
# backend/app/api/analytics.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.database import get_db
from app.services.analytics.collector import MetricsCollector
from app.models.project import Project
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


class RecordMetricRequest(BaseModel):
    metric_type: str
    metric_value: float
    metadata: Optional[Dict[str, Any]] = None


@router.post("/project/{project_id}/metrics")
async def record_project_metric(
    project_id: int,
    request: RecordMetricRequest,
    db: Session = Depends(get_db)
):
    """记录项目指标"""
    collector = MetricsCollector(db)
    
    metric = collector.record_project_metric(
        project_id=project_id,
        metric_type=request.metric_type,
        metric_value=request.metric_value,
        metadata=request.metadata
    )

    return {
        "id": metric.id,
        "project_id": metric.project_id,
        "metric_type": metric.metric_type,
        "metric_value": metric.metric_value,
        "recorded_at": metric.recorded_at
    }


@router.get("/project/{project_id}/metrics")
async def get_project_metrics(
    project_id: int,
    metric_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取项目指标列表"""
    collector = MetricsCollector(db)
    
    metrics = collector.get_project_metrics(
        project_id=project_id,
        metric_type=metric_type,
        limit=limit
    )

    return {
        "metrics": [
            {
                "id": m.id,
                "metric_type": m.metric_type,
                "metric_value": m.metric_value,
                "metadata": m.metadata,
                "recorded_at": m.recorded_at
            }
            for m in metrics
        ]
    }


@router.get("/project/{project_id}/cost-summary")
async def get_project_cost_summary(
    project_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """获取项目成本汇总"""
    collector = MetricsCollector(db)
    
    start_time = datetime.now() - timedelta(days=days)
    
    total_cost = collector.aggregate_project_metrics(
        project_id=project_id,
        metric_type="cost",
        aggregation="sum",
        start_time=start_time
    )

    # 获取成本明细
    costs = collector.get_project_metrics(
        project_id=project_id,
        metric_type="cost",
        start_time=start_time,
        limit=100
    )

    # 按提供者分组
    cost_by_provider = {}
    for cost in costs:
        provider = cost.metadata.get("provider", "unknown")
        if provider not in cost_by_provider:
            cost_by_provider[provider] = 0.0
        cost_by_provider[provider] += cost.metric_value

    return {
        "project_id": project_id,
        "total_cost": total_cost,
        "period_days": days,
        "cost_by_provider": cost_by_provider
    }


@router.get("/dashboard")
async def get_dashboard_data(db: Session = Depends(get_db)):
    """获取Dashboard数据"""
    collector = MetricsCollector(db)
    
    # 总项目数
    total_projects = db.query(Project).count()
    
    # 总成本（过去30天）
    start_time = datetime.now() - timedelta(days=30)
    total_cost = db.query(ProjectMetric).filter(
        ProjectMetric.metric_type == "cost",
        ProjectMetric.recorded_at >= start_time
    ).with_entities(
        func.sum(ProjectMetric.metric_value)
    ).scalar() or 0.0

    # 最近指标
    recent_metrics = db.query(ProjectMetric).order_by(
        ProjectMetric.recorded_at.desc()
    ).limit(10).all()

    return {
        "total_projects": total_projects,
        "total_cost": total_cost,
        "period_days": 30,
        "recent_metrics": [
            {
                "project_id": m.project_id,
                "metric_type": m.metric_type,
                "metric_value": m.metric_value,
                "recorded_at": m.recorded_at
            }
            for m in recent_metrics
        ]
    }


from sqlalchemy import func
from app.models.analytics import ProjectMetric
```

- [ ] **Step 4: Register router in main.py**

```python
# Modify backend/app/main.py
# Add import:
from app.api import analytics

# Add router registration:
app.include_router(analytics.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_analytics.py::TestAnalyticsAPI -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/analytics.py backend/app/main.py backend/tests/test_analytics.py
git commit -m "feat(api): add Analytics API and Dashboard endpoints

- Add POST /api/analytics/project/{id}/metrics for recording
- Add GET /api/analytics/project/{id}/metrics for querying
- Add GET /api/analytics/project/{id}/cost-summary for cost breakdown
- Add GET /api/analytics/dashboard for overview data

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Plan Summary

**Total Tasks:** 14 tasks across 4 major chunks

**Chunk 1 - AI Generation Service (Tasks 1-5):**
- AIGenerationProvider base class and DALL-E 3 implementation
- AIGenerationManager for provider coordination
- API endpoints for image and music generation

**Chunk 2 - Advanced Video Effects (Tasks 6-7):**
- DataVisualizationEffect for charts and graphs
- DynamicSubtitleEffect for highlight, emphasis, and typing effects

**Chunk 3 - Batch Processing (Tasks 8-11):**
- BatchJob model for job tracking
- SmartScheduler for dynamic concurrency
- Celery tasks for async processing
- API endpoints for job management

**Chunk 4 - Analytics & Dashboard (Tasks 12-14):**
- ProjectMetric and SystemMetric models
- MetricsCollector for data collection and aggregation
- Dashboard API for analytics visualization

**Testing Strategy:**
- Unit tests for each component with mocking
- Integration tests for API endpoints
- TDD approach: write failing test first, then implement

**Dependencies to Install:**
```bash
pip install matplotlib pillow psutil httpx
```

**Database Migrations Required:**
- Create batch_jobs table
- Create project_metrics table
- Create system_metrics table
