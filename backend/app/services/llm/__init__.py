# backend/app/services/llm/__init__.py
from typing import Dict, Any, Optional
import threading
from .base import BaseLLMProvider
from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider
from .glm_provider import GLMProvider
from app.config import settings


class LLMProviderManager:
    """LLM Provider管理器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Double-check locking pattern for thread safety
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # Initialize instance variables
                    cls._instance._providers: Dict[str, BaseLLMProvider] = {}
                    cls._instance._initialize_providers()
        return cls._instance

    def _initialize_providers(self):
        """初始化所有配置的provider"""
        # Claude
        if settings.ANTHROPIC_API_KEY:
            self._providers["claude"] = ClaudeProvider(
                api_key=settings.ANTHROPIC_API_KEY
            )

        # OpenAI
        openai_key = getattr(settings, "OPENAI_API_KEY", None)
        if openai_key:
            self._providers["openai"] = OpenAIProvider(
                api_key=openai_key,
                config={
                    "provider_name": "openai",
                    "base_url": getattr(settings, "OPENAI_BASE_URL", None),
                    "default_model": getattr(settings, "OPENAI_MODEL", "gpt-4-turbo")
                }
            )

        # Kimi (OpenAI-compatible API)
        kimi_key = getattr(settings, "KIMI_API_KEY", None)
        if kimi_key:
            self._providers["kimi"] = OpenAIProvider(
                api_key=kimi_key,
                config={
                    "provider_name": "kimi",
                    "base_url": getattr(settings, "KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
                    "default_model": getattr(settings, "KIMI_MODEL", "moonshot-v1-8k")
                }
            )

        # GLM
        glm_endpoint = getattr(settings, "GLM_ENDPOINT", None)
        if glm_endpoint:
            self._providers["glm"] = GLMProvider(endpoint=glm_endpoint)

    def get_provider(self, name: str) -> BaseLLMProvider:
        """获取指定provider"""
        if name not in self._providers:
            raise ValueError(f"LLM provider '{name}' not available")
        return self._providers[name]

    def list_providers(self) -> Dict[str, Any]:
        """列出所有可用provider"""
        return {
            name: {
                "name": provider.provider_name,
                "models": provider.available_models,
                "available": provider.validate_config()
            }
            for name, provider in self._providers.items()
        }

    def register_provider(self, name: str, provider: BaseLLMProvider):
        """动态注册provider"""
        self._providers[name] = provider


# 全局管理器实例
llm_manager = LLMProviderManager()

# 默认provider（向后兼容）
llm_provider = None
try:
    llm_provider = llm_manager.get_provider("claude")
except ValueError:
    # Claude provider not configured
    pass


__all__ = [
    "BaseLLMProvider",
    "ClaudeProvider",
    "OpenAIProvider",
    "GLMProvider",
    "LLMProviderManager",
    "llm_manager",
    "llm_provider"
]
