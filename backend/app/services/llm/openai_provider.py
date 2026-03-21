# backend/app/services/llm/openai_provider.py
from typing import Dict, Any, Optional, List
import logging
from openai import AsyncOpenAI
from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT-4提供商"""

    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = api_key
        self.base_url = self.config.get("base_url")
        self.default_model = self.config.get("default_model", "gpt-4-turbo")
        self._provider_name = self.config.get("provider_name", "openai")
        self.client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def available_models(self) -> List[str]:
        models = [
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4o",
            "gpt-4o-mini"
        ]
        if self.default_model not in models:
            models.insert(0, self.default_model)
        return models

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        model = model or self.default_model
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            # Log full error for debugging
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            # Raise sanitized error message
            error_type = type(e).__name__
            raise RuntimeError(f"OpenAI API error: {error_type}")

    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        model = model or self.default_model
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            # Log full error for debugging
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            # Raise sanitized error message
            error_type = type(e).__name__
            raise RuntimeError(f"OpenAI API error: {error_type}")

    def validate_config(self) -> bool:
        return bool(self.api_key)
