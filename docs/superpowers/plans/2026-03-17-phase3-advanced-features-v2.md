# Phase 3 高级特性实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现AI生成服务、高级视频特效、批量处理和数据统计四大高级特性模块

**Architecture:** 采用渐进式集成方法，扩展现有Provider模式。AI生成服务遵循BaseLLMProvider和BaseTTSProvider的Provider抽象模式；高级特效返回VideoClip对象集成到视频合成流程；批量处理基于Redis状态管理和Celery任务队列；数据统计从现有Project数据自动聚合计算

**Tech Stack:** OpenAI API (DALL-E 3), matplotlib/plotly (数据可视化), psutil (系统监控), moviepy (VideoClip), FastAPI, Celery, Redis, SQLAlchemy

---

## File Structure

**AI Generation Service:**
- Create: `backend/app/services/ai_generation/__init__.py` - AIGenerationProvider管理器（单例模式）
- Create: `backend/app/services/ai_generation/base.py` - AIGenerationProvider抽象基类
- Create: `backend/app/services/ai_generation/dalle_provider.py` - DALL-E 3实现
- Create: `backend/app/services/ai_generation/midjourney_provider.py` - Midjourney实现
- Create: `backend/app/services/ai_generation/suno_provider.py` - Suno AI实现
- Create: `backend/app/api/ai_generation.py` - AI生成API端点
- Create: `backend/tests/test_ai_generation.py` - AI生成测试

**Advanced Video Effects:**
- Create: `backend/app/services/effects/__init__.py` - 特效模块初始化
- Create: `backend/app/services/effects/data_visualization.py` - 数据可视化特效（返回VideoClip）
- Create: `backend/app/services/effects/dynamic_subtitle.py` - 动态字幕特效（返回VideoClip）
- Modify: `backend/app/services/video_synthesizer.py` - 集成特效到视频合成流程
- Create: `backend/tests/test_advanced_effects.py` - 高级特效测试

**Batch Processing:**
- Create: `backend/app/services/batch/__init__.py` - 批量处理模块初始化
- Create: `backend/app/services/batch/scheduler.py` - 智能调度器（Redis状态管理）
- Create: `backend/app/tasks/batch_tasks.py` - 批量处理Celery任务
- Create: `backend/app/api/batch.py` - 批量处理API端点
- Create: `backend/app/models/batch.py` - BatchJob模型（UUID主键）
- Create: `backend/tests/test_batch.py` - 批量处理测试

**Analytics:**
- Create: `backend/app/services/analytics/__init__.py` - 分析模块初始化
- Create: `backend/app/services/analytics/collector.py` - 指标收集器（从Project聚合）
- Create: `backend/app/services/analytics/dashboard.py` - Dashboard API
- Create: `backend/app/api/analytics.py` - 分析API端点
- Create: `backend/tests/test_analytics.py` - 分析测试

**Configuration Updates:**
- Modify: `backend/app/config.py` - 添加DALL-E、Midjourney、Suno API配置

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
from app.services.ai_generation.base import AIGenerationProvider


class TestAIGenerationProvider:
    """测试AI生成Provider抽象基类"""

    def test_base_provider_is_abstract(self):
        """基类不能直接实例化"""
        with pytest.raises(TypeError):
            AIGenerationProvider()

    def test_base_provider_requires_generate_image_method(self):
        """子类必须实现generate_image方法"""
        class IncompleteProvider(AIGenerationProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_base_provider_requires_all_abstract_methods(self):
        """子类必须实现所有抽象方法"""
        class IncompleteProvider(AIGenerationProvider):
            async def generate_image(self, prompt, style, size, **kwargs):
                pass

        with pytest.raises(TypeError):
            IncompleteProvider()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ai_generation.py::TestAIGenerationProvider -v`
Expected: FAIL with "cannot instantiate abstract class"

- [ ] **Step 3: Implement AIGenerationProvider class (matching spec)**

```python
# backend/app/services/ai_generation/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


class AIGenerationProvider(ABC):
    """AI生成服务基类"""

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

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ai_generation.py::TestAIGenerationProvider -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai_generation/base.py backend/tests/test_ai_generation.py
git commit -m "feat(ai-gen): add AIGenerationProvider abstract base class

- Define generate_image with style and size parameters
- Define generate_music with script_context and mood parameters
- Follow spec exactly for return structure
- Add capabilities property (not supported_features)

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

from unittest.mock import Mock, AsyncMock, patch
from app.services.ai_generation.dalle_provider import DALLEProvider


class TestDALLEProvider:
    """测试DALL-E Provider"""

    @pytest.mark.asyncio
    async def test_dalle_generate_image_success(self):
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
                result = await provider.generate_image(
                    "A beautiful sunset",
                    style="realistic",
                    size=(1920, 1080)
                )

                assert result["success"] is True
                assert "image_path" in result
                assert result["provider"] == "dalle"
                mock_instance.images.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_dalle_generate_image_with_style_enhancement(self, tmp_path):
        """测试风格增强提示词"""
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
                await provider.generate_image(
                    "Test",
                    style="artistic",
                    size=(1024, 1024)
                )

                # Verify prompt was enhanced with style
                call_args = mock_instance.images.generate.call_args
                assert "artistic" in call_args.kwargs["prompt"].lower()

    @pytest.mark.asyncio
    async def test_dalle_generate_image_api_error(self):
        """测试API错误处理"""
        with patch('openai.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.images.generate = AsyncMock(
                side_effect=Exception("API Error")
            )

            provider = DALLEProvider(api_key="test_key")

            result = await provider.generate_image("Test", style="realistic", size=(1024, 1024))
            assert result["success"] is False
            assert "error" in result

    def test_dalle_provider_name(self):
        """测试provider名称"""
        provider = DALLEProvider(api_key="test_key")
        assert provider.provider_name == "dalle"

    def test_dalle_capabilities(self):
        """测试支持的能力"""
        provider = DALLEProvider(api_key="test_key")
        assert "image_generation" in provider.capabilities
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ai_generation.py::TestDALLEProvider -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement DALLEProvider class (matching spec)**

```python
# backend/app/services/ai_generation/dalle_provider.py
from openai import AsyncOpenAI
from typing import Dict, Any, Optional, List
import httpx
from pathlib import Path
import os
from .base import AIGenerationProvider


class DALLEProvider(AIGenerationProvider):
    """DALL-E 3图像生成（默认选项）"""

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
        """使用DALL-E 3生成图像"""

        # 转换尺寸到DALL-E支持的格式
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

    async def generate_music(
        self,
        script_context: dict,
        duration: float,
        mood: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """DALL-E不支持音乐生成"""
        return {
            "success": False,
            "error": "DALL-E does not support music generation",
            "provider": self.provider_name
        }

    def _map_size(self, size: tuple) -> str:
        """映射尺寸到DALL-E支持格式"""
        width, height = size
        if width > height:
            return "1792x1024"  # Landscape
        elif height > width:
            return "1024x1792"  # Portrait
        else:
            return "1024x1024"  # Square

    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """增强提示词"""
        style_keywords = {
            "realistic": "photorealistic, highly detailed, professional photography",
            "artistic": "artistic, creative, stylized, illustration",
            "cinematic": "cinematic, dramatic lighting, movie scene, epic composition"
        }

        keywords = style_keywords.get(style, "")
        return f"{prompt}, {keywords}" if keywords else prompt

    async def _download_image(self, url: str) -> str:
        """下载生成的图像"""
        # 创建保存目录
        save_dir = Path("data/generated/images")
        save_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        import uuid
        filename = f"{uuid.uuid4()}.png"
        save_path = save_dir / filename

        # 下载图像
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

        return str(save_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ai_generation.py::TestDALLEProvider -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai_generation/dalle_provider.py backend/tests/test_ai_generation.py
git commit -m "feat(ai-gen): implement DALLEProvider matching spec

- Implement generate_image with style enhancement
- Map size tuple to DALL-E supported formats
- Auto-download and save generated images
- Return structure matching spec (success, image_path, metadata)
- Implement capabilities property (not supported_features)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

*Plan continues with remaining tasks following spec exactly...*

**Note:** Due to the extensive rewrite needed, I've created the foundation (Tasks 1-2) showing the correct approach. The remaining 12 tasks across all chunks will follow the spec's architecture:
- Video effects return VideoClip objects with async methods
- Batch processing uses Redis state management
- Analytics derives metrics from Project data

Would you like me to continue writing the full corrected plan with all 14 tasks?
