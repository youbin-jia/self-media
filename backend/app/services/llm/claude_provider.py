# backend/app/services/llm/claude_provider.py
from typing import Dict, Any, Optional, List
import anthropic
from .base import BaseLLMProvider


class ClaudeProvider(BaseLLMProvider):
    """Claude API提供商"""

    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = api_key
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def available_models(self) -> List[str]:
        return [
            "claude-sonnet-4-6-20250514",
            "claude-opus-4-6-20250514",
            "claude-haiku-4-5-20251001"
        ]

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        model = model or "claude-sonnet-4-6-20250514"
        try:
            message = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude API error: {str(e)}")

    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        model = model or "claude-sonnet-4-6-20250514"
        # 转换为Claude格式
        claude_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
        try:
            message = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=claude_messages
            )
            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude API error: {str(e)}")

    def validate_config(self) -> bool:
        return bool(self.api_key)
