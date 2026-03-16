# backend/tests/test_ai_generation.py
import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch
from app.services.ai_generation.base import AIGenerationProvider
from app.services.ai_generation.dalle_provider import DALLEProvider


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


class TestDALLEProvider:
    """测试DALL-E Provider"""

    @pytest.mark.asyncio
    async def test_dalle_generate_image_success(self):
        """测试DALL-E生成图像成功"""
        with patch('app.services.ai_generation.dalle_provider.AsyncOpenAI') as mock_client_class:
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance

            # Mock the image generation response
            mock_response = Mock()
            mock_response.data = [Mock(url="https://example.com/image.png")]
            mock_instance.images.generate = AsyncMock(return_value=mock_response)

            # Mock the image download
            with patch('httpx.AsyncClient') as mock_async_client:
                mock_response_get = AsyncMock()
                mock_response_get.content = b"fake_image_data"
                mock_response_get.raise_for_status = Mock()

                mock_async_client.return_value.__aenter__.return_value.get = AsyncMock(
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
    async def test_dalle_generate_image_with_style_enhancement(self):
        """测试风格增强提示词"""
        with patch('app.services.ai_generation.dalle_provider.AsyncOpenAI') as mock_client_class:
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance

            mock_response = Mock()
            mock_response.data = [Mock(url="https://example.com/image.png")]
            mock_instance.images.generate = AsyncMock(return_value=mock_response)

            with patch('httpx.AsyncClient') as mock_async_client:
                mock_response_get = AsyncMock()
                mock_response_get.content = b"fake_image_data"
                mock_response_get.raise_for_status = Mock()

                mock_async_client.return_value.__aenter__.return_value.get = AsyncMock(
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
        with patch('app.services.ai_generation.dalle_provider.AsyncOpenAI') as mock_client_class:
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance
            mock_instance.images.generate = AsyncMock(
                side_effect=Exception("API Error")
            )

            provider = DALLEProvider(api_key="test_key")

            result = await provider.generate_image("Test", style="realistic", size=(1024, 1024))
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_dalle_generate_image_download_error(self):
        """测试下载错误处理"""
        with patch('app.services.ai_generation.dalle_provider.AsyncOpenAI') as mock_client_class:
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance

            # Mock the image generation response
            mock_response = Mock()
            mock_response.data = [Mock(url="https://example.com/image.png")]
            mock_instance.images.generate = AsyncMock(return_value=mock_response)

            # Mock the image download to fail
            with patch('httpx.AsyncClient') as mock_async_client:
                mock_async_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.HTTPError("Network error")
                )

                provider = DALLEProvider(api_key="test_key")
                result = await provider.generate_image(
                    "Test",
                    style="realistic",
                    size=(1024, 1024)
                )

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
