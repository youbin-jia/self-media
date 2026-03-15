# backend/app/services/llm_provider.py
"""LLM Provider Abstraction Layer"""
from abc import ABC, abstractmethod
from typing import Optional
from anthropic import AsyncAnthropic
from app.config import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate text from a prompt"""
        pass


class ClaudeProvider(LLMProvider):
    """Claude API implementation"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        self.client = AsyncAnthropic(api_key=self.api_key)

    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate text using Claude API"""
        try:
            message = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude API error: {str(e)}")


def get_llm_provider() -> LLMProvider:
    """Factory function to get the configured LLM provider"""
    return ClaudeProvider()
