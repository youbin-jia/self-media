# backend/app/services/llm/glm_provider.py
from typing import Dict, Any, Optional, List
import httpx
from .base import BaseLLMProvider


class GLMProvider(BaseLLMProvider):
    """GLM-5本地模型提供商"""

    def __init__(self, endpoint: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.endpoint = endpoint  # 本地模型服务端点

    @property
    def provider_name(self) -> str:
        return "glm"

    @property
    def available_models(self) -> List[str]:
        return ["glm-5", "glm-5-9b", "glm-5-13b"]

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        model = model or "glm-5"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.endpoint}/generate",
                    json={
                        "prompt": prompt,
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()["text"]
        except Exception as e:
            raise RuntimeError(f"GLM API error: {str(e)}")

    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        model = model or "glm-5"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.endpoint}/chat",
                    json={
                        "messages": messages,
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()["text"]
        except Exception as e:
            raise RuntimeError(f"GLM API error: {str(e)}")

    def validate_config(self) -> bool:
        return bool(self.endpoint)
