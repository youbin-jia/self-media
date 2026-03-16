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
