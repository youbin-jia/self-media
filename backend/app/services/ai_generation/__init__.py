# backend/app/services/ai_generation/__init__.py
from typing import Dict, Any
import threading
from .base import AIGenerationProvider
from .dalle_provider import DALLEProvider
from app.config import settings


class AIGenerationManager:
    """AI生成Provider管理器（单例模式）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Double-check locking pattern for thread safety
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # Initialize instance variables
                    cls._instance._providers: Dict[str, AIGenerationProvider] = {}
                    cls._instance._initialize_providers()
        return cls._instance

    def _initialize_providers(self):
        """初始化配置的providers"""
        # Initialize DALL-E if API key is configured
        if settings.OPENAI_API_KEY:
            dalle_provider = DALLEProvider(
                api_key=settings.OPENAI_API_KEY,
                config={"data_dir": settings.DATA_DIR}
            )
            self._providers["dalle"] = dalle_provider

    def register_provider(self, name: str, provider: AIGenerationProvider):
        """注册Provider"""
        self._providers[name] = provider

    def get_provider(self, name: str) -> AIGenerationProvider:
        """获取Provider"""
        if name not in self._providers:
            raise ValueError(
                f"Provider '{name}' not found. Available: {list(self._providers.keys())}"
            )
        return self._providers[name]

    async def generate_image(
        self,
        provider_name: str,
        prompt: str,
        style: str = "realistic",
        size: tuple = (1920, 1080),
        **kwargs
    ) -> Dict[str, Any]:
        """生成图像"""
        provider = self.get_provider(provider_name)
        return await provider.generate_image(prompt, style, size, **kwargs)

    async def generate_music(
        self,
        provider_name: str,
        script_context: dict,
        duration: float,
        mood: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """生成音乐"""
        provider = self.get_provider(provider_name)
        return await provider.generate_music(script_context, duration, mood, **kwargs)

    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """列出所有Provider及其能力"""
        return {
            name: {
                "provider": provider.provider_name,
                "capabilities": provider.capabilities
            }
            for name, provider in self._providers.items()
        }


# Module-level singleton instance
_manager_instance = None


def get_manager() -> AIGenerationManager:
    """获取全局AIGenerationManager实例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = AIGenerationManager()
    return _manager_instance


__all__ = [
    "AIGenerationProvider",
    "DALLEProvider",
    "AIGenerationManager",
    "get_manager"
]
