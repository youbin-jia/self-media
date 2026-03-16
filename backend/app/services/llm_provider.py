# backend/app/services/llm_provider.py
"""LLM Provider Abstraction Layer - Backward Compatibility Layer"""
from app.services.llm import llm_manager, BaseLLMProvider
from app.config import settings


# Backward compatibility: Export the manager and default provider
def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get the configured LLM provider"""
    provider_name = getattr(settings, "DEFAULT_LLM_PROVIDER", "claude")
    return llm_manager.get_provider(provider_name)


# For backward compatibility
__all__ = ["get_llm_provider", "llm_manager"]

