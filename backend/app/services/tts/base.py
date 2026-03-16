# backend/app/services/tts/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


class BaseTTSProvider(ABC):
    """TTS提供商抽象基类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        language: str = "zh-CN",
        speed: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        合成语音
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            voice: 声音ID
            language: 语言代码
            speed: 语速（0.5-2.0）
        Returns:
            包含音频信息的字典
        """
        pass

    @abstractmethod
    async def list_voices(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出可用声音
        Args:
            language: 语言代码过滤
        Returns:
            声音列表
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass

    @property
    @abstractmethod
    def available_models(self) -> List[str]:
        """可用模型列表"""
        pass

    def estimate_duration(self, text: str, speed: float = 1.0) -> float:
        """估算音频时长（秒）"""
        # 中文约每秒3-4个字
        char_count = len(text)
        base_duration = char_count / 3.5
        return base_duration / speed
