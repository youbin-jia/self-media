# backend/app/services/tts/__init__.py
from typing import Dict, Any, Optional
import threading
from .base import BaseTTSProvider
from .azure_tts import AzureTTSProvider
from .elevenlabs_tts import ElevenLabsTTSProvider
from app.config import settings


class TTSProviderManager:
    """TTS Provider管理器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Double-check locking pattern for thread-safe singleton
        if cls._instance is None:
            with cls._lock:
                # Double-check inside lock to prevent race condition
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # Initialize instance variables (not class variables)
                    cls._instance._providers = {}
                    cls._instance._initialize_providers()
        return cls._instance

    def _initialize_providers(self):
        """初始化所有配置的TTS provider"""
        # Azure Speech
        if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
            self._providers["azure"] = AzureTTSProvider(
                subscription_key=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_SPEECH_REGION
            )

        # ElevenLabs
        elevenlabs_key = getattr(settings, "ELEVENLABS_API_KEY", None)
        if elevenlabs_key:
            self._providers["elevenlabs"] = ElevenLabsTTSProvider(
                api_key=elevenlabs_key
            )

    def get_provider(self, name: str) -> BaseTTSProvider:
        """获取指定TTS provider"""
        if name not in self._providers:
            raise ValueError(f"TTS provider '{name}' not available")
        return self._providers[name]

    def list_providers(self) -> Dict[str, Any]:
        """列出所有可用TTS provider"""
        return {
            name: provider.provider_name
            for name, provider in self._providers.items()
        }


# 全局管理器实例
tts_manager = TTSProviderManager()


__all__ = [
    "BaseTTSProvider",
    "AzureTTSProvider",
    "ElevenLabsTTSProvider",
    "TTSProviderManager",
    "tts_manager"
]
