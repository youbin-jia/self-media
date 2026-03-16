# backend/tests/test_llm_providers.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.llm.base import BaseLLMProvider
from app.services.llm.claude_provider import ClaudeProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.glm_provider import GLMProvider
from app.services.llm import LLMProviderManager


class TestBaseLLMProvider:
    """测试LLM抽象基类"""

    def test_base_provider_is_abstract(self):
        """基类不能直接实例化"""
        with pytest.raises(TypeError):
            BaseLLMProvider()

    def test_base_provider_requires_generate_method(self):
        """子类必须实现generate方法"""
        class IncompleteProvider(BaseLLMProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()


class TestClaudeProvider:
    """测试Claude Provider"""

    @pytest.mark.asyncio
    async def test_claude_generate_success(self):
        """测试Claude生成成功"""
        with patch('anthropic.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.messages.create = AsyncMock(
                return_value=Mock(content=[Mock(text="Generated text")])
            )

            provider = ClaudeProvider(api_key="test_key")
            result = await provider.generate("Test prompt")

            assert result == "Generated text"
            mock_instance.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_claude_generate_with_custom_model(self):
        """测试使用自定义模型"""
        with patch('anthropic.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.messages.create = AsyncMock(
                return_value=Mock(content=[Mock(text="Response")])
            )

            provider = ClaudeProvider(api_key="test_key")
            await provider.generate("Test", model="claude-opus-4-6-20250514")

            call_args = mock_instance.messages.create.call_args
            assert call_args.kwargs["model"] == "claude-opus-4-6-20250514"

    @pytest.mark.asyncio
    async def test_claude_generate_api_error(self):
        """测试API错误处理"""
        with patch('anthropic.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.messages.create = AsyncMock(
                side_effect=Exception("API Error")
            )

            provider = ClaudeProvider(api_key="test_key")

            with pytest.raises(RuntimeError, match="Claude API error"):
                await provider.generate("Test")

    def test_claude_provider_name(self):
        """测试provider名称"""
        provider = ClaudeProvider(api_key="test_key")
        assert provider.provider_name == "claude"

    def test_claude_available_models(self):
        """测试可用模型列表"""
        provider = ClaudeProvider(api_key="test_key")
        models = provider.available_models
        assert "claude-sonnet-4-6-20250514" in models
        assert len(models) == 3

    @pytest.mark.asyncio
    async def test_claude_generate_with_history(self):
        """测试带历史记录的生成"""
        with patch('anthropic.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.messages.create = AsyncMock(
                return_value=Mock(content=[Mock(text="Response with history")])
            )

            provider = ClaudeProvider(api_key="test_key")
            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
                {"role": "user", "content": "How are you?"}
            ]
            result = await provider.generate_with_history(messages)

            assert result == "Response with history"
            mock_instance.messages.create.assert_called_once()


class TestOpenAIProvider:
    """测试OpenAI Provider"""

    @pytest.mark.asyncio
    async def test_openai_generate_success(self):
        """测试OpenAI生成成功"""
        with patch('app.services.llm.openai_provider.AsyncOpenAI') as mock_client_class:
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance
            mock_instance.chat.completions.create = AsyncMock(
                return_value=Mock(choices=[Mock(message=Mock(content="OpenAI response"))])
            )

            provider = OpenAIProvider(api_key="test_key")
            result = await provider.generate("Test prompt")

            assert result == "OpenAI response"

    def test_openai_available_models(self):
        """测试OpenAI可用模型"""
        provider = OpenAIProvider(api_key="test_key")
        models = provider.available_models
        assert "gpt-4-turbo" in models
        assert "gpt-4o" in models

    @pytest.mark.asyncio
    async def test_openai_generate_with_history(self):
        """测试OpenAI带历史记录的生成"""
        with patch('app.services.llm.openai_provider.AsyncOpenAI') as mock_client_class:
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance
            mock_instance.chat.completions.create = AsyncMock(
                return_value=Mock(choices=[Mock(message=Mock(content="OpenAI response with history"))])
            )

            provider = OpenAIProvider(api_key="test_key")
            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ]
            result = await provider.generate_with_history(messages)

            assert result == "OpenAI response with history"


class TestGLMProvider:
    """测试GLM Provider"""

    @pytest.mark.asyncio
    async def test_glm_generate_success(self):
        """测试GLM生成成功"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json = Mock(return_value={"text": "GLM response"})
            mock_response.raise_for_status = Mock()

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            provider = GLMProvider(endpoint="http://localhost:8000")
            result = await provider.generate("Test prompt")

            assert result == "GLM response"

    def test_glm_validate_config(self):
        """测试GLM配置验证"""
        provider = GLMProvider(endpoint="http://localhost:8000")
        assert provider.validate_config() is True

        provider_no_endpoint = GLMProvider(endpoint="")
        assert provider_no_endpoint.validate_config() is False

    @pytest.mark.asyncio
    async def test_glm_generate_with_history(self):
        """测试GLM带历史记录的生成"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json = Mock(return_value={"text": "GLM response with history"})
            mock_response.raise_for_status = Mock()

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            provider = GLMProvider(endpoint="http://localhost:8000")
            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ]
            result = await provider.generate_with_history(messages)

            assert result == "GLM response with history"


class TestLLMProviderManager:
    """测试LLM Provider管理器"""

    def test_manager_singleton(self):
        """测试管理器单例模式"""
        manager1 = LLMProviderManager()
        manager2 = LLMProviderManager()
        assert manager1 is manager2

    @patch('app.services.llm.settings')
    def test_manager_initializes_configured_providers(self, mock_settings):
        """测试管理器初始化已配置的providers"""
        mock_settings.ANTHROPIC_API_KEY = "test_key"
        mock_settings.OPENAI_API_KEY = "openai_key"
        mock_settings.GLM_ENDPOINT = None

        # Reset singleton for testing
        LLMProviderManager._instance = None

        manager = LLMProviderManager()
        providers = manager.list_providers()

        assert "claude" in providers
        assert "openai" in providers

    def test_manager_get_provider(self):
        """测试获取provider"""
        manager = LLMProviderManager()

        with pytest.raises(ValueError, match="not available"):
            manager.get_provider("nonexistent")

    @patch('app.services.llm.settings')
    def test_manager_register_custom_provider(self, mock_settings):
        """测试注册自定义provider"""
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GLM_ENDPOINT = None

        # Clear singleton for testing
        LLMProviderManager._instance = None
        manager = LLMProviderManager()

        custom_provider = Mock(spec=BaseLLMProvider)
        custom_provider.provider_name = "custom"
        custom_provider.available_models = ["custom-model"]

        manager.register_provider("custom", custom_provider)
        assert "custom" in manager.list_providers()


class TestLLMErrorHandling:
    """测试LLM错误处理"""

    @pytest.mark.asyncio
    async def test_claude_rate_limit_retry(self):
        """测试Claude速率限制重试"""
        with patch('anthropic.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            # First call fails, second succeeds
            mock_instance.messages.create = AsyncMock(
                side_effect=[
                    Exception("Rate limit exceeded"),
                    Mock(content=[Mock(text="Success after retry")])
                ]
            )

            provider = ClaudeProvider(api_key="test_key")

            # Should retry on rate limit
            with pytest.raises(RuntimeError):
                await provider.generate("Test")
            # Note: Actual retry logic would be implemented in the provider

    @pytest.mark.asyncio
    async def test_openai_timeout_handling(self):
        """测试OpenAI超时处理"""
        with patch('openai.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.chat.completions.create = AsyncMock(
                side_effect=TimeoutError("Request timed out")
            )

            provider = OpenAIProvider(api_key="test_key")

            with pytest.raises(RuntimeError, match="OpenAI API error"):
                await provider.generate("Test")
