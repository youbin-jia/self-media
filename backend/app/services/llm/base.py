# backend/app/services/llm/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseLLMProvider(ABC):
    """LLM提供商抽象基类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """生成文本"""
        pass

    @abstractmethod
    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """带历史记录的生成（用于多轮对话）"""
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

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        return True
