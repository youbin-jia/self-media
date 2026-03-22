# backend/app/services/tts/__init__.py
from typing import Dict, Any, Optional
import threading
from .base import BaseTTSProvider
from .azure_tts import AzureTTSProvider
from .elevenlabs_tts import ElevenLabsTTSProvider
from .aliyun_tts import AliyunTTSProvider
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

        # Aliyun NLS TTS (requires token + app key)
        aliyun_token = getattr(settings, "ALIYUN_TTS_TOKEN", None)
        aliyun_app_key = getattr(settings, "ALIYUN_TTS_APP_KEY", None)
        aliyun_ak = getattr(settings, "ALIYUN_ACCESS_KEY_ID", None)
        aliyun_sk = getattr(settings, "ALIYUN_ACCESS_KEY_SECRET", None)
        if aliyun_app_key and (aliyun_token or (aliyun_ak and aliyun_sk)):
            self._providers["aliyun"] = AliyunTTSProvider(
                token=aliyun_token,
                app_key=aliyun_app_key,
                region=getattr(settings, "ALIYUN_TTS_REGION", "cn-shanghai"),
                voice=getattr(settings, "ALIYUN_TTS_VOICE", "xiaoyun"),
                access_key_id=aliyun_ak,
                access_key_secret=aliyun_sk
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
    "AliyunTTSProvider",
    "TTSProviderManager",
    "tts_manager"
]
